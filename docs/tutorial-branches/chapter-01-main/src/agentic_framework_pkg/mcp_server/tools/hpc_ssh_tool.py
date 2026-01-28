"""
HPC SSH Tool - Remote cluster job submission via SSH

This module provides MCP tools for connecting to remote HPC clusters,
submitting Slurm batch jobs, and monitoring job status.

Features:
- SSH connection testing with encrypted PEM key support
- Slurm job submission (sbatch)
- Job status monitoring (squeue)
- Secure credential handling via environment variables

Security:
- Supports both unencrypted and passphrase-protected PEM keys
- Fabric automatically handles encrypted keys via ssh-agent or passphrase prompt
- No credentials hardcoded in source
"""

from fastmcp import FastMCP, Context
from fabric import Connection
from typing import Dict, Any, Optional
import os
import re
import asyncio
from functools import wraps
from ...logger_config import get_logger

logger = get_logger(__name__)


def async_fabric(func):
    """Decorator to run Fabric (sync) operations in async context."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    return wrapper


def _validate_path_safe(path: str) -> str:
    """
    Validate that a file path is safe and doesn't contain shell injection attempts.

    Prevents command injection by blocking dangerous shell characters.

    Args:
        path: File path to validate

    Returns:
        Validated path (same as input if safe)

    Raises:
        ValueError: If path contains suspicious characters or patterns
    """
    # Check for dangerous characters
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"]
    for char in dangerous_chars:
        if char in path:
            raise ValueError(
                f"Path contains dangerous character '{char}' - potential injection attempt"
            )

    # Check for command substitution patterns
    if "$(" in path or "${" in path:
        raise ValueError(
            "Path contains command substitution pattern - potential injection attempt"
        )

    return path


def _validate_job_name_safe(job_name: Optional[str]) -> Optional[str]:
    """
    Validate that a job name is safe and doesn't contain shell injection attempts.

    Args:
        job_name: Job name to validate (can be None)

    Returns:
        Validated job name or None

    Raises:
        ValueError: If job name contains suspicious characters
    """
    if job_name is None:
        return None

    # Only allow alphanumeric, dash, underscore, dot
    if not re.match(r"^[a-zA-Z0-9_.-]+$", job_name):
        raise ValueError(
            f"Job name '{job_name}' contains invalid characters. "
            "Only alphanumeric, dash, underscore, and dot allowed."
        )

    # Reasonable length limit
    if len(job_name) > 64:
        raise ValueError(f"Job name too long (max 64 characters): {job_name}")

    return job_name


def _validate_job_id_safe(job_id: str) -> str:
    """
    Validate that a job ID is numeric and safe.

    Args:
        job_id: Job ID to validate

    Returns:
        Validated job ID

    Raises:
        ValueError: If job ID is not numeric
    """
    if not re.match(r"^\d+$", job_id):
        raise ValueError(f"Job ID must be numeric: {job_id}")

    return job_id


def _validate_path_safe(path: str) -> str:
    """
    Validate that a file path is safe and doesn't contain shell injection attempts.

    Args:
        path: File path to validate

    Returns:
        Validated path (same as input if safe)

    Raises:
        ValueError: If path contains suspicious characters or patterns
    """
    # Check for dangerous characters
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"]
    for char in dangerous_chars:
        if char in path:
            raise ValueError(f"Path contains dangerous character: {char}")

    # Check for command substitution patterns
    if "$(" in path or "${" in path:
        raise ValueError("Path contains command substitution pattern")

    # Must be absolute path or relative to home
    if not (path.startswith("/") or path.startswith("~") or path.startswith(".")):
        # Allow simple relative paths
        pass

    return path


def _validate_job_name_safe(job_name: Optional[str]) -> Optional[str]:
    """
    Validate that a job name is safe and doesn't contain shell injection attempts.

    Args:
        job_name: Job name to validate (can be None)

    Returns:
        Validated job name (same as input if safe, or None)

    Raises:
        ValueError: If job name contains suspicious characters
    """
    if job_name is None:
        return None

    # Only allow alphanumeric, dash, underscore, dot
    if not re.match(r"^[a-zA-Z0-9_.-]+$", job_name):
        raise ValueError(
            f"Job name contains invalid characters. Only alphanumeric, dash, underscore, and dot allowed: {job_name}"
        )

    # Reasonable length limit
    if len(job_name) > 64:
        raise ValueError(f"Job name too long (max 64 characters): {job_name}")

    return job_name


def _validate_job_id_safe(job_id: str) -> str:
    """
    Validate that a job ID is numeric and safe.

    Args:
        job_id: Job ID to validate

    Returns:
        Validated job ID

    Raises:
        ValueError: If job ID is not numeric
    """
    if not re.match(r"^\d+$", job_id):
        raise ValueError(f"Job ID must be numeric: {job_id}")

    return job_id


def _get_hpc_connection(
    hpc_host: Optional[str] = None, hpc_user: Optional[str] = None, timeout: int = 30
) -> Connection:
    """
    Create Fabric SSH connection to HPC cluster.

    Supports both unencrypted and passphrase-protected PEM keys.
    Fabric automatically handles encrypted keys by:
    1. Using ssh-agent if key is loaded
    2. Prompting for passphrase if key is encrypted and not in agent

    Args:
        hpc_host: HPC hostname (defaults to HPC_HOST env var)
        hpc_user: SSH username (defaults to HPC_USER env var)
        timeout: Connection timeout in seconds

    Returns:
        Connection: Fabric connection object

    Raises:
        ValueError: If required env vars not set
    """
    host = hpc_host or os.getenv("HPC_HOST")
    user = hpc_user or os.getenv("HPC_USER")

    if not host:
        raise ValueError("HPC_HOST must be set in environment or passed as parameter")
    if not user:
        raise ValueError("HPC_USER must be set in environment or passed as parameter")

    # Build connection kwargs
    connect_kwargs = {}

    # Try SSH key first (supports both encrypted and unencrypted PEM)
    key_path = os.getenv("HPC_SSH_KEY_PATH")
    if key_path:
        if not os.path.exists(key_path):
            raise ValueError(f"SSH key not found: {key_path}")

        connect_kwargs["key_filename"] = key_path

        # Optional: Passphrase for encrypted keys
        # If not provided, Fabric will prompt or use ssh-agent
        passphrase = os.getenv("HPC_SSH_KEY_PASSPHRASE")
        if passphrase:
            connect_kwargs["passphrase"] = passphrase
            logger.info(f"Using SSH key with passphrase: {key_path}")
        else:
            logger.info(f"Using SSH key (will prompt if encrypted): {key_path}")

    # Fallback to password (not recommended)
    elif os.getenv("HPC_SSH_PASSWORD"):
        connect_kwargs["password"] = os.getenv("HPC_SSH_PASSWORD")
        logger.warning("Using password auth - SSH keys strongly recommended!")

    else:
        raise ValueError(
            "No authentication method configured. Set HPC_SSH_KEY_PATH or HPC_SSH_PASSWORD"
        )

    port = int(os.getenv("HPC_SSH_PORT", "22"))

    logger.info(f"Connecting to {user}@{host}:{port}")

    return Connection(
        host=host,
        user=user,
        port=port,
        connect_timeout=timeout,
        connect_kwargs=connect_kwargs,
    )


def _parse_sbatch_output(output: str) -> str:
    """
    Extract job ID from sbatch output.

    Expected format: "Submitted batch job 123456"

    Args:
        output: sbatch command stdout

    Returns:
        str: Job ID

    Raises:
        ValueError: If job ID cannot be parsed
    """
    match = re.search(r"Submitted batch job (\d+)", output)
    if match:
        return match.group(1)

    # Handle alternative formats
    match = re.search(r"job (\d+)", output, re.IGNORECASE)
    if match:
        return match.group(1)

    raise ValueError(f"Could not parse job ID from sbatch output: {output}")


def _parse_squeue_output(output: str) -> Dict[str, Any]:
    """
    Parse squeue output into structured data.

    Expected format (header + data):
    JOBID PARTITION NAME USER ST TIME
    123456 compute myjob username R 0:05:30

    State codes:
    PD = PENDING, R = RUNNING, CG = COMPLETING,
    CD = COMPLETED, F = FAILED, CA = CANCELLED

    Args:
        output: squeue command stdout

    Returns:
        Dict with job_id, job_state, partition, job_name, user, runtime
    """
    output = output.strip()

    if not output:
        return {
            "job_state": "NOT_FOUND",
            "message": "Job not in queue (may have completed or been removed)",
        }

    lines = output.split("\n")

    # Need at least header + 1 data line
    if len(lines) < 2:
        # Single line might be error message
        if "Invalid" in output or "error" in output.lower():
            return {"job_state": "ERROR", "message": output}
        return {"job_state": "COMPLETED_OR_REMOVED", "message": output}

    # Parse data line (skip header)
    parts = lines[1].split()
    if len(parts) < 6:
        return {
            "job_state": "PARSE_ERROR",
            "raw": output,
            "message": "Unexpected squeue format",
        }

    # Map Slurm state codes to readable states
    state_map = {
        "PD": "PENDING",
        "R": "RUNNING",
        "CG": "COMPLETING",
        "CD": "COMPLETED",
        "F": "FAILED",
        "CA": "CANCELLED",
        "TO": "TIMEOUT",
        "S": "SUSPENDED",
    }

    state_code = parts[4]
    job_state = state_map.get(state_code, state_code)

    return {
        "job_id": parts[0],
        "partition": parts[1],
        "job_name": parts[2],
        "user": parts[3],
        "job_state": job_state,
        "runtime": parts[5] if len(parts) > 5 else "unknown",
        "raw_output": output,
    }


def register_tools(mcp: FastMCP):
    """Register HPC SSH tools with FastMCP server."""

    @mcp.tool()
    async def test_hpc_connection(
        ctx: Context,
        hpc_host: Optional[str] = None,
        hpc_user: Optional[str] = None,
        mcp_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Test SSH connection to remote HPC cluster.

        Verifies that SSH authentication works and the cluster is reachable.
        Supports both unencrypted PEM keys and passphrase-protected keys.

        Args:
            ctx: FastMCP context
            hpc_host: HPC hostname (defaults to HPC_HOST env var)
            hpc_user: SSH username (defaults to HPC_USER env var)
            mcp_session_id: MCP session ID for tracking

        Returns:
            {
                "status": "success" | "error",
                "message": str,
                "hostname": str,
                "kernel": str,
                "uptime": str
            }

        Example:
            >>> await test_hpc_connection(ctx)
            {
                "status": "success",
                "hostname": "hpc-login01.institution.edu",
                "kernel": "Linux",
                "uptime": "up 45 days"
            }
        """
        await ctx.info("Testing HPC cluster SSH connection...")

        try:
            # Create connection
            conn = _get_hpc_connection(hpc_host, hpc_user)

            # Test connection with simple commands
            @async_fabric
            def test_connection():
                # Get kernel info
                kernel_result = conn.run("uname -s", hide=True)
                hostname_result = conn.run("hostname", hide=True)
                uptime_result = conn.run("uptime -p 2>/dev/null || uptime", hide=True)

                return {
                    "kernel": kernel_result.stdout.strip(),
                    "hostname": hostname_result.stdout.strip(),
                    "uptime": uptime_result.stdout.strip(),
                }

            info = await test_connection()

            await ctx.info(f"✓ Connected to {info['hostname']}")

            return {
                "status": "success",
                "message": f"Successfully connected to HPC cluster",
                **info,
            }

        except ValueError as e:
            # Configuration error
            error_msg = f"Configuration error: {str(e)}"
            logger.error(error_msg)
            await ctx.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "error_type": "configuration",
            }

        except Exception as e:
            # Connection or authentication error
            error_msg = f"Connection failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await ctx.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "error_type": "connection",
                "hint": "Check HPC_HOST, HPC_USER, and SSH key configuration",
            }

    @mcp.tool()
    async def submit_slurm_job(
        ctx: Context,
        script_path: str,
        job_name: Optional[str] = None,
        hpc_host: Optional[str] = None,
        hpc_user: Optional[str] = None,
        mcp_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submit a Slurm batch job to remote HPC cluster.

        The script must already exist on the remote HPC filesystem.
        Use absolute paths or paths relative to the remote user's home directory.

        Args:
            ctx: FastMCP context
            script_path: Path to batch script on REMOTE HPC (e.g., /home/user/jobs/hello.sh)
            job_name: Optional job name (overrides script's #SBATCH --job-name)
            hpc_host: HPC hostname (defaults to HPC_HOST env var)
            hpc_user: SSH username (defaults to HPC_USER env var)
            mcp_session_id: MCP session ID for tracking

        Returns:
            {
                "status": "success" | "error",
                "job_id": str,
                "message": str,
                "script_path": str,
                "submission_output": str
            }

        Example:
            >>> await submit_slurm_job(ctx, "/home/user/jobs/hello.sh", job_name="test_job")
            {
                "status": "success",
                "job_id": "123456",
                "message": "Job submitted successfully"
            }
        """
        await ctx.info(f"Submitting Slurm job: {script_path}")

        try:
            # Validate inputs for security
            script_path = _validate_path_safe(script_path)
            job_name = _validate_job_name_safe(job_name)

            conn = _get_hpc_connection(hpc_host, hpc_user)

            @async_fabric
            def submit_job():
                # Verify script exists on remote (using safe path)
                check_result = conn.run(
                    f"test -f {script_path} && echo 'exists' || echo 'missing'",
                    hide=True,
                )

                if "missing" in check_result.stdout:
                    raise FileNotFoundError(f"Script not found on HPC: {script_path}")

                # Build sbatch command with validated inputs
                submit_cmd = f"sbatch"
                if job_name:
                    submit_cmd += f" --job-name={job_name}"
                submit_cmd += f" {script_path}"

                # Submit job
                result = conn.run(submit_cmd, hide=True)

                return {
                    "output": result.stdout.strip(),
                    "stderr": result.stderr.strip() if result.stderr else "",
                }

            result = await submit_job()

            # Parse job ID from output
            job_id = _parse_sbatch_output(result["output"])

            await ctx.info(f"✓ Job {job_id} submitted successfully")

            return {
                "status": "success",
                "job_id": job_id,
                "message": f"Job {job_id} submitted successfully",
                "script_path": script_path,
                "submission_output": result["output"],
            }

        except FileNotFoundError as e:
            error_msg = str(e)
            logger.error(error_msg)
            await ctx.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "script_path": script_path,
                "error_type": "file_not_found",
            }

        except ValueError as e:
            # Configuration or parsing error
            error_msg = f"Configuration error: {str(e)}"
            logger.error(error_msg)
            await ctx.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "script_path": script_path,
                "error_type": "configuration",
            }

        except Exception as e:
            error_msg = f"Job submission failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await ctx.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "script_path": script_path,
                "error_type": "submission",
            }

    @mcp.tool()
    async def check_slurm_job_status(
        ctx: Context,
        job_id: str,
        hpc_host: Optional[str] = None,
        hpc_user: Optional[str] = None,
        mcp_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check status of a Slurm job on remote HPC cluster.

        Queries the Slurm scheduler for current job state.

        Args:
            ctx: FastMCP context
            job_id: Slurm job ID (returned by submit_slurm_job)
            hpc_host: HPC hostname (defaults to HPC_HOST env var)
            hpc_user: SSH username (defaults to HPC_USER env var)
            mcp_session_id: MCP session ID for tracking

        Returns:
            {
                "status": "success" | "error",
                "job_id": str,
                "job_state": "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | ...,
                "job_name": str,
                "partition": str,
                "user": str,
                "runtime": str,
                "message": str
            }

        Job States:
            - PENDING: Job is waiting in queue
            - RUNNING: Job is executing
            - COMPLETING: Job is finishing
            - COMPLETED: Job finished successfully
            - FAILED: Job failed
            - CANCELLED: Job was cancelled
            - NOT_FOUND: Job not in queue (completed or removed)

        Example:
            >>> await check_slurm_job_status(ctx, "123456")
            {
                "status": "success",
                "job_id": "123456",
                "job_state": "RUNNING",
                "runtime": "0:05:30"
            }
        """
        await ctx.info(f"Checking status of Slurm job {job_id}")

        try:
            # Validate job ID to prevent command injection
            job_id = _validate_job_id_safe(job_id)

            conn = _get_hpc_connection(hpc_host, hpc_user)

            @async_fabric
            def check_status():
                # Query job status
                result = conn.run(
                    f"squeue -j {job_id} --format='%.18i %.9P %.30j %.8u %.2t %.10M'",
                    hide=True,
                    warn=True,  # Don't raise exception if job not found
                )

                return {
                    "output": result.stdout.strip(),
                    "stderr": result.stderr.strip() if result.stderr else "",
                    "exit_code": result.exited,
                }

            result = await check_status()

            # Parse status output
            job_info = _parse_squeue_output(result["output"])

            # Log appropriately based on state
            state = job_info.get("job_state", "UNKNOWN")
            if state in ["RUNNING", "PENDING"]:
                await ctx.info(f"✓ Job {job_id} is {state}")
            elif state == "COMPLETED":
                await ctx.info(f"✓ Job {job_id} completed")
            elif state in ["FAILED", "CANCELLED"]:
                await ctx.warning(f"Job {job_id} {state}")
            else:
                await ctx.info(f"Job {job_id} status: {state}")

            return {"status": "success", "job_id": job_id, **job_info}

        except ValueError as e:
            error_msg = f"Configuration error: {str(e)}"
            logger.error(error_msg)
            await ctx.error(error_msg)
            return {
                "status": "error",
                "job_id": job_id,
                "message": error_msg,
                "error_type": "configuration",
            }

        except Exception as e:
            error_msg = f"Status check failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await ctx.error(error_msg)
            return {
                "status": "error",
                "job_id": job_id,
                "message": error_msg,
                "error_type": "query",
            }

    logger.info("HPC SSH MCP tools registered.")
