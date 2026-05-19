import aiohttp
import json
from typing import Dict, List, Any, Type, Optional
from langchain.tools import Tool
from pydantic import BaseModel, create_model
import os
import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError
import httpx
from ..logger_config import get_logger
from .stdio_tool_wrapper import create_stdio_tool

logger = get_logger(__name__)


def _create_args_schema(schema_definition: Dict[str, Any]) -> Type[BaseModel]:
    """Dynamically creates a Pydantic model from a JSON schema definition."""
    field_definitions = {}
    if schema_definition:
        for prop_name, prop_details in schema_definition.items():
            field_type = str
            if prop_details.get("type") == "integer":
                field_type = int
            elif prop_details.get("type") == "number":
                field_type = float
            elif prop_details.get("type") == "boolean":
                field_type = bool

            field_definitions[prop_name] = (field_type, ...)

    return create_model("DynamicToolArgs", **field_definitions)


def _create_http_tool(config: Dict[str, Any]) -> Tool:
    """Factory for creating a tool that communicates over HTTP."""
    connection_info = config["invocation"]["connection"]
    url = connection_info["url"]
    method = connection_info.get("method", "POST")
    headers = connection_info.get("headers", {})

    async def _http_tool_func(**kwargs) -> str:
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.request(method, url, json=kwargs) as response:
                    response.raise_for_status()
                    if "application/json" in response.content_type:
                        return json.dumps(await response.json())
                    else:
                        return await response.text()
        except aiohttp.ClientError as e:
            logger.error(f"HTTP tool '{config['name']}' failed: {e}")
            return f"Error: Could not connect to the tool service at {url}. {e}"
        except Exception as e:
            logger.error(
                f"An unexpected error occurred in HTTP tool '{config['name']}': {e}"
            )
            return f"An unexpected error occurred: {e}"

    return Tool(
        name=config["name"],
        description=config["description"],
        func=None,
        coroutine=_http_tool_func,
        args_schema=_create_args_schema(config.get("args_schema", {})),
    )


def _create_stdio_tool_from_config(config: Dict[str, Any]) -> Tool:
    """Factory for creating a tool that communicates over stdio."""
    connection_info = config["invocation"]["connection"]
    command = connection_info.get("command")
    if not command or not isinstance(command, list):
        raise ValueError("Stdio tool configuration must include a 'command' list.")

    working_directory = connection_info.get("working_directory")

    return create_stdio_tool(
        name=config["name"],
        description=config["description"],
        command=command,
        args_schema=_create_args_schema(config.get("args_schema", {})),
        working_directory=working_directory,
    )


class ExternalToolManager:
    """
    Manages the registration and creation of tools from external sources.

    This class acts as the central registry and factory for all dynamically registered
    tools within the Agent Gateway. It abstracts away the complexities of tool
    invocation, allowing the agent to interact with any tool through a unified,
    LangChain-compatible interface.

    ### Key Responsibilities:

    1.  **Persistence (Redis):**
        - Tool configurations, including their invocation details (URL, command, etc.)
          and Access Control Lists (ACLs), are persisted in Redis using `redis.asyncio`.
        - This ensures that registered tools are not lost when the gateway restarts.

    2.  **Protocol-Agnostic Factory:**
        - The manager uses a dictionary of factory functions (`protocol_factories`)
          to create `langchain.tools.Tool` objects from their stored configurations.
        - It supports multiple communication protocols (e.g., `http`, `stdio`). When a
          tool is to be created, the manager looks at the `protocol` specified in its
          configuration and calls the corresponding factory function (e.g.,
          `_create_http_tool`, `_create_stdio_tool_from_config`).
        - This design is highly extensible; adding support for a new protocol simply
          requires adding a new factory function to the dictionary.

    3.  **Dynamic Tool Loading and Caching:**
        - On startup, the manager loads all tool configurations from Redis and the
          `mcp_servers.json` file, and creates the corresponding `Tool` objects,
          caching them in memory in the `self.registered_tools` dictionary for fast access.
        - When a new tool is registered via the `/v1/tools/register` endpoint, it is
          added to both Redis and the in-memory cache.

    4.  **Authorization and Access Control:**
        - The `get_authorized_tools` method is the critical link between the tool
          registry and the agent. It takes a user's ID and group memberships (from
          their JWT) and filters the master list of cached tools.
        - It returns only the `Tool` objects that the user is permitted to use, based
          on the `acl` metadata stored with each tool's configuration.
        - This ensures that when the `ScientificWorkflowAgent` is instantiated, it is
          only provisioned with the tools it is authorized to access.

    5.  **Tool Introspection:**
        - For HTTP tools, the manager attempts to fetch the OpenAPI schema to gather
          more detailed information about the tool's capabilities.
    """

    def __init__(self):
        self.redis_client = None
        self.registered_tools: Dict[str, Tool] = {}
        self.protocol_factories = {
            "http": _create_http_tool,
            "stdio": _create_stdio_tool_from_config,
        }
        self._load_tools_from_file()

    async def connect_redis(self):
        """Connect to Redis and load persisted tools. Safe to call even if Redis is unavailable."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = aioredis.from_url(redis_url)
        logger.info(f"ExternalToolManager connecting to Redis at {redis_url}")
        await self._load_tools_from_redis()

    @classmethod
    async def create(cls) -> "ExternalToolManager":
        """Async factory that connects to Redis and loads persisted tools."""
        instance = cls()
        await instance.connect_redis()
        return instance

    def _load_tools_from_file(self):
        """Loads tool configurations from the mcp_servers.json file."""
        config_path = os.getenv(
            "MCP_SERVERS_CONFIG_PATH",
            os.path.join(os.path.dirname(__file__), "config", "mcp_servers.json"),
        )
        try:
            with open(config_path) as f:
                config_data = json.load(f)
                mcp_servers = config_data.get("mcpServers", {})
                for tool_name, server_config in mcp_servers.items():
                    server_config["name"] = tool_name  # Add the name to the config dict
                    try:
                        self._register_tool_from_config(server_config)
                    except ValueError as e:
                        logger.error(
                            f"Failed to load tool '{tool_name}' from file: {e}"
                        )
        except FileNotFoundError:
            logger.warning(
                f"{config_path} not found, skipping file-based tool loading."
            )
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding {config_path}: {e}")

    async def _load_tools_from_redis(self):
        """Asynchronously loads all tool configurations from Redis and registers them."""
        try:
            async for key in self.redis_client.scan_iter("external_tool:*"):
                config_json = await self.redis_client.get(key)
                if config_json:
                    config = json.loads(config_json)
                    try:
                        self._register_tool_from_config(config)
                    except ValueError as e:
                        logger.error(
                            f"Failed to load tool '{config.get('name')}' from Redis: {e}"
                        )
        except Exception as e:
            logger.error(f"Error loading tools from Redis: {e}", exc_info=True)

    def _register_tool_from_config(self, config: Dict[str, Any]):
        """Registers a single tool from its configuration dictionary."""
        tool_name = config.get("name")
        if not tool_name:
            raise ValueError("Tool configuration must include a 'name'.")

        invocation = config.get("invocation")
        if not invocation or "protocol" not in invocation:
            raise ValueError(
                "Tool configuration must include an 'invocation' block with a 'protocol'."
            )

        protocol = invocation["protocol"]
        if protocol not in self.protocol_factories:
            raise ValueError(
                f"Unsupported tool protocol: '{protocol}'. Supported protocols are: {list(self.protocol_factories.keys())}"
            )

        if tool_name in self.registered_tools:
            logger.warning(f"Tool '{tool_name}' is already registered. Overwriting.")

        # Create the tool using the appropriate factory
        factory = self.protocol_factories[protocol]
        tool = factory(config)

        self.registered_tools[tool_name] = tool
        logger.info(f"Successfully registered '{protocol}' tool: '{tool_name}'")

    def get_all_tools(self) -> List[Tool]:
        return list(self.registered_tools.values())

    async def _introspect_http_tool(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Attempts to introspect an HTTP tool to get more details (e.g., OpenAPI schema)."""
        url = config["invocation"]["connection"]["url"]
        try:
            # Assuming a common pattern for OpenAPI/Swagger docs
            openapi_url = f"{url.rstrip('/')}/openapi.json"
            async with httpx.AsyncClient() as client:
                response = await client.get(openapi_url, timeout=5)
                response.raise_for_status()
                openapi_spec = response.json()
                logger.info(
                    f"Successfully introspected OpenAPI spec for {config['name']}"
                )
                # You might want to extract specific paths/methods/schemas here
                # For now, we'll just store the whole spec or relevant parts
                config["introspected_metadata"] = {"openapi_spec": openapi_spec}
        except httpx.RequestError as e:
            logger.warning(
                f"Could not fetch OpenAPI spec for {config['name']} at {openapi_url}: {e}"
            )
            config["introspected_metadata"] = {
                "error": f"Could not fetch OpenAPI spec: {e}"
            }
        except json.JSONDecodeError:
            logger.warning(
                f"Could not decode OpenAPI spec for {config['name']} at {openapi_url}: Invalid JSON response."
            )
            config["introspected_metadata"] = {
                "error": "Invalid JSON response for OpenAPI spec."
            }
        except Exception as e:
            logger.error(
                f"Unexpected error during introspection for {config['name']}: {e}",
                exc_info=True,
            )
            config["introspected_metadata"] = {
                "error": f"Unexpected introspection error: {e}"
            }
        return config

    async def register_tool(self, config: Dict[str, Any]):
        """
        Asynchronously validates a tool configuration, registers it, performs introspection,
        and persists it to Redis if available.
        """
        tool_name = config.get("name")
        if not tool_name:
            raise ValueError("Tool configuration must include a 'name'.")

        # Perform introspection if it's an HTTP tool
        if config.get("invocation", {}).get("protocol") == "http":
            config = await self._introspect_http_tool(config)

        self._register_tool_from_config(config)

        if self.redis_client is not None:
            try:
                await self.redis_client.set(
                    f"external_tool:{tool_name}", json.dumps(config)
                )
                logger.info(f"Tool '{tool_name}' persisted to Redis.")
            except RedisConnectionError:
                logger.warning(
                    f"Tool '{tool_name}' registered in-memory only (Redis not reachable)."
                )
            except Exception as e:
                logger.error(
                    f"Failed to persist tool '{tool_name}' to Redis: {e}", exc_info=True
                )
                raise
        else:
            logger.warning(
                f"Tool '{tool_name}' registered in-memory only (Redis not configured)."
            )

    async def get_authorized_tools(
        self, user_id: Optional[str], user_groups: List[str]
    ) -> List[Tool]:
        """Asynchronously returns a list of tools that the user is authorized to use."""
        authorized_tools = []
        if self.redis_client is None:
            # No Redis: return all registered tools from in-memory store
            return list(self.registered_tools.values())

        # Load all tools from Redis to check ACLs
        try:
            async for key in self.redis_client.scan_iter("external_tool:*"):
                config_json = await self.redis_client.get(key)
                if config_json:
                    config = json.loads(config_json)
                    tool_id = config.get("name")
                    acl = config.get("acl", {})

                    if acl.get("global"):
                        authorized_tools.append(self.registered_tools[tool_id])
                        continue

                    if user_id and user_id in acl.get("users", []):
                        authorized_tools.append(self.registered_tools[tool_id])
                        continue

                    if user_groups and any(
                        group in acl.get("groups", []) for group in user_groups
                    ):
                        authorized_tools.append(self.registered_tools[tool_id])
                        continue
        except RedisConnectionError:
            logger.warning(
                "Redis not reachable, returning all in-memory registered tools."
            )
            return list(self.registered_tools.values())
        except Exception as e:
            logger.error(
                f"Error retrieving authorized tools from Redis: {e}", exc_info=True
            )
            raise

        return authorized_tools


# Global instance of the tool manager
tool_manager = ExternalToolManager()
