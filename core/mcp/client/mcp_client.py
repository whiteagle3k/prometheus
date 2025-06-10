"""
MCP Client for Agent Integration

Provides a unified interface for agents to interact with MCP servers.
Handles connection management, tool discovery, and execution.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPCapability:
    """Represents a capability provided by an MCP server."""
    
    def __init__(self, name: str, description: str, server_name: str, tool_name: str):
        self.name = name
        self.description = description
        self.server_name = server_name
        self.tool_name = tool_name


class MCPClient:
    """
    MCP Client for Agent Integration
    
    Provides agents with standardized access to external capabilities
    through MCP servers (filesystem, git, terminal, web, etc.)
    """
    
    def __init__(self):
        self.servers: Dict[str, Any] = {}
        self.capabilities: Dict[str, MCPCapability] = {}
        self.sessions: Dict[str, ClientSession] = {}
        self.contexts: Dict[str, Any] = {}  # Store context managers
        self._initialized = False
        
    async def initialize(self):
        """Initialize MCP client and discover available servers."""
        if self._initialized:
            return
            
        logger.info("🔌 Initializing MCP client...")
        
        # Start core environment servers
        await self._start_server("filesystem", "core/mcp/servers/filesystem_server_simple.py")
        await self._start_server("git", "core/mcp/servers/git_server.py") 
        await self._start_server("terminal", "core/mcp/servers/terminal_server.py")
        await self._start_server("web", "core/mcp/servers/web_server.py")
        await self._start_server("agent_communication", "core/mcp/servers/agent_communication_server.py")
        
        # Discover capabilities from all servers
        await self._discover_capabilities()
        
        self._initialized = True
        logger.info(f"✅ MCP client initialized with {len(self.capabilities)} capabilities")
        
    async def _start_server(self, name: str, script_path: str):
        """Start an MCP server subprocess."""
        print(f"🔧 DEBUG: Attempting to start MCP server: {name} with script: {script_path}")
        try:
            import sys
            
            server_params = StdioServerParameters(
                command=sys.executable,
                args=["-u", script_path],
                env=None
            )
            
            print(f"🔧 DEBUG: Created server params for {name}")
            
            # Create and store the context manager
            context = stdio_client(server_params)
            self.contexts[name] = context
            
            print(f"🔧 DEBUG: Created context for {name}, entering...")
            
            # Enter the context and store streams
            read_stream, write_stream = await context.__aenter__()
            
            print(f"🔧 DEBUG: Got streams for {name}, creating session...")
            
            # Create session with the streams
            session = ClientSession(read_stream, write_stream)
            
            print(f"🔧 DEBUG: Created session for {name}, initializing...")
            
            try:
                await asyncio.wait_for(session.initialize(), timeout=2)
                print(f"🔧 DEBUG: Session initialized for {name}")
            except asyncio.TimeoutError:
                print(f"🔧 DEBUG: Timeout initializing {name}")
                raise RuntimeError("MCP handshake timed-out – "
                                 "проверь, что сервер запущен в stdio")
            except Exception as e:
                print(f"🔧 DEBUG: Exception during {name} initialization: {e}")
                raise
            
            self.sessions[name] = session
            logger.info(f"🚀 Started MCP server: {name}")
            print(f"🔧 DEBUG: Successfully started {name}")
            
        except Exception as e:
            print(f"🔧 DEBUG: Exception starting {name}: {e}")
            logger.error(f"❌ Failed to start MCP server {name}: {e}")
            # Clean up context if it was created
            if name in self.contexts:
                try:
                    await self.contexts[name].__aexit__(None, None, None)
                except:
                    pass
                del self.contexts[name]
            
    async def _discover_capabilities(self):
        """Discover capabilities from all connected servers."""
        for server_name, session in self.sessions.items():
            try:
                # List available tools from server
                tools_result = await session.list_tools()
                
                for tool in tools_result.tools:
                    capability_name = f"{server_name}_{tool.name}"
                    
                    capability = MCPCapability(
                        name=capability_name,
                        description=tool.description or f"{tool.name} tool from {server_name}",
                        server_name=server_name,
                        tool_name=tool.name
                    )
                    
                    self.capabilities[capability_name] = capability
                    
                logger.info(f"📋 Discovered {len(tools_result.tools)} capabilities from {server_name}")
                
            except Exception as e:
                logger.error(f"❌ Failed to discover capabilities from {server_name}: {e}")
    
    async def get_available_capabilities(self) -> List[Dict[str, str]]:
        """Get list of available capabilities for agents."""
        if not self._initialized:
            await self.initialize()
            
        return [
            {
                "name": cap.name,
                "description": cap.description,
                "server": cap.server_name,
                "tool": cap.tool_name
            }
            for cap in self.capabilities.values()
        ]
    
    async def execute_capability(
        self, 
        capability_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a capability through its MCP server."""
        if not self._initialized:
            await self.initialize()
            
        if capability_name not in self.capabilities:
            raise ValueError(f"Capability '{capability_name}' not found")
            
        capability = self.capabilities[capability_name]
        session = self.sessions[capability.server_name]
        
        try:
            # Execute tool through MCP
            result = await session.call_tool(
                capability.tool_name,
                arguments
            )
            
            return {
                "success": True,
                "result": result.content,
                "capability": capability_name,
                "server": capability.server_name
            }
            
        except Exception as e:
            logger.error(f"❌ Error executing {capability_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "capability": capability_name,
                "server": capability.server_name
            }
    
    # Convenience methods for common operations
    
    async def read_file(self, path: str) -> Dict[str, Any]:
        """Read file contents through filesystem server."""
        return await self.execute_capability("filesystem_read_file", {"path": path})
    
    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write file contents through filesystem server."""
        return await self.execute_capability("filesystem_write_file", {
            "path": path,
            "content": content
        })
    
    async def list_directory(self, path: str) -> Dict[str, Any]:
        """List directory contents through filesystem server."""
        return await self.execute_capability("filesystem_list_directory", {"path": path})
    
    async def git_status(self) -> Dict[str, Any]:
        """Get git status through git server."""
        return await self.execute_capability("git_status", {})
    
    async def git_commit(self, message: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create git commit through git server."""
        args = {"message": message}
        if files:
            args["files"] = files
        return await self.execute_capability("git_commit", args)
    
    async def execute_command(self, command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Execute terminal command through terminal server."""
        args = {"command": command}
        if cwd:
            args["cwd"] = cwd
        return await self.execute_capability("terminal_execute", args)
    
    async def web_search(self, query: str) -> Dict[str, Any]:
        """Perform web search through web server."""
        return await self.execute_capability("web_search", {"query": query})
    
    # Agent Communication methods
    
    async def send_message_to_agent(self, target_agent: str, message: str, task_type: str = "general", priority: str = "medium") -> Dict[str, Any]:
        """Send a message to another agent."""
        return await self.execute_capability("agent_communication_agent_send_message", {
            "target_agent": target_agent,
            "message": message,
            "task_type": task_type,
            "priority": priority
        })
    
    async def delegate_task_to_agent(self, target_agent: str, task_title: str, task_description: str, 
                                   acceptance_criteria: Optional[List[str]] = None, priority: str = "medium", 
                                   deadline: Optional[str] = None) -> Dict[str, Any]:
        """Delegate a task to another agent with tracking."""
        args = {
            "target_agent": target_agent,
            "task_title": task_title,
            "task_description": task_description,
            "priority": priority
        }
        if acceptance_criteria:
            args["acceptance_criteria"] = acceptance_criteria
        if deadline:
            args["deadline"] = deadline
        return await self.execute_capability("agent_communication_agent_delegate_task", args)
    
    async def get_agent_status(self, target_agent: Optional[str] = None) -> Dict[str, Any]:
        """Get status of agents."""
        args = {}
        if target_agent:
            args["target_agent"] = target_agent
        return await self.execute_capability("agent_communication_agent_get_status", args)
    
    async def get_active_tasks(self, filter_by_agent: Optional[str] = None, filter_by_status: Optional[str] = None) -> Dict[str, Any]:
        """Get list of active tasks."""
        args = {}
        if filter_by_agent:
            args["filter_by_agent"] = filter_by_agent
        if filter_by_status:
            args["filter_by_status"] = filter_by_status
        return await self.execute_capability("agent_communication_agent_get_active_tasks", args)
    
    async def update_task_status(self, task_id: str, status: str, result: Optional[str] = None, 
                               next_agent: Optional[str] = None) -> Dict[str, Any]:
        """Update status of a delegated task."""
        args = {"task_id": task_id, "status": status}
        if result:
            args["result"] = result
        if next_agent:
            args["next_agent"] = next_agent
        return await self.execute_capability("agent_communication_agent_update_task_status", args)
    
    async def shutdown(self):
        """Shutdown all MCP server connections."""
        # Close sessions first
        for name, session in self.sessions.items():
            try:
                await session.close()
                logger.info(f"🔌 Closed MCP session: {name}")
            except Exception as e:
                logger.error(f"❌ Error closing session {name}: {e}")
        
        # Exit context managers
        for name, context in self.contexts.items():
            try:
                await context.__aexit__(None, None, None)
                logger.info(f"🔌 Closed MCP context: {name}")
            except Exception as e:
                logger.error(f"❌ Error closing context {name}: {e}")
        
        self.sessions.clear()
        self.contexts.clear()
        self.capabilities.clear()
        self._initialized = False


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None

async def get_mcp_client() -> MCPClient:
    """Get or create global MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
        await _mcp_client.initialize()
    return _mcp_client 