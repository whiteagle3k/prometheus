#!/usr/bin/env python3
"""
Terminal MCP Server

Provides terminal/command execution as MCP tools:
- Execute shell commands
- Run scripts
- Process management
- Environment variable access
"""

import asyncio
import os
import subprocess
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server


# Initialize the MCP server
app = Server("terminal")


@app.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available terminal tools."""
    return [
        types.Tool(
            name="execute",
            description="Execute a shell command",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory for command execution",
                        "default": "."
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                        "default": 30
                    },
                    "shell": {
                        "type": "boolean",
                        "description": "Whether to use shell for execution",
                        "default": True
                    }
                },
                "required": ["command"]
            }
        ),
        types.Tool(
            name="run_script",
            description="Run a script file",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_path": {
                        "type": "string",
                        "description": "Path to script file"
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Arguments to pass to script",
                        "default": []
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory",
                        "default": "."
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                        "default": 60
                    }
                },
                "required": ["script_path"]
            }
        ),
        types.Tool(
            name="get_env",
            description="Get environment variable",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Environment variable name"
                    },
                    "default": {
                        "type": "string",
                        "description": "Default value if not found"
                    }
                },
                "required": ["name"]
            }
        ),
        types.Tool(
            name="set_env",
            description="Set environment variable for current session",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Environment variable name"
                    },
                    "value": {
                        "type": "string",
                        "description": "Environment variable value"
                    }
                },
                "required": ["name", "value"]
            }
        ),
        types.Tool(
            name="list_processes",
            description="List running processes (basic ps)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "description": "Filter processes by name pattern"
                    }
                }
            }
        ),
        types.Tool(
            name="which",
            description="Find location of executable",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to locate"
                    }
                },
                "required": ["command"]
            }
        ),
        types.Tool(
            name="pwd",
            description="Get current working directory",
            inputSchema={"type": "object", "properties": {}}
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls."""
    
    if name == "execute":
        command = arguments["command"]
        cwd = arguments.get("cwd", ".")
        timeout = arguments.get("timeout", 30)
        shell = arguments.get("shell", True)
        return await execute_command(command, cwd, timeout, shell)
    elif name == "run_script":
        script_path = arguments["script_path"]
        args = arguments.get("args", [])
        cwd = arguments.get("cwd", ".")
        timeout = arguments.get("timeout", 60)
        return await run_script(script_path, args, cwd, timeout)
    elif name == "get_env":
        env_name = arguments["name"]
        default = arguments.get("default")
        return await get_env_var(env_name, default)
    elif name == "set_env":
        name = arguments["name"]
        value = arguments["value"]
        return await set_env_var(name, value)
    elif name == "list_processes":
        filter_pattern = arguments.get("filter")
        return await list_processes(filter_pattern)
    elif name == "which":
        command = arguments["command"]
        return await which_command(command)
    elif name == "pwd":
        return await get_pwd()
    else:
        raise ValueError(f"Unknown tool: {name}")


async def execute_command(
    command: str, 
    cwd: str = ".", 
    timeout: int = 30, 
    shell: bool = True
) -> List[types.TextContent]:
    """Execute a shell command."""
    try:
        # Sanitize and prepare command
        if not shell:
            # Split command for non-shell execution
            cmd_args = shlex.split(command)
        else:
            cmd_args = command
        
        # Execute command
        result = subprocess.run(
            cmd_args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=shell
        )
        
        # Format output
        output_parts = []
        output_parts.append(f"Command: {command}")
        output_parts.append(f"Exit Code: {result.returncode}")
        
        if result.stdout:
            output_parts.append(f"STDOUT:\n{result.stdout}")
        
        if result.stderr:
            output_parts.append(f"STDERR:\n{result.stderr}")
        
        if not result.stdout and not result.stderr:
            output_parts.append("No output produced")
        
        return [types.TextContent(
            type="text",
            text="\n\n".join(output_parts)
        )]
        
    except subprocess.TimeoutExpired:
        return [types.TextContent(
            type="text",
            text=f"Command '{command}' timed out after {timeout} seconds"
        )]
    except FileNotFoundError:
        return [types.TextContent(
            type="text",
            text=f"Command not found: {command}"
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error executing command '{command}': {str(e)}"
        )]


async def run_script(
    script_path: str, 
    args: List[str] = None, 
    cwd: str = ".", 
    timeout: int = 60
) -> List[types.TextContent]:
    """Run a script file."""
    try:
        script_path_obj = Path(script_path)
        
        if not script_path_obj.exists():
            return [types.TextContent(
                type="text",
                text=f"Script not found: {script_path}"
            )]
        
        if not script_path_obj.is_file():
            return [types.TextContent(
                type="text",
                text=f"Path is not a file: {script_path}"
            )]
        
        # Determine interpreter based on file extension
        interpreters = {
            '.py': 'python',
            '.sh': 'bash',
            '.js': 'node',
            '.rb': 'ruby',
            '.pl': 'perl'
        }
        
        ext = script_path_obj.suffix.lower()
        interpreter = interpreters.get(ext)
        
        if interpreter:
            # Use interpreter
            cmd = [interpreter, str(script_path_obj)] + (args or [])
        else:
            # Try to execute directly (assumes executable)
            cmd = [str(script_path_obj)] + (args or [])
        
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # Format output
        output_parts = []
        output_parts.append(f"Script: {script_path}")
        if args:
            output_parts.append(f"Args: {' '.join(args)}")
        output_parts.append(f"Exit Code: {result.returncode}")
        
        if result.stdout:
            output_parts.append(f"STDOUT:\n{result.stdout}")
        
        if result.stderr:
            output_parts.append(f"STDERR:\n{result.stderr}")
        
        return [types.TextContent(
            type="text",
            text="\n\n".join(output_parts)
        )]
        
    except subprocess.TimeoutExpired:
        return [types.TextContent(
            type="text",
            text=f"Script '{script_path}' timed out after {timeout} seconds"
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error running script '{script_path}': {str(e)}"
        )]


async def get_env_var(name: str, default: Optional[str] = None) -> List[types.TextContent]:
    """Get environment variable."""
    try:
        value = os.environ.get(name, default)
        
        if value is None:
            return [types.TextContent(
                type="text",
                text=f"Environment variable '{name}' not found"
            )]
        
        return [types.TextContent(
            type="text",
            text=f"Environment variable '{name}': {value}"
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error getting environment variable '{name}': {str(e)}"
        )]


async def set_env_var(name: str, value: str) -> List[types.TextContent]:
    """Set environment variable for current session."""
    try:
        os.environ[name] = value
        
        return [types.TextContent(
            type="text",
            text=f"Set environment variable '{name}' = '{value}'"
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error setting environment variable '{name}': {str(e)}"
        )]


async def list_processes(filter_pattern: Optional[str] = None) -> List[types.TextContent]:
    """List running processes."""
    try:
        if filter_pattern:
            # Use ps with grep for filtering
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return [types.TextContent(
                    type="text",
                    text=f"Error listing processes: {result.stderr}"
                )]
            
            # Filter processes
            lines = result.stdout.split('\n')
            filtered_lines = [lines[0]]  # Header
            for line in lines[1:]:
                if filter_pattern.lower() in line.lower():
                    filtered_lines.append(line)
            
            if len(filtered_lines) == 1:
                return [types.TextContent(
                    type="text",
                    text=f"No processes found matching '{filter_pattern}'"
                )]
            
            output = '\n'.join(filtered_lines)
        else:
            # List all processes (limited)
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return [types.TextContent(
                    type="text",
                    text=f"Error listing processes: {result.stderr}"
                )]
            
            # Limit output to prevent overwhelming
            lines = result.stdout.split('\n')[:20]
            output = '\n'.join(lines)
            if len(result.stdout.split('\n')) > 20:
                output += "\n... (output truncated, use filter for specific processes)"
        
        return [types.TextContent(
            type="text",
            text=f"Running Processes:\n\n{output}"
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error listing processes: {str(e)}"
        )]


async def which_command(command: str) -> List[types.TextContent]:
    """Find location of executable."""
    try:
        result = subprocess.run(
            ["which", command],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return [types.TextContent(
                type="text",
                text=f"'{command}' found at: {result.stdout.strip()}"
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"Command '{command}' not found in PATH"
            )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error locating command '{command}': {str(e)}"
        )]


async def get_pwd() -> List[types.TextContent]:
    """Get current working directory."""
    try:
        cwd = os.getcwd()
        return [types.TextContent(
            type="text",
            text=f"Current working directory: {cwd}"
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error getting current directory: {str(e)}"
        )]


async def main():
    """Run the terminal MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main()) 