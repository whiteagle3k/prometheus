"""
Direct MCP Client Implementation

Bypasses the problematic stdio_client and implements direct subprocess communication.
"""

import asyncio
import json
import logging
import subprocess
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DirectMCPCapability:
    """Represents a capability provided by an MCP server."""
    
    def __init__(self, name: str, description: str, server_name: str, tool_name: str):
        self.name = name
        self.description = description
        self.server_name = server_name
        self.tool_name = tool_name


class DirectMCPClient:
    """
    Direct MCP Client Implementation
    
    Uses direct subprocess communication to avoid stdio_client issues.
    """
    
    def __init__(self):
        self.servers: Dict[str, subprocess.Process] = {}
        self.capabilities: Dict[str, DirectMCPCapability] = {}
        self._initialized = False
        self._request_id = 0
        
    def _next_id(self) -> int:
        """Get next request ID."""
        self._request_id += 1
        return self._request_id
        
    async def initialize(self):
        """Initialize MCP client and discover available servers."""
        if self._initialized:
            return
            
        logger.info("🔌 Initializing Direct MCP client...")
        
        # Start all core MCP servers
        await self._start_server("filesystem", "core/mcp/servers/filesystem_server_simple.py")
        await self._start_server("git", "core/mcp/servers/git_server.py")
        await self._start_server("terminal", "core/mcp/servers/terminal_server.py")
        await self._start_server("web", "core/mcp/servers/web_server.py")
        
        # Discover capabilities from all servers
        await self._discover_capabilities()
        
        self._initialized = True
        logger.info(f"✅ Direct MCP client initialized with {len(self.capabilities)} capabilities from {len(self.servers)} servers")
        
    async def _start_server(self, name: str, script_path: str):
        """Start an MCP server subprocess."""
        try:
            logger.info(f"🚀 Starting MCP server: {name}")
            
            # Start server process
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-u", script_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "prometheus-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            request_data = json.dumps(init_request) + '\n'
            proc.stdin.write(request_data.encode())
            await proc.stdin.drain()
            
            # Read initialize response
            response_data = await asyncio.wait_for(
                proc.stdout.readline(), 
                timeout=5.0
            )
            
            if not response_data:
                raise Exception(f"No response from server {name}")
                
            response = json.loads(response_data.decode().strip())
            
            if 'error' in response:
                raise Exception(f"Server {name} returned error: {response['error']}")
            
            # Send initialized notification (required by MCP protocol)
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            }
            
            notification_data = json.dumps(initialized_notification) + '\n'
            proc.stdin.write(notification_data.encode())
            await proc.stdin.drain()
                
            self.servers[name] = proc
            logger.info(f"✅ Started MCP server: {name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start MCP server {name}: {e}")
            if proc:
                proc.terminate()
                await proc.wait()
                
    async def _discover_capabilities(self):
        """Discover capabilities from all connected servers."""
        for server_name, proc in self.servers.items():
            try:
                # List tools request
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": self._next_id(),
                    "method": "tools/list",
                    "params": {}
                }
                
                request_data = json.dumps(tools_request) + '\n'
                proc.stdin.write(request_data.encode())
                await proc.stdin.drain()
                
                # Read response
                response_data = await asyncio.wait_for(
                    proc.stdout.readline(),
                    timeout=5.0
                )
                
                if response_data:
                    response = json.loads(response_data.decode().strip())
                    
                    if 'result' in response and 'tools' in response['result']:
                        tools = response['result']['tools']
                        
                        for tool in tools:
                            capability_name = f"{server_name}_{tool['name']}"
                            
                            capability = DirectMCPCapability(
                                name=capability_name,
                                description=tool.get('description', f"{tool['name']} tool from {server_name}"),
                                server_name=server_name,
                                tool_name=tool['name']
                            )
                            
                            self.capabilities[capability_name] = capability
                            
                        logger.info(f"📋 Discovered {len(tools)} capabilities from {server_name}")
                
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
        proc = self.servers[capability.server_name]
        
        try:
            # Call tool request
            call_request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {
                    "name": capability.tool_name,
                    "arguments": arguments
                }
            }
            
            request_data = json.dumps(call_request) + '\n'
            proc.stdin.write(request_data.encode())
            await proc.stdin.drain()
            
            # Read response
            response_data = await asyncio.wait_for(
                proc.stdout.readline(),
                timeout=10.0
            )
            
            if not response_data:
                raise Exception("No response from server")
                
            response = json.loads(response_data.decode().strip())
            
            if 'error' in response:
                raise Exception(f"Server error: {response['error']}")
                
            return {
                "success": True,
                "result": response['result']['content'],
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
    
    # Git operations
    
    async def git_status(self, cwd: str = ".") -> Dict[str, Any]:
        """Get git status through git server."""
        return await self.execute_capability("git_status", {"cwd": cwd})
    
    async def git_diff(self, cwd: str = ".", cached: bool = False, file: str = None) -> Dict[str, Any]:
        """Get git diff through git server."""
        args = {"cwd": cwd, "cached": cached}
        if file:
            args["file"] = file
        return await self.execute_capability("git_diff", args)
    
    async def git_add(self, files: List[str], cwd: str = ".") -> Dict[str, Any]:
        """Add files to git through git server."""
        return await self.execute_capability("git_add", {"files": files, "cwd": cwd})
    
    async def git_commit(self, message: str, cwd: str = ".", amend: bool = False) -> Dict[str, Any]:
        """Create git commit through git server."""
        return await self.execute_capability("git_commit", {"message": message, "cwd": cwd, "amend": amend})
    
    async def git_branch(self, action: str, name: str = None, cwd: str = ".") -> Dict[str, Any]:
        """Git branch operations through git server."""
        args = {"action": action, "cwd": cwd}
        if name:
            args["name"] = name
        return await self.execute_capability("git_branch", args)
    
    async def git_push(self, remote: str = "origin", branch: str = None, cwd: str = ".", force: bool = False) -> Dict[str, Any]:
        """Push to git remote through git server."""
        args = {"remote": remote, "cwd": cwd, "force": force}
        if branch:
            args["branch"] = branch
        return await self.execute_capability("git_push", args)
    
    async def git_pull(self, remote: str = "origin", branch: str = None, cwd: str = ".") -> Dict[str, Any]:
        """Pull from git remote through git server."""
        args = {"remote": remote, "cwd": cwd}
        if branch:
            args["branch"] = branch
        return await self.execute_capability("git_pull", args)
    
    async def git_log(self, limit: int = 10, oneline: bool = True, cwd: str = ".") -> Dict[str, Any]:
        """Get git log through git server."""
        return await self.execute_capability("git_log", {"limit": limit, "oneline": oneline, "cwd": cwd})
    
    # Terminal operations
    
    async def execute_command(self, command: str, cwd: str = ".", timeout: int = 30, shell: bool = True) -> Dict[str, Any]:
        """Execute command through terminal server."""
        return await self.execute_capability("terminal_execute", {
            "command": command,
            "cwd": cwd,
            "timeout": timeout,
            "shell": shell
        })
    
    async def run_script(self, script_path: str, args: List[str] = None, cwd: str = ".", timeout: int = 60) -> Dict[str, Any]:
        """Run script through terminal server."""
        return await self.execute_capability("terminal_run_script", {
            "script_path": script_path,
            "args": args or [],
            "cwd": cwd,
            "timeout": timeout
        })
    
    async def get_env(self, name: str, default: str = None) -> Dict[str, Any]:
        """Get environment variable through terminal server."""
        args = {"name": name}
        if default is not None:
            args["default"] = default
        return await self.execute_capability("terminal_get_env", args)
    
    async def set_env(self, name: str, value: str) -> Dict[str, Any]:
        """Set environment variable through terminal server."""
        return await self.execute_capability("terminal_set_env", {"name": name, "value": value})
    
    async def list_processes(self, filter_pattern: str = None) -> Dict[str, Any]:
        """List processes through terminal server."""
        args = {}
        if filter_pattern:
            args["filter"] = filter_pattern
        return await self.execute_capability("terminal_list_processes", args)
    
    async def which_command(self, command: str) -> Dict[str, Any]:
        """Find command location through terminal server."""
        return await self.execute_capability("terminal_which", {"command": command})
    
    async def get_pwd(self) -> Dict[str, Any]:
        """Get current working directory through terminal server."""
        return await self.execute_capability("terminal_pwd", {})
    
    # Web operations
    
    async def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web through web server."""
        return await self.execute_capability("web_search", {"query": query, "max_results": max_results})
    
    async def http_get(self, url: str, headers: Dict[str, str] = None, timeout: int = 10) -> Dict[str, Any]:
        """Make HTTP GET request through web server."""
        args = {"url": url, "timeout": timeout}
        if headers:
            args["headers"] = headers
        return await self.execute_capability("web_http_get", args)
    
    async def http_post(self, url: str, data: Any = None, headers: Dict[str, str] = None, timeout: int = 10) -> Dict[str, Any]:
        """Make HTTP POST request through web server."""
        args = {"url": url, "timeout": timeout}
        if data:
            args["data"] = data
        if headers:
            args["headers"] = headers
        return await self.execute_capability("web_http_post", args)
    
    async def scrape_text(self, url: str, selector: str = None, timeout: int = 10) -> Dict[str, Any]:
        """Scrape text from web page through web server."""
        args = {"url": url, "timeout": timeout}
        if selector:
            args["selector"] = selector
        return await self.execute_capability("web_scrape_text", args)
    
    async def validate_url(self, url: str) -> Dict[str, Any]:
        """Validate URL through web server."""
        return await self.execute_capability("web_validate_url", {"url": url})
    
    async def check_status(self, url: str, timeout: int = 5) -> Dict[str, Any]:
        """Check URL status through web server."""
        return await self.execute_capability("web_check_status", {"url": url, "timeout": timeout})
    
    async def shutdown(self):
        """Shutdown all MCP server connections."""
        for name, proc in self.servers.items():
            try:
                proc.terminate()
                await proc.wait()
                logger.info(f"🔌 Closed MCP server: {name}")
            except Exception as e:
                logger.error(f"❌ Error closing {name}: {e}")
        
        self.servers.clear()
        self.capabilities.clear()
        self._initialized = False


# Global MCP client instance
_direct_mcp_client: Optional[DirectMCPClient] = None

async def get_direct_mcp_client() -> DirectMCPClient:
    """Get or create global Direct MCP client instance."""
    global _direct_mcp_client
    if _direct_mcp_client is None:
        _direct_mcp_client = DirectMCPClient()
        await _direct_mcp_client.initialize()
    return _direct_mcp_client 