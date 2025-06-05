#!/usr/bin/env python3
"""
Git MCP Server

Provides git operations as MCP tools:
- Status and diff operations
- Branch management
- Commit operations
- Push/pull operations
- Repository information
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server


# Initialize the MCP server
app = Server("git")


@app.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available git tools."""
    return [
        types.Tool(
            name="status",
            description="Get git repository status",
            inputSchema={
                "type": "object",
                "properties": {
                    "cwd": {
                        "type": "string",
                        "description": "Working directory (defaults to current)",
                        "default": "."
                    }
                }
            }
        ),
        types.Tool(
            name="diff",
            description="Show git diff",
            inputSchema={
                "type": "object",
                "properties": {
                    "cwd": {
                        "type": "string", 
                        "description": "Working directory",
                        "default": "."
                    },
                    "cached": {
                        "type": "boolean",
                        "description": "Show staged changes only",
                        "default": False
                    },
                    "file": {
                        "type": "string",
                        "description": "Specific file to diff"
                    }
                }
            }
        ),
        types.Tool(
            name="add",
            description="Add files to git staging area",
            inputSchema={
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to add (use ['.'] for all)"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory",
                        "default": "."
                    }
                },
                "required": ["files"]
            }
        ),
        types.Tool(
            name="commit",
            description="Create a git commit",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Commit message"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory", 
                        "default": "."
                    },
                    "amend": {
                        "type": "boolean",
                        "description": "Amend the last commit",
                        "default": False
                    }
                },
                "required": ["message"]
            }
        ),
        types.Tool(
            name="branch",
            description="Branch operations",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "create", "delete", "checkout", "current"],
                        "description": "Branch action to perform"
                    },
                    "name": {
                        "type": "string",
                        "description": "Branch name (for create/delete/checkout)"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory",
                        "default": "."
                    }
                },
                "required": ["action"]
            }
        ),
        types.Tool(
            name="push",
            description="Push commits to remote repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "remote": {
                        "type": "string",
                        "description": "Remote name",
                        "default": "origin"
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (defaults to current)"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory",
                        "default": "."
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force push",
                        "default": False
                    }
                }
            }
        ),
        types.Tool(
            name="pull",
            description="Pull changes from remote repository",
            inputSchema={
                "type": "object", 
                "properties": {
                    "remote": {
                        "type": "string",
                        "description": "Remote name",
                        "default": "origin"
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (defaults to current)"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory",
                        "default": "."
                    }
                }
            }
        ),
        types.Tool(
            name="log",
            description="Show git commit history",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of commits to show",
                        "default": 10
                    },
                    "oneline": {
                        "type": "boolean",
                        "description": "Show one line per commit",
                        "default": True
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory",
                        "default": "."
                    }
                }
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls."""
    
    cwd = arguments.get("cwd", ".")
    
    if name == "status":
        return await git_status(cwd)
    elif name == "diff":
        cached = arguments.get("cached", False)
        file_path = arguments.get("file")
        return await git_diff(cwd, cached, file_path)
    elif name == "add":
        files = arguments["files"]
        return await git_add(files, cwd)
    elif name == "commit":
        message = arguments["message"]
        amend = arguments.get("amend", False)
        return await git_commit(message, cwd, amend)
    elif name == "branch":
        action = arguments["action"]
        branch_name = arguments.get("name")
        return await git_branch(action, cwd, branch_name)
    elif name == "push":
        remote = arguments.get("remote", "origin")
        branch = arguments.get("branch")
        force = arguments.get("force", False)
        return await git_push(remote, branch, cwd, force)
    elif name == "pull":
        remote = arguments.get("remote", "origin") 
        branch = arguments.get("branch")
        return await git_pull(remote, branch, cwd)
    elif name == "log":
        limit = arguments.get("limit", 10)
        oneline = arguments.get("oneline", True)
        return await git_log(limit, oneline, cwd)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def run_git_command(args: List[str], cwd: str = ".") -> tuple[int, str, str]:
    """Run a git command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out after 30 seconds"
    except Exception as e:
        return -1, "", str(e)


async def git_status(cwd: str = ".") -> List[types.TextContent]:
    """Get git repository status."""
    code, stdout, stderr = await run_git_command(["status", "--porcelain", "-b"], cwd)
    
    if code != 0:
        return [types.TextContent(
            type="text",
            text=f"Error getting git status: {stderr}"
        )]
    
    if not stdout.strip():
        return [types.TextContent(
            type="text",
            text="Repository is clean - no changes to commit"
        )]
    
    # Parse status output
    lines = stdout.strip().split('\n')
    branch_line = lines[0] if lines and lines[0].startswith('##') else "## unknown"
    status_lines = [line for line in lines if not line.startswith('##')]
    
    result = f"Git Status:\n{branch_line}\n\n"
    
    if status_lines:
        result += "Changes:\n"
        for line in status_lines:
            status = line[:2]
            file_path = line[3:] if len(line) > 3 else ""
            
            status_desc = {
                "??": "Untracked",
                "A ": "Added", 
                "M ": "Modified",
                " M": "Modified (unstaged)",
                "D ": "Deleted",
                "R ": "Renamed",
                "C ": "Copied"
            }.get(status, status)
            
            result += f"  {status_desc:15} {file_path}\n"
    
    return [types.TextContent(type="text", text=result)]


async def git_diff(cwd: str = ".", cached: bool = False, file_path: Optional[str] = None) -> List[types.TextContent]:
    """Show git diff."""
    args = ["diff"]
    if cached:
        args.append("--cached")
    if file_path:
        args.append(file_path)
    
    code, stdout, stderr = await run_git_command(args, cwd)
    
    if code != 0:
        return [types.TextContent(
            type="text",
            text=f"Error getting git diff: {stderr}"
        )]
    
    if not stdout.strip():
        diff_type = "staged" if cached else "unstaged"
        target = f" for {file_path}" if file_path else ""
        return [types.TextContent(
            type="text",
            text=f"No {diff_type} changes{target}"
        )]
    
    return [types.TextContent(
        type="text",
        text=f"Git Diff {'(staged)' if cached else '(unstaged)'}:\n\n{stdout}"
    )]


async def git_add(files: List[str], cwd: str = ".") -> List[types.TextContent]:
    """Add files to git staging area."""
    args = ["add"] + files
    code, stdout, stderr = await run_git_command(args, cwd)
    
    if code != 0:
        return [types.TextContent(
            type="text",
            text=f"Error adding files: {stderr}"
        )]
    
    files_str = ", ".join(files)
    return [types.TextContent(
        type="text",
        text=f"Successfully added files: {files_str}"
    )]


async def git_commit(message: str, cwd: str = ".", amend: bool = False) -> List[types.TextContent]:
    """Create a git commit."""
    args = ["commit", "-m", message]
    if amend:
        args.append("--amend")
    
    code, stdout, stderr = await run_git_command(args, cwd)
    
    if code != 0:
        return [types.TextContent(
            type="text",
            text=f"Error creating commit: {stderr}"
        )]
    
    action = "amended" if amend else "created"
    return [types.TextContent(
        type="text",
        text=f"Successfully {action} commit:\n{stdout}"
    )]


async def git_branch(action: str, cwd: str = ".", branch_name: Optional[str] = None) -> List[types.TextContent]:
    """Handle branch operations."""
    
    if action == "list":
        code, stdout, stderr = await run_git_command(["branch", "-a"], cwd)
    elif action == "current":
        code, stdout, stderr = await run_git_command(["branch", "--show-current"], cwd)
    elif action == "create" and branch_name:
        code, stdout, stderr = await run_git_command(["checkout", "-b", branch_name], cwd)
    elif action == "checkout" and branch_name:
        code, stdout, stderr = await run_git_command(["checkout", branch_name], cwd)
    elif action == "delete" and branch_name:
        code, stdout, stderr = await run_git_command(["branch", "-d", branch_name], cwd)
    else:
        return [types.TextContent(
            type="text",
            text=f"Invalid branch action: {action} (requires branch name: {branch_name is None})"
        )]
    
    if code != 0:
        return [types.TextContent(
            type="text",
            text=f"Error with branch operation '{action}': {stderr}"
        )]
    
    return [types.TextContent(
        type="text",
        text=f"Branch {action}:\n{stdout}"
    )]


async def git_push(remote: str = "origin", branch: Optional[str] = None, cwd: str = ".", force: bool = False) -> List[types.TextContent]:
    """Push commits to remote repository."""
    args = ["push"]
    if force:
        args.append("--force")
    
    args.append(remote)
    if branch:
        args.append(branch)
    
    code, stdout, stderr = await run_git_command(args, cwd)
    
    if code != 0:
        return [types.TextContent(
            type="text",
            text=f"Error pushing to {remote}: {stderr}"
        )]
    
    return [types.TextContent(
        type="text",
        text=f"Successfully pushed to {remote}:\n{stdout}"
    )]


async def git_pull(remote: str = "origin", branch: Optional[str] = None, cwd: str = ".") -> List[types.TextContent]:
    """Pull changes from remote repository."""
    args = ["pull", remote]
    if branch:
        args.append(branch)
    
    code, stdout, stderr = await run_git_command(args, cwd)
    
    if code != 0:
        return [types.TextContent(
            type="text",
            text=f"Error pulling from {remote}: {stderr}"
        )]
    
    return [types.TextContent(
        type="text",
        text=f"Successfully pulled from {remote}:\n{stdout}"
    )]


async def git_log(limit: int = 10, oneline: bool = True, cwd: str = ".") -> List[types.TextContent]:
    """Show git commit history."""
    args = ["log", f"-{limit}"]
    if oneline:
        args.append("--oneline")
    
    code, stdout, stderr = await run_git_command(args, cwd)
    
    if code != 0:
        return [types.TextContent(
            type="text",
            text=f"Error getting git log: {stderr}"
        )]
    
    if not stdout.strip():
        return [types.TextContent(
            type="text",
            text="No commits found in repository"
        )]
    
    return [types.TextContent(
        type="text",
        text=f"Git Log (last {limit} commits):\n\n{stdout}"
    )]


async def main():
    """Run the git MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main()) 