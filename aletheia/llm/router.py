"""LLM routing logic for hybrid local/external model usage."""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Union

from ..config import config
from ..identity import identity
from .external_llm import ExternalLLM, ExternalLLMManager
from .local_llm import LocalLLM


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
    # New context fields
    conversation_context: Optional[str] = None
    user_name: Optional[str] = None
    session_context: Optional[dict] = None


class LLMRouter:
    """Router for deciding between local and external LLMs."""

    def __init__(self) -> None:
        """Initialize the router."""
        self.local_llm = LocalLLM()
        self.external_manager = ExternalLLMManager()
        self._routing_stats: dict[str, int] = {
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
        """Apply routing heuristics to make decision using identity configuration."""

        # Estimate token count
        estimated_tokens = await self.local_llm.count_tokens(task.prompt)
        total_estimated_tokens = estimated_tokens + task.max_tokens

        # Rule 1: Token threshold check - use identity configuration
        routing_threshold = identity.get_routing_threshold()
        if estimated_tokens > routing_threshold:
            return RouteDecision.EXTERNAL

        # Rule 2: Deep reasoning keyword check
        prompt_lower = task.prompt.lower()
        if any(keyword in prompt_lower for keyword in config.deep_reasoning_keywords):
            task.requires_deep_reasoning = True

        # Rule 3: Explicit deep reasoning requirement - use identity configuration
        if task.requires_deep_reasoning and identity.should_require_deep_reasoning():
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

        # Default: use local for efficiency (aligned with identity's cost optimization goal)
        return RouteDecision.LOCAL

    async def execute_task(self, task: TaskContext) -> dict[str, Any]:
        """Execute a task using the appropriate LLM."""
        start_time = asyncio.get_event_loop().time()

        try:
            # Make routing decision
            route = await self.route_task(task)

            if route == RouteDecision.LOCAL:
                # Execute locally
                response = await self.local_llm.generate(
                    prompt=task.prompt,
                    max_tokens=task.max_tokens,
                    temperature=0.7,
                )
                route_used = "local"

            else:
                # Execute externally  
                external_llm = await self.external_manager.get_best_available()
                if not external_llm:
                    # Fallback to local
                    response = await self.local_llm.generate(
                        prompt=task.prompt,
                        max_tokens=task.max_tokens,
                        temperature=0.7,
                    )
                    route_used = "local_fallback"
                else:
                    # Enhance prompt with context for external LLM
                    enhanced_prompt = await self._prepare_external_prompt(task)
                    
                    # Use external LLM with enhanced context
                    raw_response = await external_llm.generate(
                        prompt=enhanced_prompt,
                        max_tokens=task.max_tokens,
                        temperature=0.7,
                        system_prompt=self._get_external_system_prompt(task)
                    )
                    response = await self._filter_external_response(raw_response, task.prompt)
                    route_used = "external"

            execution_time = asyncio.get_event_loop().time() - start_time

            return {
                "result": response,
                "route_used": route_used,
                "execution_time": execution_time,
                "estimated_cost": 0,  # TODO: Calculate actual cost
            }

        except Exception as e:
            print(f"Task execution error: {e}")
            # Fallback to local if available
            try:
                response = await self.local_llm.generate(
                    prompt=task.prompt,
                    max_tokens=task.max_tokens,
                    temperature=0.7,
                )
                execution_time = asyncio.get_event_loop().time() - start_time
                return {
                    "result": response,
                    "route_used": "local_fallback",
                    "execution_time": execution_time,
                    "estimated_cost": 0,
                    "error": str(e),
                }
            except Exception as fallback_error:
                return {
                    "result": "Извините, произошла ошибка при обработке запроса. / Sorry, an error occurred processing your request.",
                    "route_used": "error",
                    "execution_time": 0,
                    "estimated_cost": 0,
                    "error": f"Primary: {e}, Fallback: {fallback_error}",
                }

    async def _prepare_external_prompt(self, task: TaskContext) -> str:
        """Prepare an enhanced prompt for external LLM with context."""
        enhanced_prompt = task.prompt
        
        # Add conversation context if available
        if task.conversation_context:
            # Create a brief summary of context for external LLM
            context_summary = await self._summarize_context(task.conversation_context)
            enhanced_prompt = f"""Conversation context: {context_summary}

Current question: {task.prompt}"""
        
        # Add user personalization if available
        if task.user_name:
            enhanced_prompt = f"""User: {task.user_name}

{enhanced_prompt}"""
        
        return enhanced_prompt

    def _get_external_system_prompt(self, task: TaskContext) -> str:
        """Get appropriate system prompt for external LLM from identity configuration."""
        # Detect language
        is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in task.prompt.lower())
        
        # Use identity system to get external system prompt
        language = "ru" if is_russian else "en"
        return identity.get_external_system_prompt(language)

    async def _summarize_context(self, context: str) -> str:
        """Create a brief summary of conversation context for external LLM."""
        # For now, use a simple truncation with key information extraction
        # In the future, this could use a summarization model
        
        if len(context) <= 300:
            return context
        
        # Extract key information patterns
        lines = context.split('\n')
        important_lines = []
        
        for line in lines:
            line = line.strip()
            # Keep lines with key information
            if any(keyword in line.lower() for keyword in [
                'user:', 'пользователь:', 'name', 'имя', 'topic', 'тема', 
                'question', 'вопрос', 'task', 'задача', 'problem', 'проблема'
            ]):
                important_lines.append(line)
        
        # If we have important lines, use them; otherwise truncate
        if important_lines:
            summary = '\n'.join(important_lines[:5])  # Top 5 important lines
            if len(summary) > 300:
                summary = summary[:300] + "..."
            return summary
        else:
            return context[:300] + "..."

    async def _filter_external_response(self, external_response: str, original_prompt: str) -> str:
        """Filter external LLM response through identity personality and maintain language consistency."""
        
        # Detect language of original prompt
        is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in original_prompt.lower())
        
        # Create a personality filter prompt using English core identity for better model understanding
        core_traits = ', '.join(identity.personality.personality[:3])
        core_values = ', '.join(identity.core_values[:2])
        
        if is_russian:
            filter_prompt = f"""Original user question: {original_prompt}

External system response: {external_response}

Reframe this response as {identity.name} - {identity.personality.summary}. Important personality traits: {core_traits}. Core principles: {core_values}.

Requirements:
1. Maintain my personality and traits listed above
2. Keep all useful information from the response
3. Make the response natural according to my character
4. Don't mention ChatGPT or other systems - you are {identity.name}
5. Respond in Russian with natural grammar and cultural context
6. Follow my core principles

Response in Russian:"""
        else:
            filter_prompt = f"""Original user question: {original_prompt}

External system response: {external_response}

Reframe this response as {identity.name} - {identity.personality.summary}. Important personality traits: {core_traits}. Core principles: {core_values}.

Requirements:
1. Maintain my personality and traits listed above
2. Keep all useful information from the response
3. Make the response natural according to my character
4. Don't mention ChatGPT or other systems - you are {identity.name}
5. Respond in English
6. Follow my core principles

Response:"""

        try:
            # Use local LLM to filter the response with identity personality
            filtered_response = await self.local_llm.generate(
                prompt=filter_prompt,
                max_tokens=min(800, len(external_response) + 200),
                temperature=0.3,  # Lower temperature for consistent personality
            )
            return filtered_response
        except Exception as e:
            print(f"Error filtering response: {e}")
            # Fallback: return external response with identity disclaimer
            if is_russian:
                return f"[От {identity.name}] {external_response}"
            else:
                return f"[From {identity.name}] {external_response}"

    def get_routing_stats(self) -> dict[str, Any]:
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

    async def health_check(self) -> dict[str, Any]:
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
