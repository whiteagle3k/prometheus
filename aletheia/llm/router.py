"""LLM routing logic for hybrid local/external model usage."""

import asyncio
from typing import Dict, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass

from .local_llm import LocalLLM  
from .external_llm import ExternalLLM, ExternalLLMManager
from ..config import config


class RouteDecision(Enum):
    """Routing decision options."""
    LOCAL = "local"
    EXTERNAL = "external"


@dataclass
class TaskContext:
    """Context for routing decisions."""
    prompt: str
    max_tokens: int = 512
    requires_deep_reasoning: bool = False
    is_creative: bool = False
    needs_latest_knowledge: bool = False
    cost_sensitive: bool = True
    latency_sensitive: bool = False


class LLMRouter:
    """Router for deciding between local and external LLMs."""

    def __init__(self) -> None:
        """Initialize the router."""
        self.local_llm = LocalLLM()
        self.external_manager = ExternalLLMManager()
        self._routing_stats: Dict[str, int] = {
            "local_routes": 0,
            "external_routes": 0,
            "routing_errors": 0,
        }

    async def route_task(self, task: TaskContext) -> RouteDecision:
        """Make routing decision for a task."""
        try:
            # Check if local model is available
            local_available = await self.local_llm.is_available()
            external_available = await self.external_manager.get_best_available() is not None

            # If only one option available, use it
            if not external_available:
                if local_available:
                    self._routing_stats["local_routes"] += 1
                    return RouteDecision.LOCAL
                else:
                    raise RuntimeError("No LLMs available")

            if not local_available:
                self._routing_stats["external_routes"] += 1
                return RouteDecision.EXTERNAL

            # Both available - apply routing heuristics
            decision = await self._apply_routing_heuristics(task)
            
            if decision == RouteDecision.LOCAL:
                self._routing_stats["local_routes"] += 1
            else:
                self._routing_stats["external_routes"] += 1
                
            return decision

        except Exception as e:
            self._routing_stats["routing_errors"] += 1
            print(f"Routing error: {e}")
            # Fallback to local if available
            if await self.local_llm.is_available():
                return RouteDecision.LOCAL
            else:
                return RouteDecision.EXTERNAL

    async def _apply_routing_heuristics(self, task: TaskContext) -> RouteDecision:
        """Apply routing heuristics to make decision."""
        
        # Estimate token count
        estimated_tokens = await self.local_llm.count_tokens(task.prompt)
        total_estimated_tokens = estimated_tokens + task.max_tokens

        # Rule 1: Token threshold check
        if estimated_tokens > config.local_token_threshold:
            return RouteDecision.EXTERNAL

        # Rule 2: Deep reasoning keyword check
        prompt_lower = task.prompt.lower()
        if any(keyword in prompt_lower for keyword in config.deep_reasoning_keywords):
            task.requires_deep_reasoning = True

        # Rule 3: Explicit deep reasoning requirement
        if task.requires_deep_reasoning:
            return RouteDecision.EXTERNAL

        # Rule 4: Latest knowledge requirement
        if task.needs_latest_knowledge:
            return RouteDecision.EXTERNAL

        # Rule 5: Creative tasks with high token requirements
        if task.is_creative and total_estimated_tokens > 2000:
            return RouteDecision.EXTERNAL

        # Rule 6: Cost vs latency tradeoff
        if task.latency_sensitive and not task.cost_sensitive:
            return RouteDecision.LOCAL

        # Rule 7: Very long outputs
        if task.max_tokens > 1500:
            return RouteDecision.EXTERNAL

        # Rule 8: Context size check
        local_context = self.local_llm.get_context_size()
        if total_estimated_tokens > local_context * 0.8:  # 80% threshold
            return RouteDecision.EXTERNAL

        # Default: use local for efficiency
        return RouteDecision.LOCAL

    async def get_llm_for_task(
        self, 
        task: TaskContext,
        force_route: Optional[RouteDecision] = None,
    ) -> Union[LocalLLM, ExternalLLM]:
        """Get the appropriate LLM instance for a task."""
        
        route = force_route or await self.route_task(task)
        
        if route == RouteDecision.LOCAL:
            return self.local_llm
        else:
            external_llm = await self.external_manager.get_best_available()
            if not external_llm:
                print("⚠️  No external LLM available, falling back to local")
                return self.local_llm
            return external_llm

    async def execute_task(
        self,
        task: TaskContext,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute a task with automatic routing."""
        
        start_time = asyncio.get_event_loop().time()
        
        # Get routing decision
        route = await self.route_task(task)
        llm = await self.get_llm_for_task(task, force_route=route)
        
        # Execute the task
        try:
            result = await llm.generate(
                prompt=task.prompt,
                max_tokens=task.max_tokens,
                system_prompt=system_prompt,
                **kwargs,
            )
            
            # Handle empty or None results
            if not result or result.strip() == "":
                result = "I apologize, but I wasn't able to generate a proper response. Please try rephrasing your question."
            
            end_time = asyncio.get_event_loop().time()
            
            # Estimate cost for external LLMs
            cost_estimate = 0.0
            if route == RouteDecision.EXTERNAL and isinstance(llm, ExternalLLM):
                input_tokens = await llm.count_tokens(task.prompt)
                output_tokens = await llm.count_tokens(result)
                cost_estimate = llm.estimate_cost(input_tokens, output_tokens)
            
            return {
                "result": result,
                "route_used": route.value,
                "model_info": llm.get_model_info() if hasattr(llm, 'get_model_info') else {},
                "execution_time": end_time - start_time,
                "estimated_cost": cost_estimate,
                "task_context": {
                    "prompt_length": len(task.prompt),
                    "max_tokens": task.max_tokens,
                    "requires_deep_reasoning": task.requires_deep_reasoning,
                },
            }
            
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            return {
                "result": f"Error generating response: {str(e)}",
                "error": str(e),
                "route_used": route.value,
                "execution_time": end_time - start_time,
                "estimated_cost": 0.0,
            }

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        total_routes = (
            self._routing_stats["local_routes"] + 
            self._routing_stats["external_routes"]
        )
        
        if total_routes == 0:
            return {**self._routing_stats, "local_percentage": 0, "external_percentage": 0}
        
        return {
            **self._routing_stats,
            "total_routes": total_routes,
            "local_percentage": (self._routing_stats["local_routes"] / total_routes) * 100,
            "external_percentage": (self._routing_stats["external_routes"] / total_routes) * 100,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check health of local and external LLMs."""
        local_available = await self.local_llm.is_available()
        external_available = await self.external_manager.get_best_available() is not None
        
        # Get available providers without triggering async calls
        available_providers = self.external_manager.list_available_providers()
        
        return {
            "local_llm_available": local_available,
            "external_llm_available": external_available,
            "available_external_providers": [p.value for p in available_providers],
            "routing_stats": self.get_routing_stats(),
        } 