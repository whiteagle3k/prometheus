import abc
import json
import logging
import time
from abc import ABC
from typing import Any
import sys

from core.mcp.client.direct_mcp_client import DirectMCPClient

logger = logging.getLogger(__name__)


class BaseEntity(ABC):
    def __init__(self, entity_name: str, entity_id: str):
        self.entity_name = entity_name
        self.entity_id = entity_id

    def __str__(self):
        return f"{self.entity_name} ({self.entity_id})"

    async def process_input(self, user_input: str, user_id: str = "default", **kwargs) -> dict:
        """Process user input and return response."""
        start_time = time.time()
        
        # Process the input and get response
        result = await self._process_input(user_input, user_id, **kwargs)
        
        # Extract execution details
        details = result.get('execution_details', {})
        route = details.get('route_used', 'unknown').upper()
        exec_time = details.get('execution_time', 0)
        metadata = details.get('consultation_metadata', {})
        provider = metadata.get('provider', '')
        
        # Format route info
        route_str = f"{route}"
        if provider:
            route_str += f" ({provider})"
            
        # No debug output to console - we'll format the response elsewhere
        
        return result

    def _display_debug_summary(self, user_input: str, result: dict[str, Any], total_time: float) -> None:
        """Display comprehensive debug information about the thinking process."""
        execution_details = result.get("execution_details", {})
        route_used = execution_details.get("route_used", "unknown")
        approach = execution_details.get("approach", "unknown")
        fast_track = execution_details.get("fast_track", False)
        
        # Get provider info if available
        consultation_metadata = execution_details.get("consultation_metadata", {})
        provider = consultation_metadata.get("provider", "")
        
        # Format route info
        route_str = f"{route_used.upper()}"
        if provider:
            route_str += f" ({provider})"
            
        # Performance metrics
        execution_time = execution_details.get("execution_time", 0)
        
        # Print minimal summary - only uncomment for debug
        # print(f"\n🤖 {self.entity_name}: {result.get('response', '')}")
        # print(f"📊 Route: {route_str} | Time: {execution_time:.1f}s")

    async def _process_input(self, user_input: str, user_id: str = "default", **kwargs) -> dict:
        """Internal processing of user input."""
        start_time = time.time()
        
        try:
            llm_response_dict = await self._get_llm_response(user_input, user_id, **kwargs)
            end_time = time.time()
            llm_response_dict["execution_time"] = round(end_time - start_time, 1)
            return llm_response_dict
            
        except Exception as e:
            print(f"❌ Error processing input: {str(e)}")
            return {
                "response": "I encountered an error processing your request.",
                "execution_details": {
                    "route_used": "error",
                    "execution_time": time.time() - start_time,
                    "error": str(e)
                }
            }

    async def think(self, user_input: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Process user input and generate a response."""
        start_time = time.time()
        
        # 1. Handle MCP requests if input is a JSON string
        if user_input.strip().startswith("{") and '"jsonrpc"' in user_input:
            if not context:
                context = {}
            context["user_input"] = user_input
        
        # 3. Main processing
        llm_response_dict = await self._process_input(user_input, context)
        
        # NEW: Handle tool calls returned from the router
        if "tool_calls" in llm_response_dict and llm_response_dict["tool_calls"]:
            tool_call = llm_response_dict["tool_calls"][0] # Handle first tool call
            mcp_result = await self.mcp_client.execute_capability(
                tool_call["method"], 
                tool_call["params"]
            )
            llm_response_dict["result"] = f"Tool call executed: {mcp_result}"
            return llm_response_dict

        # 4. Cleanup and final response formatting
        llm_response_dict["result"] = self.cleanup_response(llm_response_dict.get("result", ""))
        
        end_time = time.time()
        llm_response_dict["execution_time"] = round(end_time - start_time, 1)
        
        # Extract execution details
        details = llm_response_dict.get('execution_details', {})
        route = details.get('route_used', 'unknown')
        exec_time = details.get('execution_time', 0)
        metadata = details.get('consultation_metadata', {})
        provider = metadata.get('provider', 'unknown')
        
        # Format execution summary for structured return
        route_info = f"Route: {route.upper()}"
        if provider != 'unknown':
            route_info += f" ({provider})"
        
        # Add execution info to the response dictionary
        llm_response_dict["route_info"] = route_info
        llm_response_dict["execution_time_formatted"] = f"{exec_time:.1f}s"
        
        return llm_response_dict