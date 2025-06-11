"""LLM routing logic for hybrid local/external model usage."""

import asyncio
import csv
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
import time

from core.config import config

# TODO: Remove direct identity import - should be passed from entity
# from ..identity import identity
from core.llm.providers import ExternalLLMManager
from core.llm.providers.base import GenerationRequest

from .confidence_calibrator import calibrator
from .fast_llm import FastLLM
from .local_llm import LocalLLM

# Create logs directory if it doesn't exist
LOGS_DIR = Path("data/logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
ROUTER_LOG_FILE = LOGS_DIR / "router.csv"

class RouteDecision(Enum):
    """Routing decision options."""
    LOCAL = "local"
    EXTERNAL = "external"
    FAST = "fast"  # For fast classification tasks


@dataclass
class TaskContext:
    """Context for routing decisions."""
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.7
    tools: list[dict[str, Any]] | None = None  # Add tools here
    requires_deep_reasoning: bool = False
    is_creative: bool = False
    needs_latest_knowledge: bool = False
    cost_sensitive: bool = True
    latency_sensitive: bool = False
    # New context fields
    conversation_context: str | None = None
    user_name: str | None = None
    session_context: dict | None = None
    memory_retriever: callable = None


class LLMRouter:
    """Router for deciding between local and external LLMs."""

    def __init__(self, identity_config: dict | None = None) -> None:
        """Initialize the router."""
        # TODO: Properly inject identity configuration from entity
        self.identity_config = identity_config or {
            "name": "AI Assistant",
            "personality": {
                "summary": "A helpful AI assistant",
                "personality": ["helpful", "analytical", "precise"]
            },
            "core_values": ["accuracy", "helpfulness"],
            "routing_threshold": 1000,
            "require_deep_reasoning": True,
            "system_prompts": {
                "en": "You are a helpful AI assistant.",
                "ru": "Вы полезный ИИ-помощник."
            },
            "llm_instructions": "You are a helpful AI assistant."
        }

        self.local_llm = None
        # Only initialize local LLM if it's not explicitly disabled
        operational_guidelines = self.identity_config.get("operational_guidelines", {})
        if operational_guidelines.get("enable_local_llm", True):
            self.local_llm = LocalLLM(identity_config=self.identity_config)

        self.utility_llm = FastLLM(identity_config=self.identity_config)  # Pass identity config
        self.external_manager = ExternalLLMManager(providers_config=self.identity_config.get("external_llms"))
        self.use_calibrator = True  # Enable calibrated routing

        self._routing_stats: dict[str, int] = {
            "local_routes": 0,
            "external_routes": 0,
            "routing_errors": 0,
            "calibrator_predictions": 0,
            "fallback_threshold_used": 0,
        }

        # Initialize CSV logging
        self._init_router_logging()

    def _init_router_logging(self):
        """Initialize CSV logging for routing decisions."""
        try:
            if not ROUTER_LOG_FILE.exists():
                with open(ROUTER_LOG_FILE, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "timestamp", "query", "route_decision", "oracle_confidence",
                        "oracle_reasoning", "complexity", "execution_time",
                        "actual_route_used", "success", "error_details"
                    ])
        except Exception as e:
            print(f"⚠️ Could not initialize router logging: {e}")

    def _log_routing_decision(self, query: str, route_decision: str, oracle_result: dict,
                            execution_time: float, actual_route: str, success: bool,
                            error_details: str = ""):
        """Log routing decision to CSV for analysis."""
        try:
            with open(ROUTER_LOG_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    query[:100],  # Truncate query for readability
                    route_decision,
                    oracle_result.get("confidence", "unknown"),
                    oracle_result.get("reasoning", "unknown"),
                    oracle_result.get("complexity", "unknown"),
                    f"{execution_time:.3f}",
                    actual_route,
                    success,
                    error_details
                ])
        except Exception as e:
            print(f"⚠️ Could not log routing decision: {e}")

    async def route_task(self, task: TaskContext) -> RouteDecision:
        """Make routing decision for a task."""
        try:
            # Check if local model is available
            local_available = self.local_llm and await self.local_llm.is_available()
            
            # Only check external availability if we might actually need it
            # This avoids unnecessary health check API calls during LOCAL routing
            external_available = False
            if not local_available:
                # Only do expensive health checks if local is not available
                external_available = await self.external_manager.get_best_available() is not None
            else:
                # Quick check without health calls - just see if any providers are configured
                external_available = len(self.external_manager.list_available_providers()) > 0

            # If only one option available, use it
            if not external_available:
                if local_available:
                    self._routing_stats["local_routes"] += 1
                    return RouteDecision.LOCAL
                else:
                    msg = "No LLMs available"
                    raise RuntimeError(msg)

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
            if self.local_llm and await self.local_llm.is_available():
                return RouteDecision.LOCAL
            else:
                return RouteDecision.EXTERNAL

    async def _apply_routing_heuristics(self, task: TaskContext) -> RouteDecision:
        """Apply routing heuristics to make decision using fast LLM routing oracle."""
        start_time = time.time()
        route_used = "unknown"  # Ensure this is always defined for error handling
        
        # Rule 0: Check if external LLM is preferred in identity config
        # Try multiple possible config locations for routing preferences
        
        # Location 1: operational_guidelines.routing_policy (current agent configs)
        operational_guidelines = self.identity_config.get("operational_guidelines", {})
        routing_policy = operational_guidelines.get("routing_policy", {})
        prefer_external = routing_policy.get("prefer_external", False)
        use_for_coding = routing_policy.get("use_for_coding", False) or routing_policy.get("use_for_analysis", False)
        
        # Location 1b: also check thresholds substructure (Vasya's config structure)
        if not prefer_external:
            thresholds = routing_policy.get("thresholds", {})
            prefer_external = thresholds.get("prefer_external", False)
            use_for_coding = thresholds.get("use_for_coding", False) or thresholds.get("use_for_implementation", False)
        
        # Location 2: external_llms.routing_preferences (alternative location) 
        if not prefer_external:
            external_prefs = self.identity_config.get("external_llms", {}).get("routing_preferences", {})
            prefer_external = external_prefs.get("prefer_external", False)
            use_for_coding = external_prefs.get("use_for_coding", False)
        
        # If external is preferred and available, use it
        if prefer_external:
            print(f"🎯 External LLM preferred in config (prefer_external: {prefer_external})")
            return RouteDecision.EXTERNAL
            
        # Check for coding tasks if configured
        if use_for_coding and self._is_coding_task(task.prompt):
            print("🎯 Coding task detected, using external LLM as configured")
            return RouteDecision.EXTERNAL

        # Rule 1: Basic sanity checks first
        if self.local_llm:
            estimated_tokens = await self.local_llm.count_tokens(task.prompt)
            total_estimated_tokens = estimated_tokens + task.max_tokens

            # Rule 1a: Token threshold check - use from identity config or default
            routing_threshold = self.identity_config.get("routing_threshold", 1000)
            if estimated_tokens > routing_threshold:
                print(f"🎯 Token threshold exceeded ({estimated_tokens} > {routing_threshold})")
                return RouteDecision.EXTERNAL

            # Rule 1b: Very long outputs
            if task.max_tokens > 1500:
                print(f"🎯 Large output requested ({task.max_tokens} tokens)")
                return RouteDecision.EXTERNAL

            # Rule 1c: Context size check
            local_context = self.local_llm.get_context_size()
            if total_estimated_tokens > local_context * 0.8:  # 80% threshold
                print(f"🎯 Context limit approaching ({total_estimated_tokens} / {local_context})")
                return RouteDecision.EXTERNAL
        else:
            # If no local llm, all checks that would route to external are effectively true
            print("➡️ No local LLM, routing to external.")
            return RouteDecision.EXTERNAL

        # Rule 1d: Explicit requirements
        if task.needs_latest_knowledge:
            print("🎯 Latest knowledge required")
            return RouteDecision.EXTERNAL

        if task.is_creative and total_estimated_tokens > 2000:
            print("🎯 Creative task with large output")
            return RouteDecision.EXTERNAL

        if task.latency_sensitive and not task.cost_sensitive:
            print("🎯 Latency-sensitive task")
            return RouteDecision.LOCAL

        # Rule 2: Fast LLM Routing Oracle (NEW!)
        # This replaces the old self-assessment logic with unbiased routing
        print("🔧 Fast LLM: Making routing decision...")
        try:
            # Build assessment context for the oracle
            oracle_result = await self.utility_llm.decide_routing(task)

            # Rule 2b: Use calibrator for confidence-based routing
            if self.use_calibrator and self.local_llm:
                self._routing_stats["calibrator_predictions"] += 1
                should_use_local, _ = calibrator.predict_should_use_local(
                    entropy=oracle_result.get("entropy", 0.5), # Assuming FastLLM provides entropy
                    query=task.prompt,
                    local_confidence=oracle_result.get("confidence", "low")
                )
                if not should_use_local:
                    print("🎯 Calibrator recommends external route")
                    return RouteDecision.EXTERNAL

            # Rule 2c: Fallback based on complexity
            complexity = oracle_result.get("complexity", 5)
            # Ensure complexity is treated as a number
            if isinstance(complexity, str):
                try:
                    complexity = int(complexity)
                except ValueError:
                    complexity = 5  # Default if conversion fails
            
            if complexity > 7:
                print(f"🎯 High complexity ({complexity}/10), routing to external")
                return RouteDecision.EXTERNAL

        except Exception as e:
            execution_time = time.time() - start_time
            # Log the error for debugging
            print(f"⚠️ Error in routing decision: {e}")
            
            # Log error but return a valid RouteDecision enum
            self._log_routing_decision(
                query=task.prompt,
                route_decision="error",
                oracle_result={"error": str(e)},
                execution_time=execution_time,
                actual_route="external", # Default to external on error
                success=False,
                error_details=str(e)
            )
            
            # Return a fallback decision (preferring EXTERNAL for safety)
            return RouteDecision.EXTERNAL

        # Default to local if no other rule applies
        return RouteDecision.LOCAL

    def _is_coding_task(self, prompt: str) -> bool:
        """Check if the prompt is a coding-related task."""
        # Simple keyword-based check for now
        coding_keywords = ["code", "python", "javascript", "typescript", "java", "c++", "rust", "golang", "php", "html", "css", "sql", "docker", "kubernetes", "terraform"]
        return any(keyword in prompt.lower() for keyword in coding_keywords)

    async def execute_task(self, task: "TaskContext") -> dict[str, Any]:
        """
        Execute a task using the appropriate LLM, with robust error handling.
        This method is rewritten to be simple and correct.
        """
        start_time = time.time()
        route_used = "unknown"
        
        try:
            # 1. Get routing decision
            route = await self.route_task(task)
            route_used = route.value
            print(f"🎯 Router: {route.name} LLM selected")

            response = ""
            consultation_metadata = {}

            # 2. Execute based on route
            if route == RouteDecision.LOCAL:
                if not self.local_llm:
                    raise RuntimeError("Local LLM not available")

                # Retrieve memories if retriever is provided
                memories = await task.memory_retriever() if task.memory_retriever else []
                local_context = self._build_local_context(task.prompt, memories)

                # Generate response
                structured_result = await self.local_llm.generate_structured(
                    prompt=task.prompt,
                    max_tokens=task.max_tokens,
                    temperature=0.7,
                    context=local_context
                )
                response = structured_result.get("answer", "")

            elif route == RouteDecision.EXTERNAL:
                # Get the provider name
                provider_name = self._get_preferred_provider(task)
                if not provider_name:
                    raise RuntimeError("No external provider available")

                # Get the actual provider instance
                provider_instance = await self.external_manager.get_provider_by_name(provider_name)
                if not provider_instance:
                    raise RuntimeError(f"Provider {provider_name} not available")

                # Prepare external prompt that includes conversation context
                prepared_prompt = await self._prepare_external_prompt(task)
                
                # Use the provider instance to generate a response
                external_response = await provider_instance.generate(
                    prompt=prepared_prompt,
                    max_tokens=task.max_tokens,
                    temperature=task.temperature,
                    system_prompt=self._get_external_system_prompt(task)
                )
                
                # Filter and get metadata
                response, consultation_metadata = await self._filter_external_response(
                    external_response, task.prompt, task
                )
                consultation_metadata = consultation_metadata or {}
                consultation_metadata["provider"] = provider_name

            # 3. Log successful execution
            execution_time = time.time() - start_time
            self._log_routing_decision(
                query=task.prompt,
                route_decision=route.value,
                oracle_result=consultation_metadata,
                execution_time=execution_time,
                actual_route=route_used,
                success=True
            )
            
            return {
                "response": response,
                "execution_details": {
                    "route_used": route_used,
                    "execution_time": execution_time,
                    "consultation_metadata": consultation_metadata,
                }
            }

        except Exception as e:
            # 4. Log error and return a safe response
            execution_time = time.time() - start_time
            print(f"❌ Error during task execution: {e}")
            self._log_routing_decision(
                query=task.prompt,
                route_decision="error",
                oracle_result={"error": str(e)},
                execution_time=execution_time,
                actual_route=route_used,
                success=False,
                error_details=str(e)
            )
            return {
                "response": "An error occurred while processing your request.",
                "error": str(e),
                "execution_details": {
                    "route_used": "error",
                    "execution_time": execution_time,
                    "error_details": str(e),
                }
            }

    def _build_local_context(self, prompt: str, memories: list[dict]) -> str:
        """Build the context string for the local model from memories."""
        if not memories:
            return None # No extra context

        context_str = "Relevant past conversations:\n"
        for mem in memories:
            context_str += f"- {mem['content']}\n"
        
        return context_str

    def _get_preferred_provider(self, task: TaskContext) -> str | None:
        """Get preferred external provider based on config and task type."""
        
        external_prefs = self.identity_config.get("external_llms", {}).get("routing_preferences", {})
        
        # Check for task-specific provider
        if self._is_coding_task(task.prompt):
            coding_provider = external_prefs.get("primary_for_implementation") or external_prefs.get("primary_for_coding")
            if coding_provider:
                print(f"✅ Preferred provider for coding: {coding_provider}")
                return coding_provider
        
        # Fallback to primary provider
        primary_provider = self.identity_config.get("external_llms", {}).get("primary_provider")
        if primary_provider:
            return primary_provider
            
        return None

    async def _prepare_external_prompt(self, task: TaskContext) -> str:
        """Prepare a consultation request for external LLM."""

        # Build entity's self-description for the consultation using identity config
        try:
            name = self.identity_config.get('name', 'AI Assistant')
            identity = self.identity_config.get('identity', {})
            summary = identity.get('summary', 'helpful AI assistant')
            personality_traits = identity.get('personality', [])
            
            entity_intro = f"I am {name}, {summary}."
            
            # Get key personality traits with fallback
            if personality_traits:
                traits_text = ", ".join(personality_traits[:3])
            else:
                traits_text = "technically precise, analytical"
                
        except Exception as e:
            print(f"⚠️ Error accessing personality config: {e}")
            entity_intro = f"I am {self.identity_config.get('name', 'AI Assistant')}, a helpful AI assistant."
            traits_text = "technically precise, analytical"

        # Detect language for response format
        is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in task.prompt.lower())
        response_language = "Russian" if is_russian else "English"

        # Check if this is an ongoing conversation (has context with previous exchanges)
        # Use generic conversation markers that don't depend on specific entity names
        is_ongoing_conversation = False
        if task.conversation_context and isinstance(task.conversation_context, str):
            is_ongoing_conversation = bool(task.conversation_context.strip() and any(
                marker in task.conversation_context
                for marker in ["👤 You:", "🧠", "User:", "Assistant:", "Human:", "AI:"]
            ))

        # Build the consultation prompt with comprehensive context
        consultation_prompt = f"""{entity_intro}

My key traits: {traits_text}

"""

        # Add comprehensive conversation context if available
        if task.conversation_context and isinstance(task.conversation_context, str) and task.conversation_context.strip():
            consultation_prompt += f"""CONVERSATION CONTEXT:
{task.conversation_context}

"""

        # Add conversation flow instructions based on context
        conversation_flow_note = ""
        if is_ongoing_conversation:
            conversation_flow_note = """
IMPORTANT: This is a CONTINUATION of an ongoing conversation. DO NOT include greetings like "Hello", "Hi", "Здравствуйте" etc.
The user and I are already engaged in conversation as shown in the context above.
Simply provide a direct, natural response that continues the flow."""
        else:
            conversation_flow_note = """
Note: This appears to be the start of a conversation or an isolated question.
Natural greetings are appropriate if the context suggests it."""

        consultation_prompt += f"""Question I need expert consultation on: "{task.prompt}"
{conversation_flow_note}

This question requires deeper knowledge than I currently have. Please provide a structured consultation response:

**1. TECHNICAL ANALYSIS** (for my knowledge base):
[Detailed explanation with scientific accuracy and relevant context]

**2. USER RESPONSE** (for me to provide to the user):
[Natural, conversational answer in {response_language} that maintains my personality and response style.
CRITICAL REQUIREMENTS:
- Look at my previous responses in the conversation context above - match that same concise, direct style
- Keep responses brief and focused (1-2 sentences for simple facts)
- Be technically precise but conversational like my other responses
- Avoid excessive detail unless the question specifically asks for it
- Match the length and tone of my previous local responses shown in the context
- {"DO NOT include greetings - continue the conversation naturally" if is_ongoing_conversation else "Include appropriate greetings only if this is a new conversation start"}]

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

    async def _filter_external_response(self, external_response: str, original_prompt: str, task: TaskContext | None = None) -> tuple[str, dict]:
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
            return await self._fallback_filter_response(external_response, original_prompt, task)

        except Exception as e:
            print(f"Error parsing consultation response: {e}")
            return await self._fallback_filter_response(external_response, original_prompt, task)

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

        lines = response.split("\n")
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
                    content = "\n".join(current_content).strip()
                    if current_section == "memory_points":
                        # Parse bullet points
                        points = [point.strip("- •*").strip() for point in current_content if point.strip().startswith(("- ", "• ", "* "))]
                        result[current_section] = points
                    else:
                        result[current_section] = content

                # Start new section
                current_section = section_found
                current_content = []
            elif current_section:
                # Skip lines that are just section markers or brackets
                if not line_clean.startswith("[") or not line_clean.endswith("]"):
                    current_content.append(line)

        # Save final section
        if current_section and current_content:
            content = "\n".join(current_content).strip()
            if current_section == "memory_points":
                points = [point.strip("- •*").strip() for point in current_content if point.strip().startswith(("- ", "• ", "* "))]
                result[current_section] = points
            else:
                result[current_section] = content

        return result if any(result.values()) else None

    async def _fallback_filter_response(self, external_response: str, original_prompt: str, task: TaskContext | None = None) -> tuple[str, dict]:
        """Fallback filtering for unstructured responses (original logic)."""

        # Detect language of original prompt
        is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in original_prompt.lower())

        # Check if this is an ongoing conversation using generic markers
        is_ongoing_conversation = False
        if task and task.conversation_context and isinstance(task.conversation_context, str):
            is_ongoing_conversation = bool(task.conversation_context.strip() and any(
                marker in task.conversation_context
                for marker in ["👤 You:", "🧠", "User:", "Assistant:", "Human:", "AI:"]
            ))

        # Create a personality filter prompt using English core identity for better model understanding
        try:
            name = self.identity_config.get('name', 'AI Assistant')
            identity = self.identity_config.get('identity', {})
            summary = identity.get('summary', 'helpful AI assistant')
            personality_traits = identity.get('personality', [])
            
            core_traits = ", ".join(personality_traits[:3]) if personality_traits else "helpful, analytical, precise"
            
            core_values = self.identity_config.get('core_values', [])
            core_values_text = ", ".join(core_values[:2]) if core_values else "accuracy, helpfulness"
            
        except Exception as e:
            print(f"⚠️ Error accessing config in filter: {e}")
            core_traits = "helpful, analytical, precise"
            core_values_text = "accuracy, helpfulness"
            name = "AI Assistant"
            summary = "helpful AI assistant"

        # Add conversation flow instruction
        flow_instruction = ""
        if is_ongoing_conversation:
            flow_instruction = "7. This is a continuation of an ongoing conversation - DO NOT include greetings or reintroductions"
        else:
            flow_instruction = "7. Include appropriate greetings only if this is clearly a new conversation start"

        if is_russian:
            filter_prompt = f"""Original user question: {original_prompt}

External system response: {external_response}

Reframe this response as {name} - {summary}. Important personality traits: {core_traits}. Core principles: {core_values_text}.

Requirements:
1. Maintain my personality and traits listed above
2. Keep all useful information from the response
3. Make the response natural according to my character
4. Don't mention ChatGPT or other systems - you are {name}
5. Respond in Russian with natural grammar and cultural context
6. Follow my core principles
{flow_instruction}

Response in Russian:"""
        else:
            filter_prompt = f"""Original user question: {original_prompt}

External system response: {external_response}

Reframe this response as {name} - {summary}. Important personality traits: {core_traits}. Core principles: {core_values_text}.

Requirements:
1. Maintain my personality and traits listed above
2. Keep all useful information from the response
3. Make the response natural according to my character
4. Don't mention ChatGPT or other systems - you are {name}
5. Respond in English
6. Follow my core principles
{flow_instruction}

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
                return f"[От {name}] {external_response}", {}
            else:
                return f"[From {name}] {external_response}", {}

    def get_routing_stats(self) -> dict[str, Any]:
        """Get routing statistics including calibrator metrics."""
        total_routes = self._routing_stats["local_routes"] + self._routing_stats["external_routes"]

        return {
            "total_routes": total_routes,
            "local_percentage": (self._routing_stats["local_routes"] / max(total_routes, 1)) * 100,
            "external_percentage": (self._routing_stats["external_routes"] / max(total_routes, 1)) * 100,
            "routing_errors": self._routing_stats["routing_errors"],
            "calibrator_enabled": self.use_calibrator,
            "calibrator_predictions": self._routing_stats["calibrator_predictions"],
            "fallback_threshold_used": self._routing_stats["fallback_threshold_used"],
            "calibrator_stats": calibrator.get_stats(),
        }


    async def health_check(self) -> dict[str, Any]:
        """Check health of local and external LLMs."""
        local_available = self.local_llm and await self.local_llm.is_available()
        external_available = await self.external_manager.get_best_available() is not None

        # Get available providers without triggering async calls
        available_providers = self.external_manager.list_available_providers()

        return {
            "local_llm_available": local_available,
            "external_llm_available": external_available,
            "available_external_providers": [p.value for p in available_providers],
            "routing_stats": self.get_routing_stats(),
        }

    def _estimate_routing_correctness(self, route_used: str, local_confidence: str, response: str) -> bool:
        """Estimate if the routing decision was correct based on heuristics.

        This is a temporary heuristic until we can get real user feedback.
        In production, user feedback would be the gold standard.
        """
        # For local routes
        if route_used in ["local", "local_fallback"]:
            # Local routing is "correct" if:
            # 1. Confidence was medium or high, AND
            # 2. Response is substantial (not a fallback response)
            confidence_ok = local_confidence in ["medium", "high"]
            response_ok = len(response) > 50 and "извините" not in response.lower() and "sorry" not in response.lower()
            return confidence_ok and response_ok

        # For external routes
        elif route_used == "external":
            # External routing is "correct" if it was triggered by:
            # 1. Low local confidence, OR
            # 2. Complex query requiring external knowledge
            # We assume external routes are generally correct unless obviously wrong
            return True

        # For error cases
        else:
            return False

    def _build_assessment_context(self, task: TaskContext) -> str:
        """Build enhanced context for local LLM self-assessment."""

        context_parts = []

        # Add conversation context if available
        if task.conversation_context:
            context_parts.append(f"CONVERSATION CONTEXT:\n{task.conversation_context}")

        # Add assessment guidelines
        context_parts.append("""
SELF-ASSESSMENT GUIDELINES:
- Scientific topics (physics, chemistry, engineering): ALWAYS require external consultation
- Technical explanations requiring precision: Use external consultation
- Mathematical calculations or formulas: Use external consultation
- Complex processes or mechanisms: Consider external consultation
- Simple conversations or personal topics: Can handle locally
- Questions about your capabilities: Can handle locally
""")

        return "\n\n".join(context_parts) if context_parts else ""

    def _validate_self_assessment(self, prompt: str, confidence: str, external_needed: bool, reasoning: str) -> bool:
        """Validate self-assessment for consistency with topic requirements."""

        prompt_lower = prompt.lower()

        # Scientific/technical topics should have low confidence and external_needed=True
        scientific_keywords = [
            "квантов", "физик", "двигатель", "тепловой", "механизм", "энергия", "принцип",
            "quantum", "physics", "engine", "thermal", "mechanism", "energy", "principle",
            "химия", "биология", "математика", "формула", "уравнение",
            "chemistry", "biology", "mathematics", "formula", "equation"
        ]

        is_scientific = any(keyword in prompt_lower for keyword in scientific_keywords)

        if is_scientific:
            # For scientific topics, we expect low confidence and external_needed=True
            if confidence == "high" or not external_needed:
                print(f"🔍 Inconsistent assessment: Scientific topic with confidence={confidence}, external_needed={external_needed}")
                return False

        # Explanation/process questions should generally require external consultation
        explanation_keywords = ["как", "что такое", "расскажи", "объясни", "устроен", "работает", "how", "what is", "explain", "works"]
        is_explanation = any(keyword in prompt_lower for keyword in explanation_keywords)

        if is_explanation and is_scientific:
            # Scientific explanations should definitely use external
            if not external_needed:
                print("🔍 Inconsistent assessment: Scientific explanation without external consultation")
                return False

        return True

    def _rules_based_assessment(self, prompt: str) -> tuple[str, bool]:
        """Fallback rules-based assessment for consistency."""

        prompt_lower = prompt.lower()

        # Scientific/technical topics
        scientific_keywords = [
            "квантов", "физик", "двигатель", "тепловой", "механизм", "энергия", "принцип",
            "quantum", "physics", "engine", "thermal", "mechanism", "energy", "principle",
            "химия", "биология", "математика", "формула", "уравнение",
            "chemistry", "biology", "mathematics", "formula", "equation"
        ]

        is_scientific = any(keyword in prompt_lower for keyword in scientific_keywords)

        if is_scientific:
            return "low", True  # Low confidence, external needed

        # Complex explanation topics
        explanation_keywords = ["как", "что такое", "расскажи", "объясни", "устроен", "работает", "how", "what is", "explain", "works"]
        is_explanation = any(keyword in prompt_lower for keyword in explanation_keywords)

        if is_explanation:
            return "medium", True  # Medium confidence, but external recommended

        # Simple conversational topics
        conversational_keywords = ["привет", "как дела", "кто", "меня зовут", "hello", "how are", "who are", "my name"]
        is_conversational = any(keyword in prompt_lower for keyword in conversational_keywords)

        if is_conversational:
            return "high", False  # High confidence, no external needed

        # Default: medium confidence, consider external
        return "medium", False
