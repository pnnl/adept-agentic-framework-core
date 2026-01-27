import os
from typing import List, Dict, Any, Optional, TypedDict, Annotated
import json  # Added json import

from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_openai.chat_models.base import ChatOpenAI as BaseChatOpenAI
from langchain_ollama import ChatOllama
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END

from .mcp_langchain_tools import (
    get_mcp_sql_tool_langchain,
    get_mcp_sql_schema_tool_langchain,
    get_mcp_rag_tool_langchain,
    get_mcp_list_files_tool_langchain,
    get_mcp_ingest_data_tool_langchain,
)
from ..core.logger_config import get_logger

logger = get_logger(__name__)


class AgentState(TypedDict):
    chat_history: List[BaseMessage]
    user_input: str
    sql_query: str
    query_result: str
    rag_documents: List[str]
    next_action: str
    agent_outcome: Any


logger = get_logger(__name__)


class ScientificWorkflowAgent:
    def __init__(self):
        self._llm_config = {
            "model_name": os.getenv(
                "STREAMLIT_DEFAULT_MODEL", "ollama/mistral"
            ),  # Use STREAMLIT_DEFAULT_MODEL
            "ollama_base_url": os.getenv("OLLAMA_API_BASE_URL")
            or os.getenv("OLLAMA_API_BASE"),
            "azure_api_version": os.getenv("AZURE_API_VERSION"),
            "azure_api_key": os.getenv("AZURE_API_KEY") or os.getenv("OPENAI_API_KEY"),
            "azure_api_base": os.getenv("AZURE_API_BASE"),  # Add Azure API Base
            "google_project_id": os.getenv("GOOGLE_PROJECT_ID"),
            "google_location": os.getenv("GOOGLE_LOCATION"),
            # Internal LLM provider configuration
            "internal_llm_api_key": os.getenv("INTERNAL_LLM_API_KEY"),
            "internal_llm_base_url": os.getenv("INTERNAL_LLM_BASE_URL"),
            "internal_llm_model": os.getenv("INTERNAL_LLM_MODEL"),
        }
        self.tools = [
            get_mcp_sql_tool_langchain(),
            get_mcp_sql_schema_tool_langchain(),
            get_mcp_rag_tool_langchain(),
            get_mcp_list_files_tool_langchain(),
            # Note: ingest_data tool commented out due to API restrictions
            # get_mcp_ingest_data_tool_langchain(),
        ]
        self.app = self._build_langgraph_app()

    async def _get_llm_instance(self):
        # Check for internal LLM provider FIRST (before reading model_name)
        if (
            self._llm_config["internal_llm_api_key"]
            and self._llm_config["internal_llm_base_url"]
            and self._llm_config["internal_llm_model"]
        ):
            internal_model = self._llm_config["internal_llm_model"]
            internal_base_url = self._llm_config["internal_llm_base_url"]
            internal_api_key = self._llm_config["internal_llm_api_key"]

            logger.info(
                f"Using internal LLM provider: {internal_base_url} with model {internal_model}"
            )

            # Reasoning models need higher max_tokens for internal reasoning + response
            max_tokens = (
                4000
                if "o4-mini" in internal_model or "o3-mini" in internal_model
                else 1000
            )

            return ChatOpenAI(
                model=internal_model,
                api_key=internal_api_key,
                base_url=internal_base_url,
                max_tokens=max_tokens,
            )

        model_name = str(self._llm_config["model_name"]).lower()
        logger.info(f"Using model {model_name} for chat agent")

        if model_name.startswith("ollama/"):
            ollama_model = model_name.split("/")[1]
            ollama_base_url = self._llm_config["ollama_base_url"]
            return ChatOllama(
                model=ollama_model, base_url=ollama_base_url, temperature=0
            )
        elif (
            model_name.startswith("azure/")
            or model_name.startswith("4o-")
            or model_name.startswith("o4-")
            or model_name.startswith("o3")
            or model_name.startswith("gpt")
        ):
            azure_api_base = self._llm_config["azure_api_base"]
            azure_api_version = self._llm_config["azure_api_version"]
            azure_api_key = self._llm_config["azure_api_key"]

            if not azure_api_base or not azure_api_version or not azure_api_key:
                logger.warning(
                    "Azure OpenAI Chat Model requested but AZURE_API_BASE/VERSION/KEY are not fully set. Falling back to OpenAI Chat Model if applicable."
                )
                return ChatOpenAI(model=model_name)  # Removed temperature=0

            # Check if the base URL already contains the deployment path
            if "/deployments/" in azure_api_base.lower():
                logger.info(
                    f"Loading AzureChatOpenAI with full endpoint: {azure_api_base}"
                )
                return AzureChatOpenAI(
                    azure_endpoint=azure_api_base,
                    api_version=azure_api_version,
                    api_key=azure_api_key,
                )  # Removed temperature=0
            else:
                # Assume model_name is the deployment name if base URL is just the resource endpoint
                azure_deployment = (
                    model_name.split("/")[1]
                    if model_name.startswith("azure/")
                    else model_name
                )
                logger.info(
                    f"Loading AzureChatOpenAI with deployment: {azure_deployment}, base_url: {azure_api_base}"
                )
                return AzureChatOpenAI(
                    azure_deployment=azure_deployment,
                    azure_endpoint=azure_api_base,
                    api_version=azure_api_version,
                    api_key=azure_api_key,
                )  # Removed temperature=0
        elif model_name.startswith("google/"):
            google_model = model_name.split("/")[1]
            google_project_id = self._llm_config["google_project_id"]
            google_location = self._llm_config["google_location"]
            return ChatVertexAI(
                model_name=google_model,
                project=google_project_id,
                location=google_location,
                temperature=0,
            )
        else:
            return ChatOpenAI(model=model_name)  # Removed temperature=0

    def _build_langgraph_app(self):
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("llm_decision", self._call_llm_decision_node)
        workflow.add_node("get_sql_schema", self._call_get_sql_schema_tool_node)
        workflow.add_node("execute_sql", self._call_execute_sql_tool_node)
        workflow.add_node("query_csv_rag", self._call_query_csv_rag_tool_node)
        workflow.add_node(
            "list_files", self._call_list_files_tool_node
        )  # Add list_files node

        # Set entry point
        workflow.set_entry_point("llm_decision")

        # Define edges
        workflow.add_conditional_edges(
            "get_sql_schema",
            self._decide_schema_next_step,
            {"continue": "llm_decision", "end": END},
        )
        workflow.add_edge("execute_sql", END)  # End after SQL execution
        workflow.add_edge("query_csv_rag", END)  # End after RAG query
        workflow.add_edge("list_files", END)  # End after list_files execution

        # Define conditional edges from llm_decision
        workflow.add_conditional_edges(
            "llm_decision",
            self._decide_next_step,
            {
                "list_files": "list_files",  # Add this condition
                "get_sql_schema": "get_sql_schema",
                "execute_sql": "execute_sql",
                "query_csv_rag": "query_csv_rag",
                "end": END,  # If LLM decides to end or provide a direct answer
            },
        )

        return workflow.compile()

    async def _call_llm_decision_node(self, state: AgentState) -> AgentState:
        logger.info("LLM Decision Node: Deciding next action...")
        current_chat_history = state.get("chat_history", [])
        user_input = state.get("user_input", "")

        system_prompt = """You are a helpful assistant that can answer questions about data. You have access to tools to execute SQL queries against a SQLite database, to perform RAG (Retrieval Augmented Generation) on ingested data, and to list uploaded files.

Here's how you should operate:

1.  **To answer questions about your own capabilities (e.g., "What tools do you have?", "list available tools")**:
    *   Do not use a tool. Instead, provide a direct answer listing your available tools: `execute_sql`, `get_sql_schema`, `query_csv_rag`, `list_files`, and `ingest_data`.

2.  **To list uploaded files:**
    *   If the user asks to "list files", "show uploaded files", or similar, use the `list_files` tool.

3.  **For structured queries against database tables (e.g., "What is the average age?", "List all users from New York", "Show the first 10 rows of table X"):**
    *   First, use the `get_sql_schema` tool to understand the database structure (tables and columns).
    *   Then, formulate and execute an accurate SQL query using the `execute_sql` tool.
    *   Provide the answer based on the SQL query result.

4.  **For open-ended questions or when direct SQL might not be suitable (e.g., "Tell me about the data", "Summarize the key findings"):**
    *   Use the `query_csv_rag` tool to retrieve relevant information from the ingested data.
    *   Synthesize the retrieved information to answer the user's question.

Your response should indicate the `next_action` to take: `list_files`, `get_sql_schema`, `execute_sql`, `query_csv_rag`, or `end` (if you can answer directly or no further tool use is needed).
If `execute_sql` is the next action, provide the SQL query in the `sql_query` field.
If `query_csv_rag` is the next action, the `user_input` will be used as the query.
If `end` is the next action, provide the final answer in the `agent_outcome` field.
"""
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
            ]
        )

        # Get a fresh LLM instance for this call
        llm_instance = await self._get_llm_instance()

        # Bind tools to the LLM for tool calling
        llm_with_tools = llm_instance.bind_tools(self.tools)

        # Create a chain to get the LLM's decision
        decision_chain = prompt_template | llm_with_tools

        response = await decision_chain.ainvoke(
            {"input": user_input, "chat_history": current_chat_history}
        )

        # Parse the response to determine next_action and any tool calls
        tool_calls = response.tool_calls
        logger.debug(f"LLM response tool_calls: {tool_calls}")
        logger.debug(f"LLM response content: {response.content}")

        # Check if schema was already retrieved and avoid calling it again
        schema_info = state.get("schema_info")
        if schema_info and tool_calls and tool_calls[0]["name"] == "get_sql_schema":
            logger.warning(
                "Schema already retrieved, but LLM wants to call get_sql_schema again. Ending instead."
            )
            return {
                **state,
                "next_action": "end",
                "agent_outcome": f"Based on the schema information already retrieved, I can see the database structure. However, I need a more specific query to proceed. Please ask a specific question about the data.",
            }

        if tool_calls:
            # Assuming the LLM will call one of our tools
            tool_call = tool_calls[0]
            logger.info(f"Decision Node: Next action is {tool_call['name']}")
            if tool_call["name"] == "execute_sql":
                return {
                    **state,
                    "next_action": "execute_sql",
                    "sql_query": tool_call["args"]["query"],
                }
            elif tool_call["name"] == "get_sql_schema":
                return {**state, "next_action": "get_sql_schema"}
            elif tool_call["name"] == "query_csv_rag":
                return {**state, "next_action": "query_csv_rag"}
            elif tool_call["name"] == "list_files":
                return {**state, "next_action": "list_files"}

        # If no tool call, assume LLM is providing a direct answer or needs to end
        logger.info("Decision Node: No tool call, ending with direct response")
        return {
            **state,
            "next_action": "end",
            "agent_outcome": response.content
            or "I understand your question but need more specific information to proceed.",
        }

    def _parse_tool_result(self, tool_result: Any) -> Any:
        """Parses the tool result, handling nested lists and TextContent objects."""
        if isinstance(tool_result, list) and tool_result:
            content = tool_result[0]
        else:
            content = tool_result

        if hasattr(content, "content"):
            content = content.content

        if hasattr(content, "text"):
            content = content.text

        try:
            if isinstance(content, str):
                return json.loads(content)
            return content
        except (json.JSONDecodeError, TypeError):
            return content

    async def _call_get_sql_schema_tool_node(self, state: AgentState) -> AgentState:
        logger.info("Tool Node: Calling get_sql_schema tool...")
        tool_result = await self.tools[1].ainvoke(
            {}
        )  # get_mcp_sql_schema_tool_langchain is at index 1
        parsed_result = self._parse_tool_result(tool_result)

        schema_info = parsed_result.get("schemas") if parsed_result else None

        # If the user asked for the schema directly, end the turn.
        if any(
            keyword in state.get("user_input", "").lower()
            for keyword in ["tables", "schema"]
        ):
            if schema_info:
                return {
                    **state,
                    "agent_outcome": f"Database Schema:\n{schema_info}",
                    "next_action": "end",
                }
            else:
                return {
                    **state,
                    "agent_outcome": "There are no tables in the database yet.",
                    "next_action": "end",
                }

        # Otherwise, add the schema to the history and state, then continue.
        if schema_info:
            return {
                **state,
                "schema_info": schema_info,  # Store schema in state to avoid re-fetching
                "chat_history": state.get("chat_history", [])
                + [AIMessage(content=f"Database Schema: {schema_info}")],
                "next_action": "continue",
            }
        else:
            return {
                **state,
                "chat_history": state.get("chat_history", [])
                + [AIMessage(content="Could not retrieve database schema.")],
                "next_action": "continue",
            }

    def _decide_schema_next_step(self, state: AgentState) -> str:
        logger.info(f"Schema Decision Node: Next action is {state.get('next_action')}")
        return state.get("next_action", "end")

    async def _call_execute_sql_tool_node(self, state: AgentState) -> AgentState:
        logger.info(
            f"Tool Node: Calling execute_sql tool with query: {state.get('sql_query')}"
        )
        sql_query = state.get("sql_query")
        if not sql_query:
            return {
                **state,
                "agent_outcome": "Error: No SQL query provided to execute.",
                "next_action": "end",
            }

        tool_result = await self.tools[0].ainvoke({"query": sql_query})
        parsed_result = self._parse_tool_result(tool_result)

        if parsed_result and parsed_result.get("result"):
            return {
                **state,
                "query_result": parsed_result["result"],
                "agent_outcome": f"SQL Query Result: {parsed_result['result']}",
            }
        else:
            return {
                **state,
                "agent_outcome": f"Error executing SQL query: {parsed_result.get('error', 'Unknown error')}",
            }

    async def _call_query_csv_rag_tool_node(self, state: AgentState) -> AgentState:
        logger.info(
            f"Tool Node: Calling query_csv_rag tool with query: {state.get('user_input')}"
        )
        user_input = state.get("user_input")
        if not user_input:
            return {
                **state,
                "agent_outcome": "Error: No query provided for RAG.",
                "next_action": "end",
            }

        tool_result = await self.tools[2].ainvoke({"query": user_input})
        parsed_result = self._parse_tool_result(tool_result)

        if parsed_result and parsed_result.get("documents"):
            # ChromaDB returns documents as list of lists [[doc1, doc2, ...]]. Flatten it.
            documents = parsed_result["documents"]
            if documents and isinstance(documents[0], list):
                documents = documents[0]  # Get first (and only) query's results

            rag_docs = "\n\n".join(str(doc) for doc in documents)
            return {
                **state,
                "rag_documents": documents,
                "agent_outcome": f"Relevant Information from CSV: {rag_docs}",
            }
        else:
            return {
                **state,
                "agent_outcome": "No relevant information found in CSV data.",
            }

    def _decide_next_step(self, state: AgentState) -> str:
        logger.info(f"Decision Node: Next action is {state.get('next_action')}")
        return state.get("next_action", "end")

    async def arun(
        self, user_input: str, chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        current_chat_history = []
        if chat_history:
            for msg in chat_history:
                if msg.get("role") == "user":
                    current_chat_history.append(
                        HumanMessage(content=msg.get("content", ""))
                    )
                elif msg.get("role") == "assistant":
                    current_chat_history.append(
                        AIMessage(content=msg.get("content", ""))
                    )

        initial_state = {
            "user_input": user_input,
            "chat_history": current_chat_history,
            "sql_query": "",
            "query_result": "",
            "rag_documents": [],
            "next_action": "",
            "agent_outcome": "",
        }

        logger.info(f"Running Langchain agent with input: {user_input}")
        try:
            # Stream the output from the graph
            final_state = {}
            # Use ainvoke for a single run, astream is for streaming intermediate steps
            response = await self.app.ainvoke(initial_state)
            return {"output": response.get("agent_outcome", "No specific outcome.")}
        except Exception as e:
            logger.error(f"Error running Langchain agent: {e}", exc_info=True)
            return {"output": f"An error occurred: {e}"}

    async def _call_list_files_tool_node(self, state: AgentState) -> AgentState:
        logger.info("Tool Node: Calling list_files tool...")
        tool_result = await self.tools[3].ainvoke(
            {}
        )  # get_mcp_list_files_tool_langchain is at index 3
        parsed_result = self._parse_tool_result(tool_result)

        files_data = []
        if isinstance(parsed_result, dict) and "files" in parsed_result:
            for doc in parsed_result["files"]:
                try:
                    doc_str = (
                        doc if isinstance(doc, str) else getattr(doc, "text", str(doc))
                    )
                    files_data.append(json.loads(doc_str))
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Could not parse document: {doc}, error: {e}")

        if files_data:
            file_list = "\n".join(
                [f"- {f['file_name']} (table: {f['table_name']})" for f in files_data]
            )
            return {**state, "agent_outcome": f"Uploaded Files:\n{file_list}"}
        else:
            return {
                **state,
                "agent_outcome": "No files uploaded yet or error listing files.",
            }
