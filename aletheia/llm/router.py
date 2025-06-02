"""LLM routing logic for hybrid local/external model usage."""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Union

from ..config import config
from ..identity import identity
from ..llm.providers import ExternalLLMManager
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
                consultation_metadata = None

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
                    consultation_metadata = None
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
                    
                    # Parse and filter response, also get consultation metadata
                    response, consultation_metadata = await self._filter_external_response(raw_response, task.prompt)
                    
                    # Enhance consultation metadata with provider information
                    model_info = external_llm.get_model_info()
                    
                    if consultation_metadata is None:
                        consultation_metadata = {}
                    
                    consultation_metadata.update({
                        "provider": external_llm.provider_type.value,
                        "model": model_info.get("model", "unknown_model"),
                        "external_llm_type": external_llm.__class__.__name__,
                        "context_size": model_info.get("capabilities", {}).get("max_context_size", 0),
                        "cost_info": model_info.get("costs", {}),
                    })
                    
                    route_used = "external"

            execution_time = asyncio.get_event_loop().time() - start_time

            result = {
                "result": response,
                "route_used": route_used,
                "execution_time": execution_time,
                "estimated_cost": 0,  # TODO: Calculate actual cost
            }
            
            # Add consultation metadata if available
            if consultation_metadata:
                result["consultation_metadata"] = consultation_metadata

            return result

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
        """Prepare a consultation request for external LLM."""
        
        # Build Aletheia's self-description for the consultation
        aletheia_intro = f"I am {identity.name}, {identity.personality.summary}."
        
        # Get key personality traits
        personality_traits = ", ".join(identity.personality.personality[:3]) if identity.personality.personality else "technically precise, analytical"
        
        # Detect language for response format
        is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in task.prompt.lower())
        response_language = "Russian" if is_russian else "English"
        
        # Build the consultation prompt with comprehensive context
        consultation_prompt = f"""{aletheia_intro}

My key traits: {personality_traits}

"""
        
        # Add comprehensive conversation context if available
        if task.conversation_context and task.conversation_context.strip():
            consultation_prompt += f"""CONVERSATION CONTEXT:
{task.conversation_context}

"""
        
        consultation_prompt += f"""Question I need expert consultation on: "{task.prompt}"

This question requires deeper knowledge than I currently have. Please provide a structured consultation response:

**1. TECHNICAL ANALYSIS** (for my knowledge base):
[Detailed explanation with scientific accuracy and relevant context]

**2. USER RESPONSE** (for me to provide to the user):
[Natural, conversational answer in {response_language} that maintains my personality and response style. 
IMPORTANT: Look at my previous responses in the conversation context above - match that same concise, direct style:
- Keep responses brief and focused (1-2 sentences for simple facts)
- Be technically precise but conversational like my other responses
- Avoid excessive detail unless the question specifically asks for it
- Match the length and tone of my previous local responses shown in the context]

**3. MEMORY POINTS** (key facts for my future reference):
[3-5 bullet points of essential information I should remember]

Please structure your response with exactly these three sections clearly marked."""

        return consultation_prompt

    def _get_external_system_prompt(self, task: TaskContext) -> str:
        """Get consultant system prompt for external LLM."""
        return """You are an expert AI consultant helping other AI agents provide better responses to their users.

When an AI agent requests consultation:
1. Provide accurate, detailed technical analysis
2. Suggest natural responses that match the agent's personality
3. Identify key information worth remembering

Your role is to be a knowledgeable consultant, not to impersonate the requesting agent. Structure your responses clearly and be precise with scientific and factual information."""

    async def _filter_external_response(self, external_response: str, original_prompt: str) -> tuple[str, dict]:
        """Parse structured consultation response and extract user response and consultation metadata."""
        
        try:
            # Try to parse structured response
            parsed_response = self._parse_consultation_response(external_response)
            
            if parsed_response:
                # Successfully parsed structured response
                user_response = parsed_response.get("user_response", "")
                technical_analysis = parsed_response.get("technical_analysis", "")
                memory_points = parsed_response.get("memory_points", [])
                
                print(f"📋 Consultation received: {len(technical_analysis)} chars analysis, {len(memory_points)} memory points")
                
                # Return the user response (this is what goes to the user)
                if user_response:
                    consultation_metadata = {
                        "technical_analysis": technical_analysis,
                        "memory_points": memory_points
                    }
                    return user_response.strip(), consultation_metadata
                else:
                    # Fallback: use technical analysis if no user response
                    consultation_metadata = {
                        "technical_analysis": technical_analysis,
                        "memory_points": memory_points
                    }
                    return technical_analysis.strip() if technical_analysis else external_response, consultation_metadata
            
            # If parsing failed, fall back to simple filtering
            print("⚠️  Structured parsing failed, using fallback filtering")
            return await self._fallback_filter_response(external_response, original_prompt)
            
        except Exception as e:
            print(f"Error parsing consultation response: {e}")
            return await self._fallback_filter_response(external_response, original_prompt)
    
    def _parse_consultation_response(self, response: str) -> dict:
        """Parse structured consultation response into components."""
        result = {
            "technical_analysis": "",
            "user_response": "",
            "memory_points": []
        }
        
        # Split response into sections based on markers
        sections = {
            "technical_analysis": ["**1. TECHNICAL ANALYSIS**", "**TECHNICAL ANALYSIS**", "1. TECHNICAL ANALYSIS"],
            "user_response": ["**2. USER RESPONSE**", "**USER RESPONSE**", "2. USER RESPONSE"],
            "memory_points": ["**3. MEMORY POINTS**", "**MEMORY POINTS**", "3. MEMORY POINTS"]
        }
        
        lines = response.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line_clean = line.strip()
            
            # Check if this line starts a new section
            section_found = None
            for section_name, markers in sections.items():
                if any(marker in line_clean for marker in markers):
                    section_found = section_name
                    break
            
            if section_found:
                # Save previous section content
                if current_section and current_content:
                    content = '\n'.join(current_content).strip()
                    if current_section == "memory_points":
                        # Parse bullet points
                        points = [point.strip('- •*').strip() for point in current_content if point.strip().startswith(('- ', '• ', '* '))]
                        result[current_section] = points
                    else:
                        result[current_section] = content
                
                # Start new section
                current_section = section_found
                current_content = []
            elif current_section:
                # Skip lines that are just section markers or brackets
                if not line_clean.startswith('[') or not line_clean.endswith(']'):
                    current_content.append(line)
        
        # Save final section
        if current_section and current_content:
            content = '\n'.join(current_content).strip()
            if current_section == "memory_points":
                points = [point.strip('- •*').strip() for point in current_content if point.strip().startswith(('- ', '• ', '* '))]
                result[current_section] = points
            else:
                result[current_section] = content
        
        return result if any(result.values()) else None
    
    async def _fallback_filter_response(self, external_response: str, original_prompt: str) -> tuple[str, dict]:
        """Fallback filtering for unstructured responses (original logic)."""
        
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
            consultation_metadata = {
                "filtered_response": filtered_response
            }
            return filtered_response, consultation_metadata
        except Exception as e:
            print(f"Error filtering response: {e}")
            # Fallback: return external response with identity disclaimer
            if is_russian:
                return f"[От {identity.name}] {external_response}", {}
            else:
                return f"[From {identity.name}] {external_response}", {}

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
