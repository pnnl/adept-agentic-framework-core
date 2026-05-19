from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn
import os
import uuid
import json
import asyncio
from typing import List, Dict, Any, Optional
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .auth import validate_jwt, AuthCredentials, JWTValidationError

# Load environment variables from .env file at the very beginning
load_dotenv()

from agentic_framework_pkg.scientific_workflow.langchain_agent import (
    ScientificWorkflowAgent,
)  # noqa: E402
from agentic_framework_pkg.logger_config import get_logger  # noqa: E402
from .stdio_tool_wrapper import create_stdio_tool, EchoToolSchema  # noqa: E402
from .external_tool_manager import ExternalToolManager

logger = get_logger(__name__)

tool_manager = ExternalToolManager()

# --- Authentication Setup ---
AUTH_ENABLED = os.getenv("AGENT_GATEWAY_AUTH_ENABLED", "false").lower() == "true"
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token", auto_error=False
)  # auto_error=False makes it optional


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[AuthCredentials]:
    if not AUTH_ENABLED:
        return None  # No auth, no user
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = await validate_jwt(token)
        return AuthCredentials(
            user_id=payload.get("sub"),
            username=payload.get("preferred_username"),
            groups=payload.get("groups", []),
            token=token,
        )
    except JWTValidationError as e:
        raise HTTPException(status_code=401, detail=str(e))


# --- FastAPI App Initialization ---
app = FastAPI(
    title="Agent Gateway",
    description="A unified, OpenAI-compatible entry point for interacting with various agentic framework configurations. This gateway allows external clients like OpenWebUI and n8n to use the framework's agents without needing to understand the internal architecture.",
    version="1.0.0",
)

# --- Agent Configurations ---
# This dictionary defines the different "models" or agent personalities that this gateway exposes.
# The key is the model ID that clients will use. The value contains the settings needed to
# initialize the ScientificWorkflowAgent for that specific personality.
AGENT_CONFIGURATIONS = {
    "agentic-framework/scientific-agent-v1": {
        "description": "Default scientific agent with all tools enabled, including a sample stdio echo tool.",
        "agent_class": ScientificWorkflowAgent,
        "system_prompt": None,  # Use the default system prompt from the agent class
        "stdio_tools": [
            {
                "name": "echo_message_tool",
                "description": "A simple tool that echoes back a message. Useful for testing the stdio tool integration.",
                "command": ["python3", "tools/echo_tool.py"],
                "working_directory": "/app/agentic_framework_pkg/agent_gateway",  # Relative to container's /app
                "args_schema": EchoToolSchema,
            }
        ],
    },
    "agentic-framework/n8n-summary-agent": {
        "description": "A specialized agent with a system prompt optimized for summarizing data and providing concise answers suitable for n8n workflows.",
        "agent_class": ScientificWorkflowAgent,
        "system_prompt": "You are an expert summarization agent. Your goal is to provide clear, concise summaries of the information you find. Do not provide long explanations or conversational filler. Your output will be used in automated workflows.",
        "stdio_tools": [],  # No stdio tools for this agent
    },
}


# CORS Configuration
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:8081",
    "http://localhost:8083",
    "http://localhost:8902",
    "http://127.0.0.1",
    "http://127.0.0.1:8902",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8081",
    "http://127.0.0.1:8082",
    "http://host.docker.internal",
    "http://host.docker.internal:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """
    Initializes the global tool_manager's Redis connection on application startup.
    This ensures that the ExternalToolManager's Redis client is connected
    and tools are loaded from Redis before the application starts serving requests.
    """
    await tool_manager.connect_redis()


sessions: Dict[str, Any] = {}


def format_sse_chunk(data: Dict[str, Any]) -> str:
    return f"data: {json.dumps(data)}\n\n"


@app.get("/v1/models", summary="List Available Agent Models")
async def list_models():
    """
    Provides a list of available agent configurations that can be used.
    This endpoint adheres to the OpenAI `/v1/models` specification, allowing
    clients like OpenWebUI and n8n to discover and select from the available agents.
    """
    logger.info("Received request on /v1/models")

    model_list = []
    for model_id, config in AGENT_CONFIGURATIONS.items():
        model_entry = {
            "id": model_id,
            "object": "model",
            "created": int(os.path.getctime(__file__)),
            "owned_by": "AgenticFramework",
            "description": config.get("description"),
        }
        model_list.append(model_entry)

    response_data = {
        "object": "list",
        "data": model_list,
    }

    logger.info(f"Sending models response: {response_data}")
    return JSONResponse(content=response_data)


@app.get("/v1/models/{model_id}", summary="Retrieve a specific agent model")
async def get_model(model_id: str):
    """
    Provides details for a single agent model configuration.
    This endpoint adheres to the OpenAI `/v1/models/{model}` specification.
    """
    logger.info(f"Received request on /v1/models/{model_id}")

    if model_id not in AGENT_CONFIGURATIONS:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")

    config = AGENT_CONFIGURATIONS[model_id]
    model_entry = {
        "id": model_id,
        "object": "model",
        "created": int(os.path.getctime(__file__)),
        "owned_by": "AgenticFramework",
        "description": config.get("description"),
    }

    logger.info(f"Sending model response: {model_entry}")
    return JSONResponse(content=model_entry)


@app.get("/tools/{model_id}", summary="Discover Agent Tools")
async def get_agent_tools(model_id: str):
    """
    A custom, unified REST endpoint to make an agent's capabilities discoverable.

    This endpoint provides a standardized way for any client (n8n, developers, etc.)
    to programmatically query the toolset of a specific agent configuration.

    **Compatibility:**
    - **n8n:** Can use its `HTTP Request` node to call this endpoint and parse the
      standard JSON response to inform workflow logic.
    - **OpenWebUI Users/Admins:** Provides a clear, human-readable way to see what
      a selected agent model can do, aiding in prompt engineering and debugging.
    - **MCP:** This is NOT an MCP endpoint. It is a standard REST endpoint that
      *reports on* an agent's tools, some of which may be MCP tools. It acts as
      an adapter, translating the internal toolset into a simple, public-facing
      JSON format.
    """
    logger.info(f"Received request on /tools/{model_id}")
    logger.info(
        f"model_id (type): {type(model_id)}, (repr): {repr(model_id)}, length: {len(model_id)}"
    )

    config_keys = list(AGENT_CONFIGURATIONS.keys())
    logger.info(
        f"AGENT_CONFIGURATIONS keys (types): {[type(k) for k in config_keys]}, (repr): {[repr(k) for k in config_keys]}, lengths: {[len(k) for k in config_keys]}"
    )
    logger.info(f"model_id in AGENT_CONFIGURATIONS: {model_id in AGENT_CONFIGURATIONS}")

    if model_id not in AGENT_CONFIGURATIONS:
        logger.error(f"Model '{model_id}' not found in AGENT_CONFIGURATIONS.")
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")

    try:
        config = AGENT_CONFIGURATIONS[model_id]

        # Create stdio tools if configured
        additional_tools = []
        if "stdio_tools" in config:
            for tool_config in config["stdio_tools"]:
                stdio_tool = create_stdio_tool(**tool_config)
                additional_tools.append(stdio_tool)

        # Add externally registered tools
        additional_tools.extend(tool_manager.get_all_tools())

        # Temporarily instantiate the agent to inspect its tools
        agent_instance = config["agent_class"](
            mcp_session_id="dummy_session_for_inspection",
            additional_tools=additional_tools,
        )

        tools_list = []
        for tool in agent_instance.tools:
            tool_details = {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.args_schema.schema() if tool.args_schema else {},
            }
            tools_list.append(tool_details)

        return JSONResponse(content={"model_id": model_id, "tools": tools_list})

    except Exception as e:
        logger.error(
            f"Failed to inspect tools for model {model_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve agent tools.")


@app.post("/v1/tools/register", summary="Register an External Tool")
async def register_tool(request: Request):
    """
    Dynamically registers an external tool with the gateway using a
    protocol-agnostic schema. This endpoint allows administrators to extend the
    agent's capabilities without restarting the server.

    The request body must be a JSON object that defines the tool's properties,
    including its invocation method and access control list.

    ### Example Payloads:

    **1. HTTP Tool Registration:**
    ```json
    {
      "name": "protein_sequence_fetcher",
      "description": "Fetches protein sequence data from an external API.",
      "args_schema": {
        "uniprot_id": {
          "type": "string",
          "description": "The UniProt accession ID (e.g., 'P0DTD1')."
        }
      },
      "invocation": {
        "protocol": "http",
        "connection": {
          "url": "https://api.example.com/proteins/fetch",
          "method": "GET",
          "headers": {
            "X-API-Key": "your-secret-api-key"
          }
        }
      },
      "acl": {
        "global": false,
        "groups": ["bioinformatics_team"]
      }
    }
    ```

    **2. Docker `run` stdio Tool Registration:**
    ```json
    {
      "name": "my_docker_tool",
      "description": "A tool that runs a command inside a Docker container.",
      "args_schema": {
        "input_arg": {
          "type": "string",
          "description": "An input argument for the tool."
        }
      },
      "invocation": {
        "protocol": "stdio",
        "connection": {
          "command": ["docker", "run", "--rm", "-i", "my_docker_image:latest", "my_tool_command"]
        }
      },
      "acl": {
        "global": true
      }
    }
    ```

    **3. Docker MCP Toolkit `gateway run` stdio Tool Registration:**
    ```json
    {
      "name": "my_mcp_toolkit_tool",
      "description": "A tool that uses the Docker MCP toolkit to run a gateway command.",
      "args_schema": {
        "mcp_tool_name": {
          "type": "string",
          "description": "The name of the MCP tool to invoke."
        },
        "mcp_tool_args": {
          "type": "object",
          "description": "The arguments for the MCP tool."
        }
      },
      "invocation": {
        "protocol": "stdio",
        "connection": {
          "command": ["docker", "mcp", "gateway", "run"]
        }
      },
      "acl": {
        "global": true
      }
    }
    ```
    """
    try:
        config = await request.json()
        await tool_manager.register_tool(config)
        protocol = config.get("invocation", {}).get("protocol", "unknown")
        return JSONResponse(
            content={
                "status": "success",
                "message": f"Tool '{config.get('name')}' registered successfully using protocol '{protocol}'.",
            }
        )
    except ValueError as e:
        logger.error(f"Invalid tool registration config: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to register external tool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to register tool. {e}")


@app.post("/v1/chat/completions", summary="Process Chat Request")
async def chat_completions(
    request: Request,
    current_user: Optional[AuthCredentials] = Depends(get_current_user),
):
    """
    The main chat endpoint, compatible with the OpenAI `/v1/chat/completions` API.

    This endpoint is the primary entry point for all agent interactions. It orchestrates
    the entire lifecycle of a request, from receiving a user's query to returning a
    final, streamed response. It acts as a dynamic factory for the `ScientificWorkflowAgent`.

    ### Architectural Flow:

    ```
    User Request ----------------> Agent Gateway (/v1/chat/completions)
                                         |
               +-------------------------+-------------------------+
               | 1. Authenticate User                            |
               |                                                 |
               | 2. Call ExternalToolManager.get_authorized_tools() |
               |    (Queries DB, filters by ACL)                 |
               |                                                 |
               | 3. Create LangChain Tool objects (HTTP or stdio) |
               |                                                 |
               | 4. Instantiate ScientificWorkflowAgent          |
               |    with the list of authorized Tool objects     |
               +-------------------------+-------------------------+
                                         |
                                         V
    ScientificWorkflowAgent (now has its tools) <-----> LangGraph Runtime
               ^                                                 |
               | (Tool Result)                                   V (LLM decides to use a tool)
               |                                                 |
               +------------------ Tool._arun() is called <-------+
                                         |
                     +-------------------+-------------------+
                     |                                       |
     V (HTTP Request)                                V (stdio Subprocess)
                     |                                       |
             External HTTP Service                  Docker Container / Local Command
    ```

    1.  **Authentication and Authorization:**
        - The endpoint first uses the `get_current_user` dependency to validate the
          incoming JWT (if authentication is enabled). This step is crucial for
          identifying the user and their group memberships, which are used to
          enforce tool access control.

    2.  **Session and Agent Scoping:**
        - It checks for an existing agent instance tied to the `conversation_id`.
        - If no agent exists for the session, or if the requested `model` has changed,
          it begins the process of creating a new `ScientificWorkflowAgent`.

    3.  **Dynamic Tool Provisioning:**
        - This is the core of the dynamic agent architecture. Before creating the
          agent, the gateway gathers all the tools the agent will be allowed to use.
        - It starts with any static tools defined in `AGENT_CONFIGURATIONS` (e.g.,
          the `echo_message_tool`).
        - It then calls `tool_manager.get_authorized_tools()`, passing the user's
          ID and groups. The `ExternalToolManager` queries its database for all
          registered external tools (both HTTP and stdio types) and filters them
          based on the user's permissions defined in each tool's Access Control
          List (ACL).
        - For each authorized tool configuration, the `ExternalToolManager` creates
          a fully-formed, LangChain-compatible `Tool` object.

    4.  **Agent Instantiation:**
        - A new `ScientificWorkflowAgent` instance is created. The list of authorized
          `Tool` objects is passed directly to its constructor.
        - This means the agent instance is "born" with a toolset tailored specifically
          for the current user and session. It does not need to know about the
          `ExternalToolManager` or the tool registration process; it only knows
          the tools it was given.

    5.  **Execution and Streaming:**
        - The user's query is passed to the agent's `arun` method.
        - The agent, managed by a LangGraph runtime, uses the LLM to reason about the
          user's request and its available tools.
        - When the LLM decides to use a tool, LangGraph invokes the corresponding `Tool`
          object. The tool's internal logic (e.g., making an HTTP request or
          executing a `docker run` command) is completely abstracted away from the agent.
        - The final response from the agent is streamed back to the client in the
          OpenAI-compatible Server-Sent Events (SSE) format.

    If authentication is enabled, this endpoint requires a valid JWT.
    """
    try:
        body = await request.json()
        logger.info(f"Received request on /v1/chat/completions: {body}")

        model_id = body.get("model")
        if not model_id or model_id not in AGENT_CONFIGURATIONS:
            available_models = list(AGENT_CONFIGURATIONS.keys())
            raise HTTPException(
                status_code=400,
                detail=f"Invalid or missing model ID. Available models: {available_models}",
            )

        messages = body.get("messages", [])
        if not messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        user_message = messages[-1]["content"]
        chat_history_from_request = messages[:-1]
        conversation_id = body.get("conversation_id", str(uuid.uuid4()))
        stream_requested = body.get("stream", False)

        if (
            conversation_id not in sessions
            or sessions[conversation_id].get("model_id") != model_id
        ):
            logger.info(
                f"New conversation for model '{model_id}'. Session ID: {conversation_id}"
            )
            config = AGENT_CONFIGURATIONS[model_id]

            # Create stdio tools if configured
            additional_tools = []
            if "stdio_tools" in config:
                for tool_config in config["stdio_tools"]:
                    stdio_tool = create_stdio_tool(**tool_config)
                    additional_tools.append(stdio_tool)

            # Add externally registered tools based on user's ACL
            if current_user:
                authorized_tools = await tool_manager.get_authorized_tools(
                    current_user.user_id, current_user.groups
                )
                additional_tools.extend(authorized_tools)
            else:
                # If auth is disabled or no user, get only global tools
                global_tools = await tool_manager.get_authorized_tools(None, [])
                additional_tools.extend(global_tools)

            agent = config["agent_class"](
                mcp_session_id=conversation_id, additional_tools=additional_tools
            )

            if config.get("system_prompt"):
                agent.formatted_system_prompt = config["system_prompt"]

            sessions[conversation_id] = {
                "agent": agent,
                "model_id": model_id,
            }
        else:
            agent = sessions[conversation_id]["agent"]

        async def generate_response_chunks():
            # Create and yield the initial chunk
            initial_chunk = {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion.chunk",
                "created": int(os.path.getctime(__file__)),
                "model": model_id,
                "choices": [
                    {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}
                ],
            }
            yield format_sse_chunk(initial_chunk)

            # Get the full response from the agent
            response_dict = await agent.arun(
                user_input=user_message, chat_history=chat_history_from_request
            )
            agent_response = response_dict.get(
                "output", "Agent did not provide a standard output."
            )

            # Stream the response character by character
            for char in agent_response:
                char_chunk = {
                    "id": f"chatcmpl-{uuid.uuid4()}",
                    "object": "chat.completion.chunk",
                    "created": int(os.path.getctime(__file__)),
                    "model": model_id,
                    "choices": [
                        {"index": 0, "delta": {"content": char}, "finish_reason": None}
                    ],
                }
                yield format_sse_chunk(char_chunk)
                await asyncio.sleep(0.01)

            # Create and yield the final chunk
            final_chunk = {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion.chunk",
                "created": int(os.path.getctime(__file__)),
                "model": model_id,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": len(user_message.split()),
                    "completion_tokens": len(agent_response.split()),
                    "total_tokens": len(user_message.split())
                    + len(agent_response.split()),
                },
            }
            yield format_sse_chunk(final_chunk)
            yield "data: [DONE]\n\n"

        if stream_requested:
            return StreamingResponse(
                generate_response_chunks(), media_type="text/event-stream"
            )
        else:
            response_dict = await agent.arun(
                user_input=user_message, chat_history=chat_history_from_request
            )
            agent_response = response_dict.get(
                "output", "Agent did not provide a standard output."
            )

            response_data = {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(os.path.getctime(__file__)),
                "model": model_id,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": agent_response},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            }
            logger.info(f"Sending non-streamed response: {response_data}")
            return JSONResponse(content=response_data)

    except Exception as e:
        logger.error(f"Error in /v1/chat/completions: {e}", exc_info=True)
        return JSONResponse(content={"detail": str(e)}, status_code=500)


if __name__ == "__main__":
    port = int(os.getenv("AGENT_GATEWAY_PORT", "8081"))
    uvicorn.run(app, host="0.0.0.0", port=port)
