"""
core/mcp — Model Context Protocol layer for the human-ai swarm.

Exports:
    MCPServer   — HTTP/JSON gateway that openclaw runs.
    A2AClient   — Client for direct agent-to-agent RPC calls.
"""
from .mcp_server import MCPServer, ToolRegistry
from .a2a_client import A2AClient, A2AMessage, A2AResponse

__all__ = [
    "MCPServer",
    "ToolRegistry",
    "A2AClient",
    "A2AMessage",
    "A2AResponse",
]
