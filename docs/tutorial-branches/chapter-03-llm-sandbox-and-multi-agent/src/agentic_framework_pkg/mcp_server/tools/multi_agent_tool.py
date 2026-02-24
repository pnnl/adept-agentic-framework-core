import asyncio
import uuid
from typing import Dict, Any, Optional, List, Tuple

from fastmcp import FastMCP, Context
from ...logger_config import get_logger
from ...core.llm_agnostic_layer import LLMAgnosticClient

# LangGraph and LangChain imports
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain.tools import BaseTool
from langgraph.prebuilt import create_react_agent

# Import all the tool wrappers to give to the dynamic agents
from ...scientific_workflow.mcp_langchain_tools import (
    get_mcp_query_csv_tool_langchain,
    get_mcp_perform_calculation_tool_langchain,
    get_mcp_store_note_tool_langchain,
    get_mcp_retrieve_notes_tool_langchain,
    get_mcp_query_uniprot_tool_langchain,
    get_mcp_web_search_api_tool_langchain,
    get_mcp_web_search_scraping_tool_langchain,
    get_mcp_blastp_biopython_tool_langchain,
    get_mcp_blastn_biopython_tool_langchain,
    get_mcp_search_pubchem_by_name_tool_langchain,
    get_mcp_get_pubchem_compound_properties_tool_langchain,
    get_mcp_list_uploaded_files_tool_langchain,
    get_mcp_alphafold_prediction_tool_langchain,
    get_mcp_query_stored_alphafold_tool_langchain,
    get_mcp_run_nextflow_blast_tool_langchain,
    get_mcp_run_video_transcription_tool_langchain,
    get_mcp_execute_code_tool_langchain,
    get_mcp_gitxray_scan_tool_langchain,
    get_mcp_test_hpc_connection_tool_langchain,
    get_mcp_submit_slurm_job_tool_langchain,
    get_mcp_check_slurm_job_status_tool_langchain,
    # SQL / Knowledge-base tools
    get_mcp_ingest_data_tool_langchain,
    get_mcp_sql_schema_tool_langchain,
    get_mcp_sql_tool_langchain,
    get_mcp_rag_query_tool_langchain,
    get_mcp_list_ingested_files_tool_langchain,
)

logger = get_logger(__name__)

# In-memory store for multi-agent sessions.
# In a production system, this would be a database (Redis, PostgreSQL, etc.)
MULTI_AGENT_SESSIONS: Dict[str, Any] = {}

# Global LLM client instance, to be set by register_tools
_llm_agnostic_client_instance: Optional[LLMAgnosticClient] = None


def get_all_mcp_tools(session_id: str) -> List[BaseTool]:
    """Factory function to get a list of all available MCP tools."""
    tool_factories = [
        get_mcp_query_csv_tool_langchain,
        get_mcp_perform_calculation_tool_langchain,
        get_mcp_store_note_tool_langchain,
        get_mcp_retrieve_notes_tool_langchain,
        get_mcp_query_uniprot_tool_langchain,
        get_mcp_web_search_api_tool_langchain,
        get_mcp_web_search_scraping_tool_langchain,
        get_mcp_blastp_biopython_tool_langchain,
        get_mcp_blastn_biopython_tool_langchain,
        get_mcp_search_pubchem_by_name_tool_langchain,
        get_mcp_get_pubchem_compound_properties_tool_langchain,
        get_mcp_list_uploaded_files_tool_langchain,
        get_mcp_alphafold_prediction_tool_langchain,
        get_mcp_query_stored_alphafold_tool_langchain,
        get_mcp_run_nextflow_blast_tool_langchain,
        get_mcp_run_video_transcription_tool_langchain,
        get_mcp_execute_code_tool_langchain,
        get_mcp_gitxray_scan_tool_langchain,
        get_mcp_test_hpc_connection_tool_langchain,
        get_mcp_submit_slurm_job_tool_langchain,
        get_mcp_check_slurm_job_status_tool_langchain,
        # SQL / Knowledge-base tools
        get_mcp_ingest_data_tool_langchain,
        get_mcp_sql_schema_tool_langchain,
        get_mcp_sql_tool_langchain,
        get_mcp_rag_query_tool_langchain,
        get_mcp_list_ingested_files_tool_langchain,
    ]
    return [factory(mcp_session_id=session_id) for factory in tool_factories]


def create_worker_agent(role: str, session_id: str) -> Tuple[Any, str]:
    """Creates a worker agent with a specific role and access to all tools."""
    llm = _llm_agnostic_client_instance.get_langchain_chat_model(
        llm_purpose="agent_worker"
    )
    tools = get_all_mcp_tools(session_id)
    prompt = SystemMessage(
        content=f"You are a world-class expert {role}. You must use the provided tools to complete the tasks assigned to you. Do not make up information. Fulfill the task to the best of your ability."
    )
    agent_graph = create_react_agent(model=llm, tools=tools, prompt=prompt)
    return agent_graph, role


class AgentRunnerTool(BaseTool):
    """A tool that allows the supervisor to run a worker agent."""

    agent_executor: Any
    name: str
    description: str

    def _run(self, task: str) -> str:
        """Runs the agent with the given task synchronously."""
        # This synchronous wrapper is required by the BaseTool interface.
        # It handles cases where an event loop is already running.
        try:
            return asyncio.run(self._arun(task))
        except RuntimeError as e:
            if "cannot be called when another loop is running" in str(e):
                logger.warning(
                    "Asyncio loop issue in AgentRunnerTool._run, trying nest_asyncio."
                )
                import nest_asyncio

                nest_asyncio.apply()
                return asyncio.run(self._arun(task))
            raise e

    async def _arun(self, task: str) -> str:
        """
        Runs the agent with the given task, streaming its execution steps to build a
        detailed report for the supervisor.
        """
        logger.info(f"Supervisor delegating task to {self.name}: {task}")
        try:
            final_state = {}
            # Use astream to get the full history. We iterate through the stream and only
            # care about the final state, which contains the complete message history.
            async for state in self.agent_executor.astream(
                {"messages": [HumanMessage(content=task)]}
            ):
                final_state = state

            messages = final_state.get("messages", [])
            if not messages or len(messages) <= 1:
                return (
                    f"The {self.name} agent produced no meaningful output for the task."
                )

            report_parts = [f"Execution trace for worker agent '{self.name}':"]
            last_tool_name = "unknown_tool"
            for msg in messages[1:]:  # Skip initial HumanMessage
                if isinstance(msg, AIMessage):
                    if msg.content:
                        thought = msg.content.replace("\n", " ").strip()
                        if thought:
                            report_parts.append(f"  - Thought: {thought}")
                    if msg.tool_calls:
                        for tc in msg.tool_calls:
                            last_tool_name = tc.get("name", "unknown_tool")
                            report_parts.append(
                                f"  - Action: Calling tool `{last_tool_name}` with arguments `{tc.get('args', {})}`."
                            )
                elif isinstance(msg, ToolMessage):
                    observation = str(msg.content).replace("\n", " ").strip()
                    if len(observation) > 300:  # Truncate long observations for clarity
                        observation = observation[:300] + "..."
                    report_parts.append(
                        f"  - Observation from `{last_tool_name}`: {observation}"
                    )

            final_answer_msg = messages[-1]
            if (
                isinstance(final_answer_msg, AIMessage)
                and not final_answer_msg.tool_calls
            ):
                report_parts.append(
                    f"\nFinal Answer from worker: {final_answer_msg.content}"
                )

            return "\n".join(report_parts)
        except Exception as e:
            # If the worker agent fails, report the failure back to the supervisor.
            logger.error(
                f"Worker agent {self.name} failed to execute task '{task[:50]}...'. Error: {e}",
                exc_info=True,
            )
            return f"The {self.name} agent FAILED to complete the task. Error: {e}"


def create_planner_agent(roles: List[str]) -> Any:
    """Creates the planner agent. It has no tools and its only job is to create a plan."""
    llm = _llm_agnostic_client_instance.get_langchain_chat_model(
        llm_purpose="agent_planner"
    )

    role_descriptions = ", ".join(roles)

    planner_prompt = (
        "You are an expert planner. Your job is to create a detailed, step-by-step plan to answer a user's request. "
        "You have a team of experts available with the following roles: {roles}. "
        "For each step in the plan, specify which expert role should perform the task. "
        "The plan will be executed by a supervisor agent. Do not try to execute the plan yourself or generate a final answer. "
        "Your only output should be the plan."
    ).format(roles=role_descriptions)

    # The planner is a simple LLM call, but we can wrap it in the agent interface for consistency. It has no tools.
    return create_react_agent(
        model=llm, tools=[], prompt=SystemMessage(content=planner_prompt)
    )


def create_supervisor_agent(
    worker_agents: List[Tuple[Any, str]], session_id: str
) -> Any:
    """Creates the supervisor agent whose tools are the worker agents."""
    llm = _llm_agnostic_client_instance.get_langchain_chat_model(
        llm_purpose="agent_supervisor"
    )

    worker_tools = []
    for agent_executor, role in worker_agents:
        tool = AgentRunnerTool(
            name=f"run_{role.lower().replace(' ', '_')}_agent",
            description=f"Use this tool to delegate a specific task to the {role} expert. Provide a clear and complete description of the task for the expert.",
            agent_executor=agent_executor,
        )
        worker_tools.append(tool)

    system_prompt = (
        "You are a supervisor agent. Your job is to orchestrate a team of expert agents to complete a user's request based on a provided plan. "
        "You have access to the conversation history, which you can use for context from previous tasks in this session. "
        "You will be given a high-level task and a step-by-step plan. You must execute the plan by delegating each step to the appropriate expert agent using your tools. "
        "Do not deviate from the plan. "
        "After executing all steps, synthesize the results from the workers into a single, comprehensive final report. "
        "If a worker agent returns a message indicating it FAILED, you must acknowledge this failure. "
        "Analyze the error message. If the error suggests missing information that the user could provide (e.g., an ambiguous term, a missing file ID), "
        "your final report should clearly state the failure and ask the user for the specific information needed to resolve the issue. "
        "Otherwise, simply report the failure as part of the final results. "
        "Do not use your own knowledge; rely solely on the outputs of the worker agents."
    )

    return create_react_agent(
        model=llm, tools=worker_tools, prompt=SystemMessage(content=system_prompt)
    )


def register_tools(mcp: FastMCP, llm_client: LLMAgnosticClient):
    global _llm_agnostic_client_instance
    _llm_agnostic_client_instance = llm_client

    @mcp.tool()
    async def create_multi_agent_session(
        ctx: Context, roles: List[str], mcp_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a new multi-agent session with a supervisor and worker agents for the specified roles."""
        session_id = f"multi-agent-{uuid.uuid4()}"
        await ctx.info(
            f"Creating new multi-agent session {session_id} for roles: {roles}"
        )

        try:
            worker_agents = [
                create_worker_agent(role, mcp_session_id) for role in roles
            ]
            supervisor_agent = create_supervisor_agent(worker_agents, mcp_session_id)
            planner_agent = create_planner_agent(roles)

            MULTI_AGENT_SESSIONS[session_id] = {
                "supervisor": supervisor_agent,
                "planner": planner_agent,
                "roles": roles,
                "chat_history": [],  # Initialize an empty chat history for the session
            }

            await ctx.info(f"Multi-agent session {session_id} created successfully.")
            return {
                "status": "success",
                "multi_agent_session_id": session_id,
                "message": f"Successfully created session with workers: {', '.join(roles)}.",
            }
        except Exception as e:
            logger.error(f"Failed to create multi-agent session: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    @mcp.tool()
    async def generate_plan_for_multi_agent_task(
        ctx: Context,
        multi_agent_session_id: str,
        task: str,
        mcp_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates a plan for a task in a multi-agent session. The plan must be approved by the user before execution.
        This is the first step in a two-step process. After approval, use 'execute_approved_plan_in_session'.
        """
        await ctx.info(
            f"Received task to generate plan for multi-agent session {multi_agent_session_id}: {task}"
        )

        session = MULTI_AGENT_SESSIONS.get(multi_agent_session_id)
        if not session or not session.get("supervisor") or not session.get("planner"):
            await ctx.error(
                f"Multi-agent session {multi_agent_session_id} not found or is invalid."
            )
            return {
                "status": "error",
                "message": "Session not found. Please create a session first.",
            }

        planner = session["planner"]
        chat_history = session.get(
            "chat_history", []
        )  # Retrieve the session's chat history

        try:
            # Step 1: Invoke the planner to get a plan
            await ctx.info(f"Invoking planner for task...")
            planner_messages = chat_history + [HumanMessage(content=task)]
            plan_result = await planner.ainvoke({"messages": planner_messages})
            generated_plan = plan_result.get("messages", [])[-1].content
            await ctx.info(f"Planner generated plan: {generated_plan}")

            # Store the plan and task for later execution
            session["pending_plan"] = {"task": task, "plan": generated_plan}

            return {
                "status": "plan_generated_for_approval",
                "plan": generated_plan,
                "message": "The plan has been generated. Please review and use 'execute_approved_plan_in_session' to proceed.",
            }
        except Exception as e:
            logger.error(
                f"Error during plan generation in session {multi_agent_session_id}: {e}",
                exc_info=True,
            )
            return {"status": "error", "message": str(e)}

    @mcp.tool()
    async def execute_approved_plan_in_session(
        ctx: Context, multi_agent_session_id: str, mcp_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes the previously generated and approved plan in a multi-agent session."""
        await ctx.info(
            f"Received request to execute approved plan for multi-agent session {multi_agent_session_id}"
        )

        session = MULTI_AGENT_SESSIONS.get(multi_agent_session_id)
        if not session or not session.get("supervisor"):
            await ctx.error(
                f"Multi-agent session {multi_agent_session_id} not found or is invalid."
            )
            return {"status": "error", "message": "Session not found or is invalid."}

        if "pending_plan" not in session:
            await ctx.error(
                f"No pending plan found in session {multi_agent_session_id} to execute."
            )
            return {
                "status": "error",
                "message": "No pending plan found to execute. Please generate a plan first.",
            }

        pending_plan = session.pop("pending_plan")  # Consume the plan
        task = pending_plan["task"]
        generated_plan = pending_plan["plan"]

        supervisor = session["supervisor"]
        chat_history = session.get("chat_history", [])

        try:
            supervisor_task_with_plan = (
                f"Here is the user's overall task: '{task}'\n\n"
                f"Here is the plan you must follow to achieve it:\n{generated_plan}\n\n"
                "Please execute this plan and provide a final report."
            )
            await ctx.info(f"Invoking supervisor with plan...")
            supervisor_messages = chat_history + [
                HumanMessage(content=supervisor_task_with_plan)
            ]
            result = await supervisor.ainvoke({"messages": supervisor_messages})
            final_response = result.get("messages", [])[-1].content

            await ctx.info(f"Supervisor completed task. Final response generated.")

            # Update the session's chat history with the latest interaction
            session["chat_history"].append(
                HumanMessage(content=task)
            )  # Log the original task
            session["chat_history"].append(AIMessage(content=final_response))

            return {"status": "success", "report": final_response}
        except Exception as e:
            logger.error(
                f"Error during multi-agent task execution in session {multi_agent_session_id}: {e}",
                exc_info=True,
            )
            # Put the plan back if execution fails? Maybe not, to avoid retrying a broken plan.
            return {"status": "error", "message": str(e)}

    @mcp.tool()
    async def update_pending_plan_in_session(
        ctx: Context,
        multi_agent_session_id: str,
        edited_plan: str,
        mcp_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Updates the pending plan in a multi-agent session with a user-edited version before execution."""
        await ctx.info(
            f"Received request to update pending plan for multi-agent session {multi_agent_session_id}"
        )

        session = MULTI_AGENT_SESSIONS.get(multi_agent_session_id)
        if not session:
            await ctx.error(f"Multi-agent session {multi_agent_session_id} not found.")
            return {"status": "error", "message": "Session not found."}

        if "pending_plan" not in session:
            await ctx.error(
                f"No pending plan found in session {multi_agent_session_id} to update."
            )
            return {
                "status": "error",
                "message": "No pending plan found to update. Please generate a plan first.",
            }

        # Update the plan part of the pending_plan dictionary
        session["pending_plan"]["plan"] = edited_plan

        await ctx.info(
            f"Successfully updated pending plan for session {multi_agent_session_id}."
        )
        return {
            "status": "success",
            "message": "The pending plan has been successfully updated. You can now execute it.",
            "updated_plan": edited_plan,
        }

    @mcp.tool()
    async def list_active_multi_agent_sessions(
        ctx: Context, mcp_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lists all currently active multi-agent sessions and their roles."""
        await ctx.info("Received request to list active multi-agent sessions.")

        if not MULTI_AGENT_SESSIONS:
            return {
                "active_sessions": [],
                "message": "No active multi-agent sessions found.",
            }

        active_sessions_list = []
        for session_id, session_data in MULTI_AGENT_SESSIONS.items():
            active_sessions_list.append(
                {
                    "multi_agent_session_id": session_id,
                    "roles": session_data.get("roles", []),
                    "history_length": len(session_data.get("chat_history", [])),
                }
            )

        return {"active_sessions": active_sessions_list}

    @mcp.tool()
    async def terminate_multi_agent_session(
        ctx: Context, multi_agent_session_id: str, mcp_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Terminates a multi-agent session and cleans up its resources."""
        await ctx.info(
            f"Received request to terminate multi-agent session {multi_agent_session_id}"
        )

        if multi_agent_session_id in MULTI_AGENT_SESSIONS:
            del MULTI_AGENT_SESSIONS[multi_agent_session_id]
            await ctx.info(
                f"Successfully terminated multi-agent session {multi_agent_session_id}."
            )
            return {
                "status": "success",
                "message": f"Session {multi_agent_session_id} has been terminated.",
            }
        else:
            await ctx.warning(
                f"Attempted to terminate non-existent multi-agent session {multi_agent_session_id}."
            )
            return {
                "status": "error",
                "message": f"Session {multi_agent_session_id} not found.",
            }

    logger.info("Multi-Agent MCP tools registered.")
