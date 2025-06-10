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
        print(f"[BaseEntity] llm_response_dict: {llm_response_dict}")
        
        # NEW: Handle tool calls returned from the router
        if "tool_calls" in llm_response_dict and llm_response_dict["tool_calls"]:
            tool_call = llm_response_dict["tool_calls"][0] # Handle first tool call
            print(f"[BaseEntity] Executing tool call: {tool_call}")
            mcp_result = await self.mcp_client.execute_capability(
                tool_call["method"], 
                tool_call["params"]
            )
            print(f"[BaseEntity] MCP result: {mcp_result}")
            llm_response_dict["result"] = f"Tool call executed: {mcp_result}"
            return llm_response_dict

        # 4. Cleanup and final response formatting
        llm_response_dict["result"] = self.cleanup_response(llm_response_dict.get("result", ""))
        
        end_time = time.time()
        llm_response_dict["execution_time"] = round(end_time - start_time, 1)
        return llm_response_dict 