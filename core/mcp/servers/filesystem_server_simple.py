#!/usr/bin/env python3
"""
Simple Filesystem MCP Server using FastMCP

Provides basic file system operations as MCP tools.
"""

from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Filesystem")


@mcp.tool()
def read_file(path: str) -> str:
    """Read the contents of a file"""
    try:
        file_path = Path(path)
        
        if not file_path.exists():
            return f"Error: File '{path}' does not exist"
        
        if not file_path.is_file():
            return f"Error: '{path}' is not a file"
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return f"File content of '{path}':\n\n{content}"
        
    except UnicodeDecodeError:
        return f"Error: Cannot read '{path}' - appears to be a binary file"
    except Exception as e:
        return f"Error reading file '{path}': {str(e)}"


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write content to a file"""
    try:
        file_path = Path(path)
        
        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"Successfully wrote {len(content)} characters to '{path}'"
        
    except Exception as e:
        return f"Error writing to file '{path}': {str(e)}"


@mcp.tool()
def list_directory(path: str, show_hidden: bool = False) -> str:
    """List contents of a directory"""
    try:
        dir_path = Path(path)
        
        if not dir_path.exists():
            return f"Error: Directory '{path}' does not exist"
        
        if not dir_path.is_dir():
            return f"Error: '{path}' is not a directory"
        
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
        
        return f"Contents of '{path}':\n\n{listing}"
        
    except Exception as e:
        return f"Error listing directory '{path}': {str(e)}"


if __name__ == "__main__":
    mcp.run()  # ✅ stdio-transport (default) 