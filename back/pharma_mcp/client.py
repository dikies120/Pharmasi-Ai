import sys
import asyncio
import logging
from contextlib import AsyncExitStack
from typing import Optional, Any, List, Dict

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._stdio = None
        self._write = None
        self._tools_cache: Optional[List[str]] = None

    async def connect(self, server_script_path: str) -> bool:
        if self.session is not None:
            logger.warning("MCP Client sudah connected, skip reconnect")
            return True
            
        if not (server_script_path.endswith(".py") or server_script_path.endswith(".js")):
            raise ValueError("Server script must be a .py or .js file")

        command = sys.executable if server_script_path.endswith(".py") else "node"
        logger.info(f"Connecting to MCP Server: {server_script_path}")

        try:
            server_params = StdioServerParameters(
                command=command,
                args=[server_script_path],
                env=None,
            )

            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self._stdio, self._write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self._stdio, self._write)
            )

            await self.session.initialize()
            logger.info(" Connected to MCP Server successfully")
            return True
            
        except Exception as e:
            logger.error(f" Failed to connect MCP Server: {e}")
            self.session = None
            raise

    async def list_tools(self) -> List[str]:
        if self.session is None:
            raise RuntimeError("MCP session belum connect. Call connect() dulu.")

        try:
            # Return from cache jika sudah di-fetch
            if self._tools_cache is not None:
                return self._tools_cache
                
            response = await self.session.list_tools()
            self._tools_cache = [tool.name for tool in response.tools]
            logger.info(f" Available tools: {self._tools_cache}")
            return self._tools_cache
            
        except Exception as e:
            logger.error(f" Failed to list tools: {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.session is None:
            raise RuntimeError("MCP session belum connect")

        # Validate tool exists
        available_tools = await self.list_tools()
        if tool_name not in available_tools:
            raise ValueError(f"Tool '{tool_name}' not found. Available: {available_tools}")

        try:
            logger.info(f" Calling tool: {tool_name} with args: {arguments}")
            result = await self.session.call_tool(tool_name, arguments)
            logger.info(f" Tool '{tool_name}' executed successfully")
            return result
            
        except Exception as e:
            logger.error(f" Failed to call tool '{tool_name}': {e}")
            raise

    async def close(self):
        try:
            await self.exit_stack.aclose()
            self.session = None
            self._tools_cache = None
            logger.info(" MCP Client closed")
        except Exception as e:
            logger.error(f" Error closing MCP Client: {e}")