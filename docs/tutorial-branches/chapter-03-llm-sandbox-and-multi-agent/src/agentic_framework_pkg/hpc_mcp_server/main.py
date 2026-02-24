import uvicorn
import asyncio
import os
from dotenv import load_dotenv
from fastapi import Request, FastAPI  # For middleware, if needed
import json

# Load environment variables from .env file for local development
if os.path.exists(".env"):  # Check relative to this file
    load_dotenv()
elif os.path.exists("../../.env"):  # Check from root if running as module
    load_dotenv(dotenv_path=os.path.join(os.getcwd(), "../../.env"))


from .server import hpc_mcp  # Import the HPC MCP instance
from .tools import (
    nextflow_blast_tool,
    video_processing_tool,
    gitxray_tool,
    hpc_ssh_tool,
)  # Import HPC tools

# from ..state_manager import initialize_db # If HPC server needs its own state
from ..core.llm_agnostic_layer import (
    LLMAgnosticClient,
)  # For passing to tools that need LLM
from ..logger_config import get_logger  # Assuming reuse of central logger

logger = get_logger(__name__)

# Initialize the LLM client for the HPC server
llm_agnostic_client_hpc_instance = LLMAgnosticClient()


# Middleware for logging (optional, can be adapted from the main MCP server)
async def hpc_log_request_middleware(request: Request, call_next):
    req_body_bytes = await request.body()
    # Basic logging, can be expanded
    logger.info(f"HPC Server Request: {request.method} {request.url}")
    if req_body_bytes:
        try:
            logger.info(
                f"HPC Request body (JSON): {json.loads(req_body_bytes.decode())}"
            )
        except:
            logger.info(
                f"HPC Request body (raw): {req_body_bytes[:200].decode(errors='ignore')}..."
            )

    async def new_receive():
        return {"type": "http.request", "body": req_body_bytes, "more_body": False}

    new_request = Request(request.scope, receive=new_receive)
    response = await call_next(new_request)
    logger.info(f"HPC Server Response: {response.status_code}")
    return response


def setup_hpc_mcp_server(mcp_instance=hpc_mcp) -> FastAPI:
    logger.info("Setting up HPC MCP server and registering tools...")

    # Register tools with the HPC MCP instance
    nextflow_blast_tool.register_tools(mcp_instance)
    video_processing_tool.register_tools(
        mcp_instance, llm_agnostic_client_hpc_instance
    )  # Pass LLM client
    gitxray_tool.register_tools(mcp_instance)
    hpc_ssh_tool.register_tools(mcp_instance)  # SSH-based Slurm job submission

    # Register other HPC tool modules here
    logger.info("HPC MCP tools registered.")

    actual_fastapi_app = mcp_instance.http_app()
    actual_fastapi_app.middleware("http")(
        hpc_log_request_middleware
    )  # Optional logging
    return actual_fastapi_app


async def hpc_main_async():
    # await initialize_db() # If HPC server has its own DB state
    app = setup_hpc_mcp_server()

    server_host = os.getenv("HPC_MCP_SERVER_HOST", "0.0.0.0")
    server_port = int(os.getenv("HPC_MCP_SERVER_PORT", "8081"))  # Different port
    num_workers = int(os.getenv("HPC_UVICORN_WORKERS", "2"))

    config = uvicorn.Config(
        app,
        host=server_host,
        port=server_port,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        workers=num_workers,
    )
    server = uvicorn.Server(config)
    logger.info(
        f"Starting HPC MCP Server on {server_host}:{server_port} with {num_workers} worker(s)..."
    )
    await server.serve()


def start_hpc_server_cli():
    try:
        asyncio.run(hpc_main_async())
    except KeyboardInterrupt:
        logger.info("HPC MCP Server shutting down...")
    except Exception as e:
        logger.critical(
            f"HPC MCP Server failed to start or crashed: {e}", exc_info=True
        )


if __name__ == "__main__":
    start_hpc_server_cli()
