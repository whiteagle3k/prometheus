#!/usr/bin/env python3
"""
Filesystem MCP Server

Provides file system operations as MCP tools:
- Read file contents
- Write file contents  
- List directory contents
- Create directories
- Delete files/directories
- File metadata operations
"""

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server


# Initialize the MCP server
app = Server("filesystem")


@app.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available filesystem tools."""
    return [
        types.Tool(
            name="read_file",
            description="Read the contents of a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["path"]
            }
        ),
        types.Tool(
            name="write_file", 
            description="Write content to a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        ),
        types.Tool(
            name="list_directory",
            description="List contents of a directory",
            inputSchema={
                "type": "object", 
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the directory to list"
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "description": "Whether to show hidden files",
                        "default": False
                    }
                },
                "required": ["path"]
            }
        ),
        types.Tool(
            name="create_directory",
            description="Create a new directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the directory to create"
                    },
                    "parents": {
                        "type": "boolean", 
                        "description": "Whether to create parent directories",
                        "default": True
                    }
                },
                "required": ["path"]
            }
        ),
        types.Tool(
            name="delete_path",
            description="Delete a file or directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to delete"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to delete directories recursively", 
                        "default": False
                    }
                },
                "required": ["path"]
            }
        ),
        types.Tool(
            name="get_file_info",
            description="Get metadata information about a file or directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to get information about"
                    }
                },
                "required": ["path"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls."""
    
    if name == "read_file":
        return await read_file(arguments["path"])
    elif name == "write_file":
        return await write_file(arguments["path"], arguments["content"])
    elif name == "list_directory":
        show_hidden = arguments.get("show_hidden", False)
        return await list_directory(arguments["path"], show_hidden)
    elif name == "create_directory":
        parents = arguments.get("parents", True)
        return await create_directory(arguments["path"], parents)
    elif name == "delete_path":
        recursive = arguments.get("recursive", False)
        return await delete_path(arguments["path"], recursive)
    elif name == "get_file_info":
        return await get_file_info(arguments["path"])
    else:
        raise ValueError(f"Unknown tool: {name}")


async def read_file(path: str) -> List[types.TextContent]:
    """Read file contents."""
    try:
        file_path = Path(path)
        
        if not file_path.exists():
            return [types.TextContent(
                type="text",
                text=f"Error: File '{path}' does not exist"
            )]
        
        if not file_path.is_file():
            return [types.TextContent(
                type="text", 
                text=f"Error: '{path}' is not a file"
            )]
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return [types.TextContent(
            type="text",
            text=f"File content of '{path}':\n\n{content}"
        )]
        
    except UnicodeDecodeError:
        return [types.TextContent(
            type="text",
            text=f"Error: Cannot read '{path}' - appears to be a binary file"
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error reading file '{path}': {str(e)}"
        )]


async def write_file(path: str, content: str) -> List[types.TextContent]:
    """Write content to file."""
    try:
        file_path = Path(path)
        
        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return [types.TextContent(
            type="text",
            text=f"Successfully wrote {len(content)} characters to '{path}'"
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error writing to file '{path}': {str(e)}"
        )]


async def list_directory(path: str, show_hidden: bool = False) -> List[types.TextContent]:
    """List directory contents."""
    try:
        dir_path = Path(path)
        
        if not dir_path.exists():
            return [types.TextContent(
                type="text",
                text=f"Error: Directory '{path}' does not exist"
            )]
        
        if not dir_path.is_dir():
            return [types.TextContent(
                type="text",
                text=f"Error: '{path}' is not a directory"
            )]
        
        # List directory contents
        items = []
        for item in sorted(dir_path.iterdir()):
            # Skip hidden files unless requested
            if not show_hidden and item.name.startswith('.'):
                continue
                
            item_type = "directory" if item.is_dir() else "file"
            size = item.stat().st_size if item.is_file() else "-"
            items.append(f"{item_type:>9} {size:>10} {item.name}")
        
        if not items:
            listing = "Directory is empty"
        else:
            header = f"{'Type':>9} {'Size':>10} Name\n" + "-" * 40
            listing = f"{header}\n" + "\n".join(items)
        
        return [types.TextContent(
            type="text",
            text=f"Contents of '{path}':\n\n{listing}"
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error listing directory '{path}': {str(e)}"
        )]


async def create_directory(path: str, parents: bool = True) -> List[types.TextContent]:
    """Create a directory."""
    try:
        dir_path = Path(path)
        
        if dir_path.exists():
            return [types.TextContent(
                type="text",
                text=f"Directory '{path}' already exists"
            )]
        
        # Create directory
        dir_path.mkdir(parents=parents, exist_ok=False)
        
        return [types.TextContent(
            type="text",
            text=f"Successfully created directory '{path}'"
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error creating directory '{path}': {str(e)}"
        )]


async def delete_path(path: str, recursive: bool = False) -> List[types.TextContent]:
    """Delete a file or directory."""
    try:
        target_path = Path(path)
        
        if not target_path.exists():
            return [types.TextContent(
                type="text",
                text=f"Error: Path '{path}' does not exist"
            )]
        
        if target_path.is_file():
            target_path.unlink()
            return [types.TextContent(
                type="text",
                text=f"Successfully deleted file '{path}'"
            )]
        elif target_path.is_dir():
            if recursive:
                shutil.rmtree(target_path)
                return [types.TextContent(
                    type="text",
                    text=f"Successfully deleted directory '{path}' and all contents"
                )]
            else:
                # Try to remove empty directory
                target_path.rmdir()
                return [types.TextContent(
                    type="text",
                    text=f"Successfully deleted empty directory '{path}'"
                )]
        else:
            return [types.TextContent(
                type="text",
                text=f"Error: '{path}' is neither a file nor directory"
            )]
        
    except OSError as e:
        if "Directory not empty" in str(e):
            return [types.TextContent(
                type="text",
                text=f"Error: Directory '{path}' is not empty. Use recursive=true to delete with contents"
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"Error deleting '{path}': {str(e)}"
            )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error deleting '{path}': {str(e)}"
        )]


async def get_file_info(path: str) -> List[types.TextContent]:
    """Get file/directory metadata."""
    try:
        target_path = Path(path)
        
        if not target_path.exists():
            return [types.TextContent(
                type="text",
                text=f"Error: Path '{path}' does not exist"
            )]
        
        stat = target_path.stat()
        
        info = [
            f"Path: {path}",
            f"Type: {'Directory' if target_path.is_dir() else 'File'}",
            f"Size: {stat.st_size} bytes",
            f"Modified: {stat.st_mtime}",
            f"Permissions: {oct(stat.st_mode)[-3:]}",
        ]
        
        if target_path.is_file():
            info.append(f"Extension: {target_path.suffix}")
        
        return [types.TextContent(
            type="text", 
            text=f"Information for '{path}':\n\n" + "\n".join(info)
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error getting info for '{path}': {str(e)}"
        )]


async def main():
    """Run the filesystem MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main()) 