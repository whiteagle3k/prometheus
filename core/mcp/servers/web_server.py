#!/usr/bin/env python3
"""
Web MCP Server

Provides web/internet access as MCP tools:
- Web search
- HTTP requests (GET, POST)
- Web scraping (basic)
- URL validation and parsing
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urljoin, quote
import httpx
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server


# Initialize the MCP server
app = Server("web")


@app.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available web tools."""
    return [
        types.Tool(
            name="search",
            description="Search the web using DuckDuckGo",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="http_get",
            description="Make HTTP GET request",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to request"
                    },
                    "headers": {
                        "type": "object",
                        "description": "HTTP headers",
                        "default": {}
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds",
                        "default": 10
                    }
                },
                "required": ["url"]
            }
        ),
        types.Tool(
            name="http_post",
            description="Make HTTP POST request",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to request"
                    },
                    "data": {
                        "type": "object",
                        "description": "POST data (JSON)"
                    },
                    "headers": {
                        "type": "object",
                        "description": "HTTP headers",
                        "default": {}
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds",
                        "default": 10
                    }
                },
                "required": ["url"]
            }
        ),
        types.Tool(
            name="scrape_text",
            description="Extract text content from a web page",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to scrape"
                    },
                    "selector": {
                        "type": "string",
                        "description": "CSS selector to target specific elements"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds",
                        "default": 10
                    }
                },
                "required": ["url"]
            }
        ),
        types.Tool(
            name="validate_url",
            description="Validate and parse URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to validate"
                    }
                },
                "required": ["url"]
            }
        ),
        types.Tool(
            name="check_status",
            description="Check HTTP status of URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to check"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds",
                        "default": 5
                    }
                },
                "required": ["url"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls."""
    
    if name == "search":
        query = arguments["query"]
        max_results = arguments.get("max_results", 5)
        return await web_search(query, max_results)
    elif name == "http_get":
        url = arguments["url"]
        headers = arguments.get("headers", {})
        timeout = arguments.get("timeout", 10)
        return await http_get(url, headers, timeout)
    elif name == "http_post":
        url = arguments["url"]
        data = arguments.get("data")
        headers = arguments.get("headers", {})
        timeout = arguments.get("timeout", 10)
        return await http_post(url, data, headers, timeout)
    elif name == "scrape_text":
        url = arguments["url"]
        selector = arguments.get("selector")
        timeout = arguments.get("timeout", 10)
        return await scrape_text(url, selector, timeout)
    elif name == "validate_url":
        url = arguments["url"]
        return await validate_url(url)
    elif name == "check_status":
        url = arguments["url"]
        timeout = arguments.get("timeout", 5)
        return await check_status(url, timeout)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def web_search(query: str, max_results: int = 5) -> List[types.TextContent]:
    """Search the web using DuckDuckGo instant answer API."""
    try:
        # Use DuckDuckGo instant answer API
        search_url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "pretty": "1",
            "no_redirect": "1"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(search_url, params=params, timeout=10)
            
            if response.status_code != 200:
                return [types.TextContent(
                    type="text",
                    text=f"Search failed with status {response.status_code}"
                )]
            
            data = response.json()
            
            # Format results
            results = []
            
            # Abstract answer
            if data.get("Abstract"):
                results.append(f"**Summary:** {data['Abstract']}")
                if data.get("AbstractURL"):
                    results.append(f"Source: {data['AbstractURL']}")
            
            # Related topics
            if data.get("RelatedTopics"):
                results.append("\n**Related Topics:**")
                for i, topic in enumerate(data["RelatedTopics"][:max_results]):
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append(f"{i+1}. {topic['Text']}")
                        if topic.get("FirstURL"):
                            results.append(f"   Link: {topic['FirstURL']}")
            
            # Answer (for calculations, definitions, etc.)
            if data.get("Answer"):
                results.append(f"\n**Direct Answer:** {data['Answer']}")
            
            # Definition
            if data.get("Definition"):
                results.append(f"\n**Definition:** {data['Definition']}")
                if data.get("DefinitionURL"):
                    results.append(f"Source: {data['DefinitionURL']}")
            
            if not results:
                results.append("No search results found. Try a different query.")
            
            return [types.TextContent(
                type="text",
                text=f"Search Results for '{query}':\n\n" + "\n".join(results)
            )]
    
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Search error: {str(e)}"
        )]


async def http_get(url: str, headers: Dict[str, str] = None, timeout: int = 10) -> List[types.TextContent]:
    """Make HTTP GET request."""
    try:
        if not validate_url_format(url):
            return [types.TextContent(
                type="text",
                text=f"Invalid URL format: {url}"
            )]
        
        request_headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MCP-Web-Server/1.0)"
        }
        if headers:
            request_headers.update(headers)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=request_headers, timeout=timeout)
            
            # Format response
            result_parts = [
                f"HTTP GET: {url}",
                f"Status: {response.status_code} {response.reason_phrase}",
                f"Content-Type: {response.headers.get('content-type', 'unknown')}"
            ]
            
            # Include response body (truncated if too long)
            content = response.text
            if len(content) > 2000:
                content = content[:2000] + "\n... (truncated)"
            
            result_parts.append(f"Response Body:\n{content}")
            
            return [types.TextContent(
                type="text",
                text="\n\n".join(result_parts)
            )]
    
    except httpx.TimeoutException:
        return [types.TextContent(
            type="text",
            text=f"Request to {url} timed out after {timeout} seconds"
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"HTTP GET error for {url}: {str(e)}"
        )]


async def http_post(url: str, data: Any = None, headers: Dict[str, str] = None, timeout: int = 10) -> List[types.TextContent]:
    """Make HTTP POST request."""
    try:
        if not validate_url_format(url):
            return [types.TextContent(
                type="text",
                text=f"Invalid URL format: {url}"
            )]
        
        request_headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MCP-Web-Server/1.0)",
            "Content-Type": "application/json"
        }
        if headers:
            request_headers.update(headers)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                json=data if data else {},
                headers=request_headers, 
                timeout=timeout
            )
            
            # Format response
            result_parts = [
                f"HTTP POST: {url}",
                f"Status: {response.status_code} {response.reason_phrase}",
                f"Content-Type: {response.headers.get('content-type', 'unknown')}"
            ]
            
            if data:
                result_parts.append(f"Request Data: {json.dumps(data, indent=2)}")
            
            # Include response body (truncated if too long)
            content = response.text
            if len(content) > 2000:
                content = content[:2000] + "\n... (truncated)"
            
            result_parts.append(f"Response Body:\n{content}")
            
            return [types.TextContent(
                type="text",
                text="\n\n".join(result_parts)
            )]
    
    except httpx.TimeoutException:
        return [types.TextContent(
            type="text",
            text=f"Request to {url} timed out after {timeout} seconds"
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"HTTP POST error for {url}: {str(e)}"
        )]


async def scrape_text(url: str, selector: Optional[str] = None, timeout: int = 10) -> List[types.TextContent]:
    """Extract text content from web page (basic HTML parsing)."""
    try:
        if not validate_url_format(url):
            return [types.TextContent(
                type="text",
                text=f"Invalid URL format: {url}"
            )]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MCP-Web-Server/1.0)"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=timeout)
            
            if response.status_code != 200:
                return [types.TextContent(
                    type="text",
                    text=f"Failed to fetch {url}: {response.status_code}"
                )]
            
            html_content = response.text
            
            # Basic text extraction (remove HTML tags)
            # This is a simple implementation - for production use a proper HTML parser
            text_content = extract_text_from_html(html_content)
            
            # Truncate if too long
            if len(text_content) > 3000:
                text_content = text_content[:3000] + "\n... (truncated)"
            
            return [types.TextContent(
                type="text",
                text=f"Text content from {url}:\n\n{text_content}"
            )]
    
    except httpx.TimeoutException:
        return [types.TextContent(
            type="text",
            text=f"Request to {url} timed out after {timeout} seconds"
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Scraping error for {url}: {str(e)}"
        )]


def extract_text_from_html(html: str) -> str:
    """Basic HTML text extraction."""
    # Remove script and style elements
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


async def validate_url(url: str) -> List[types.TextContent]:
    """Validate and parse URL."""
    try:
        parsed = urlparse(url)
        
        is_valid = bool(parsed.scheme and parsed.netloc)
        
        result_parts = [
            f"URL: {url}",
            f"Valid: {is_valid}"
        ]
        
        if is_valid:
            result_parts.extend([
                f"Scheme: {parsed.scheme}",
                f"Domain: {parsed.netloc}",
                f"Path: {parsed.path}",
                f"Query: {parsed.query}",
                f"Fragment: {parsed.fragment}"
            ])
        else:
            result_parts.append("Error: URL must include scheme (http/https) and domain")
        
        return [types.TextContent(
            type="text",
            text="\n".join(result_parts)
        )]
    
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"URL validation error: {str(e)}"
        )]


def validate_url_format(url: str) -> bool:
    """Quick URL format validation."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except:
        return False


async def check_status(url: str, timeout: int = 5) -> List[types.TextContent]:
    """Check HTTP status of URL."""
    try:
        if not validate_url_format(url):
            return [types.TextContent(
                type="text",
                text=f"Invalid URL format: {url}"
            )]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MCP-Web-Server/1.0)"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.head(url, headers=headers, timeout=timeout, follow_redirects=True)
            
            return [types.TextContent(
                type="text",
                text=f"Status check for {url}:\nHTTP {response.status_code} {response.reason_phrase}"
            )]
    
    except httpx.TimeoutException:
        return [types.TextContent(
            type="text",
            text=f"Request to {url} timed out after {timeout} seconds"
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Status check error for {url}: {str(e)}"
        )]


async def main():
    """Run the web MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main()) 