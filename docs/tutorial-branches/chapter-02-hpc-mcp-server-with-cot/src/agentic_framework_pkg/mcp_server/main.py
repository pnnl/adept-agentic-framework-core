import uvicorn
import asyncio
import os
from dotenv import load_dotenv
from fastapi import Request, FastAPI
import json  # Ensure json is imported if not already for the refined middleware

# Load environment variables from.env file for local development
# In Docker, env vars are passed through docker-compose.yml
if os.path.exists(".env"):
    load_dotenv()

from .server import mcp
from .state_manager import initialize_db
from .tools import (
    general_tools,
    csv_rag_tool,
    uniprot_tool,
    websearch_tool,
    blastq_tool,
    pubchem_tool,
    alphafold_tool,
)  # Added alphafold_tool
from ..core.llm_agnostic_layer import LLMAgnosticClient
from ..logger_config import get_logger  # Use centralized logger

# Configure logging
logger = get_logger(__name__)  # Gets logger with default level from logger_config


# Define the middleware function (will be applied later)
async def log_request_middleware(request: Request, call_next):
    """Log incoming requests and their metadata.

    Args:
        request (Request): The incoming request object.
        call_next (_type_): The next middleware or request handler.

    Returns:
        _type_: The response from the next middleware or request handler.
    """

    # logger.info(f"Incoming request: {request.method} {request.url} from {request.client.host}"). # Uncomment to log request method, URL, and client host

    # Note: Uncomment the next line if you want to log headers, but be cautious with sensitive data.
    # This is useful for debugging anything related to headers for any of the MCP tool servers.
    # I've used this to debug issues with Claude's expectations around headers and integration with local or remote
    # MCP servers.

    # logger.debug(f"Request Headers: {dict(request.headers)}"). # Uncomment to log headers

    # Read the full request body once. This consumes the original stream but caches it.
    req_body_bytes = await request.body()

    if req_body_bytes:
        try:
            # Attempt to parse as JSON for logging
            body_json = json.loads(req_body_bytes.decode("utf-8"))
            logger.info(f"Request body (parsed as JSON): {body_json}")
        except json.JSONDecodeError:
            logger.info(
                f"Request body (raw, not JSON): {req_body_bytes[:500].decode(errors='ignore')}..."
            )
        except UnicodeDecodeError:  # Handle cases where body is not valid UTF-8
            logger.info(
                f"Request body (raw, non-UTF-8): {req_body_bytes[:500]}..."
            )  # Log raw bytes
    else:
        logger.info("Request body: Empty")

    # Create a new 'receive' awaitable that will replay the consumed body.
    # This allows the downstream application (FastMCP) to read the body
    # as if it hadn't been touched by the middleware.
    async def new_receive():
        return {"type": "http.request", "body": req_body_bytes, "more_body": False}

    # Create a new Request object using the original scope, the new 'receive' channel,
    # and preserving the original 'send' channel to maintain headers.
    new_request = Request(scope=request.scope, receive=new_receive, send=request._send)

    response = await call_next(new_request)  # Pass the new_request to the next handler
    logger.info(f"Outgoing response: {response.status_code}")
    return response


# Initialize the LLM client (can be a singleton or passed via dependency injection)
# For simplicity, tools might access this global instance or have it passed during registration.
llm_agnostic_client_instance = LLMAgnosticClient()


def setup_mcp_server(mcp_instance: mcp = mcp) -> FastAPI:
    """Sets up the MCP server instance by registering tools."""
    logger.info("Setting up MCP server and registering tools...")
    general_tools.register_tools(mcp)  # Pass mcp instance
    csv_rag_tool.register_tools(
        mcp, llm_agnostic_client_instance
    )  # Pass mcp and llm client
    uniprot_tool.register_tools(mcp)  # Register UniProt tool
    websearch_tool.register_tools(mcp)  # Register WebSearch tool
    blastq_tool.register_tools(mcp)  # Register the Biopython-based BLAST tool
    pubchem_tool.register_tools(mcp)  # Register PubChem tool
    alphafold_tool.register_tools(
        mcp, llm_agnostic_client_instance
    )  # Register AlphaFold tool
    # Register other tool modules here as they are created
    logger.info("MCP tools registered.")

    # Get the FastAPI app from FastMCP
    actual_fastapi_app = mcp_instance.http_app()

    # Add the middleware to this app instance
    actual_fastapi_app.middleware("http")(log_request_middleware)
    logger.info("Request logging middleware added.")
    return actual_fastapi_app


async def main_async():
    """Asynchronous main function to initialize DB and start server."""
    # # Ensure data directory exists (especially for local non-Docker runs)
    # # Dockerfile handles this for containerized runs.
    # data_dir = "/app/data" # Path inside container
    # if not os.path.exists(data_dir) and "PYTEST_CURRENT_TEST" not in os.environ:
    #     try:
    #         os.makedirs(data_dir, exist_ok=True)
    #         logger.info(f"Created data directory: {data_dir}")
    #     except OSError as e:
    #         logger.error(f"Could not create data directory {data_dir}: {e}")
    #         # Decide if this is a fatal error

    # Database directory creation is now handled within state_manager.initialize_db()
    # based on the configured DATABASE_URL or the default relative path.
    logger.info("Initializing database...")
    await initialize_db()

    app = setup_mcp_server()

    server_host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    server_port = int(os.getenv("MCP_SERVER_PORT", "8080"))
    num_workers = int(os.getenv("UVICORN_WORKERS", "1"))

    config = uvicorn.Config(
        app,
        host=server_host,
        port=server_port,
        log_level=os.getenv(
            "LOG_LEVEL", "INFO"
        ).lower(),  # Uvicorn expects lowercase log level
        workers=num_workers,
    )
    server = uvicorn.Server(config)
    logger.info(
        f"Starting MCP Server on {server_host}:{server_port} with {num_workers} worker(s)..."
    )
    await server.serve()


def start_server_cli():
    """CLI entry point to start the server."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("MCP Server shutting down...")
    except Exception as e:
        logger.critical(f"MCP Server failed to start or crashed: {e}", exc_info=True)


if __name__ == "__main__":
    # This allows running the server directly using `python -m agentic_framework_pkg.mcp_server.main`
    start_server_cli()
