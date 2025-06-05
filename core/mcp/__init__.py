"""
MCP (Model Context Protocol) Integration Layer

Provides standardized interfaces for agents to interact with:
- External tools and services
- File systems and git repositories  
- Terminal/command execution
- Web resources and APIs
- Inter-agent communication

This layer abstracts all external interactions through MCP servers,
making them available to agents through a unified protocol.
"""

from .client.mcp_client import MCPClient, get_mcp_client

__all__ = [
    "MCPClient",
    "get_mcp_client"
] 