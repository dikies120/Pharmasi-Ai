import sys
import os
from typing import Optional
from pathlib import Path

from back.pharma_mcp.client import MCPClient
from back.core.memory import get_memory_manager
from back.core.agent import Agent

_mcp_client: Optional[MCPClient] = None
_memory_manager = None
_server_script_path: Optional[str] = None


def set_server_script_path(path: str):
    global _server_script_path
    _server_script_path = path


async def get_mcp_client() -> MCPClient:
    global _mcp_client
    
    if _mcp_client is None:
        _mcp_client = MCPClient()
    
    if _mcp_client.session is None and _server_script_path:
        try:
            await _mcp_client.connect(_server_script_path)
        except Exception as e:
            print(f"[ERROR] Failed to connect MCP client: {e}")
    
    return _mcp_client


def get_memory_manager_instance():
    global _memory_manager
    
    if _memory_manager is None:
        _memory_manager = get_memory_manager()
    
    return _memory_manager


def get_agent() -> Agent:
    return Agent()


async def close_mcp_client():
    global _mcp_client
    
    if _mcp_client is not None:
        try:
            await _mcp_client.close()
            _mcp_client = None
        except Exception as e:
            print(f"[ERROR] Failed to close MCP client: {e}")
