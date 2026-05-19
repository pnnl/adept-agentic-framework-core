from fastmcp import FastMCP, Context
from ...logger_config import get_logger
import asyncio
from typing import Dict, Any, Optional
import base64
import os
import uuid
import shlex
import subprocess

# Setup logging
logger = get_logger(__name__)

# --- nsjail configuration ---
SANDBOX_BACKEND = os.getenv("SANDBOX_BACKEND", "docker").lower()
NSJAIL_BINARY = os.getenv("NSJAIL_BINARY_PATH", "/usr/local/bin/nsjail")
NSJAIL_AVAILABLE = os.path.isfile(NSJAIL_BINARY) and os.access(NSJAIL_BINARY, os.X_OK)

if NSJAIL_AVAILABLE:
    logger.info(
        f"nsjail binary found at {NSJAIL_BINARY}. Process-level isolation available."
    )
else:
    logger.info(
        f"nsjail binary not found at {NSJAIL_BINARY}. Will use Docker-only isolation."
    )

# Import the sandbox
_llm_sandbox_err = None
LLM_SANDBOX_AVAILABLE = False
try:
    from llm_sandbox import ArtifactSandboxSession
    from llm_sandbox.exceptions import SandboxTimeoutError
    from llm_sandbox.data import ExecutionResult

    LLM_SANDBOX_AVAILABLE = True
    logger.info(
        "The 'llm-sandbox' package is available. Code execution tool will be enabled."
    )
except ImportError as imp_err:
    _llm_sandbox_err = imp_err
    logger.error(
        f"The 'llm-sandbox' package is not installed. Code execution tool will be unavailable: {imp_err}"
    )
    LLM_SANDBOX_AVAILABLE = False
    ArtifactSandboxSession = None
    SandboxTimeoutError = None
    ExecutionResult = None


def _build_nsjail_command(interpreter: str, script_path: str) -> list[str]:
    """Build an nsjail command that wraps a script execution with process-level isolation."""
    return [
        NSJAIL_BINARY,
        "--mode",
        "once",
        "--chroot",
        "/",
        "--user",
        "65534",  # nobody
        "--group",
        "65534",
        "--rlimit_nofile",
        "64",
        "--rlimit_nproc",
        "64",
        "--rlimit_as",
        "512",  # 512 MB address space limit
        "--time_limit",
        "30",
        "--",  # network disabled by default (new net namespace)
        interpreter,
        script_path,
    ]


def _run_code_in_sandbox_sync(
    code: str,
    language: str,
    generate_plot: bool,
    sandbox_image: Optional[str] = None,
    exec_timeout: int = 30,
) -> Dict[str, Any]:
    """
    Synchronous wrapper to run code in a new, isolated sandbox session.
    This function creates a sandbox, executes the code, and cleans up resources.
    """
    if not LLM_SANDBOX_AVAILABLE:
        logger.error(
            "The 'llm-sandbox' package is not installed. This tool is unavailable."
        )
        raise RuntimeError(
            "The 'llm-sandbox' package is not installed. This tool is unavailable."
        )

    session_params = {
        "execution_timeout": exec_timeout,
        # Enable plotting only for python and only if requested
        "enable_plotting": generate_plot and language.lower() == "python",
    }
    if sandbox_image:
        session_params["image"] = sandbox_image  # 'image' is the correct parameter name
        logger.info(f"Creating sandbox session using custom image: {sandbox_image}")
    else:
        session_params["lang"] = language.lower()
        logger.info(f"Creating sandbox session for language: {language}")

    try:
        use_nsjail = (
            SANDBOX_BACKEND == "nsjail"
            and NSJAIL_AVAILABLE
            and not (generate_plot and language.lower() == "python")
        )

        # Use ArtifactSandboxSession to capture plots
        with ArtifactSandboxSession(**session_params) as session:
            if use_nsjail:
                # nsjail path: write code to temp file, execute via nsjail inside container
                logger.info(
                    f"Executing {language} code via nsjail in sandbox:\n--- CODE ---\n{code}\n------------"
                )
                interpreters = {
                    "python": "/usr/local/bin/python3",
                    "javascript": "/usr/bin/node",
                    "shell": "/bin/sh",
                }
                interp = interpreters.get(language.lower(), "/usr/local/bin/python3")
                nsjail_cmd = _build_nsjail_command(interp, "/tmp/sandbox_exec.py")
                write_cmd = f"cat > /tmp/sandbox_exec.py << 'NSJAIL_CODE_EOF'\n{code}\nNSJAIL_CODE_EOF"
                full_cmd = (
                    f"{write_cmd} && {' '.join(shlex.quote(c) for c in nsjail_cmd)}"
                )
                result = session.execute_command(full_cmd)
                logger.info(f"nsjail execution finished. Exit code: {result.exit_code}")
                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.exit_code,
                    "plots": [],
                }
            else:
                # Docker-only path (plot capture or nsjail unavailable)
                logger.info(
                    f"Executing {language} code in sandbox (Docker path):\n--- CODE ---\n{code}\n------------"
                )
                result: ExecutionResult = session.run(code)
                logger.info(
                    f"Sandbox execution finished. Exit code: {result.exit_code}"
                )

                plots_data = []
                if result.plots:
                    logger.info(
                        f"Captured {len(result.plots)} plots from sandbox execution."
                    )
                    # Directory to save plots, served by the static endpoint
                    plots_dir = "/app/public/plots"
                    os.makedirs(plots_dir, exist_ok=True)

                    # Base URL for accessing the plots.
                    # The public URL of the sandbox server should be provided via this env var
                    # for plot URLs to be correctly resolved by the client (e.g., Streamlit app, browser).
                    base_url_from_env = os.getenv("SANDBOX_MCP_SERVER_PUBLIC_URL")
                    if base_url_from_env:
                        base_plot_url = f"{base_url_from_env.rstrip('/')}/static/plots"
                        logger.info(
                            f"Using configured SANDBOX_MCP_SERVER_PUBLIC_URL for plot URLs: {base_plot_url}"
                        )
                    else:
                        # Fallback to a less reliable method with a warning.
                        # This might work in some local setups but will fail in others.
                        host = os.getenv("HOSTNAME", "localhost")
                        port = os.getenv("PORT", "8082")
                        base_plot_url = f"http://{host}:{port}/static/plots"
                        logger.warning(
                            f"SANDBOX_MCP_SERVER_PUBLIC_URL is not set. Falling back to constructing plot URL from HOSTNAME and PORT: {base_plot_url}. This may not be accessible by clients. Please set SANDBOX_MCP_SERVER_PUBLIC_URL (e.g., http://localhost:8082) in your environment for reliable plot rendering."
                        )

                    for plot in result.plots:
                        file_extension = plot.format.value
                        plot_filename = f"{uuid.uuid4().hex}.{file_extension}"
                        plot_filepath = os.path.join(plots_dir, plot_filename)

                        # Decode base64 and save the plot
                        plot_bytes = base64.b64decode(plot.content_base64)
                        with open(plot_filepath, "wb") as f:
                            f.write(plot_bytes)

                        plot_url = f"{base_plot_url}/{plot_filename}"
                        logger.info(
                            f"Saved plot to {plot_filepath} and made available at {plot_url}"
                        )

                        # Append a dictionary containing both the raw data and the URL
                        plots_data.append(
                            {
                                "content_base64": plot.content_base64,
                                "format": file_extension,
                                "plot_url": plot_url,
                            }
                        )

                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.exit_code,
                    "plots": plots_data,
                }
    except SandboxTimeoutError as e:
        logger.error(
            f"Sandbox execution timed out for language {language}: {e}", exc_info=True
        )
        raise TimeoutError(
            f"Code execution timed out after {exec_timeout} seconds."
        ) from e
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during sandbox session for language {language}: {e}",
            exc_info=True,
        )
        raise RuntimeError(f"An unexpected error occurred in the sandbox: {e}") from e


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def execute_code(
        ctx: Context,
        code: str,
        language: str = "python",
        generate_plot: bool = False,
        sandbox_image: Optional[str] = None,
        mcp_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes a given snippet of code in a secure, isolated sandbox environment for a specified language.
        Supported languages are 'python', 'javascript', and 'shell'. For Python, it can capture and return plots
        generated by libraries like matplotlib or seaborn if 'generate_plot' is set to True.
        The sandbox enforces process-level isolation via nsjail with network access disabled,
        strict resource limits (memory, CPU, file descriptors), and a limited execution time.
        Plot-capturing executions use the Docker backend directly where container-level isolation applies.
        For Python and JavaScript, the final line of the code should be an expression that yields the result.
        Standard output will also be captured.

        Args:
            ctx: FastMCP Context.
            code: A string containing the code to execute.
            language: The programming language of the code. Defaults to 'python'.
            generate_plot: If True and language is Python, enables plot capturing. Defaults to False.
            sandbox_image: Optional. The full URI of a custom Docker image to use for the sandbox. Overrides 'language'.
            mcp_session_id: Optional session ID for logging/context.

        Returns:
            A dictionary containing the execution result, stdout, stderr, and status.
        """
        await ctx.info(
            f"Received request to execute {language} code. Session: {mcp_session_id}"
        )

        if not LLM_SANDBOX_AVAILABLE:
            err_msg = f"Code execution tool is not available because 'llm-sandbox' is not installed on the server: {_llm_sandbox_err}"
            logger.error(err_msg)
            await ctx.error(err_msg)
            return {"status": "error", "message": err_msg}

        try:
            execution_result = await asyncio.to_thread(
                _run_code_in_sandbox_sync, code, language, generate_plot, sandbox_image
            )

            if execution_result.get("exit_code") == 0:
                await ctx.info(
                    f"{language.capitalize()} code executed successfully in sandbox."
                )
                return {
                    "status": "success",
                    "stdout": execution_result.get("stdout"),
                    "stderr": execution_result.get("stderr"),
                    "plots": execution_result.get("plots", []),
                }
            else:
                await ctx.error(
                    f"Code execution in sandbox failed with exit code {execution_result.get('exit_code')}."
                )
                return {
                    "status": "error",
                    "message": "Code execution failed.",
                    "exit_code": execution_result.get("exit_code"),
                    "stdout": execution_result.get("stdout"),
                    "stderr": execution_result.get("stderr"),
                    "plots": execution_result.get("plots", []),
                }
        except Exception as e:
            error_message = f"An error occurred while executing the {language} code in the sandbox: {e}"
            logger.error(error_message, exc_info=True)
            await ctx.error(f"Sandbox execution failed: {e}")
            return {
                "status": "error",
                "message": f"Failed to execute {language} code in sandbox.",
                "details": str(e),
            }

    logger.info("Sandbox Code Execution MCP tool registered.")
