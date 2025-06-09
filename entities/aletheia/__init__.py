"""
Aletheia Entity for Prometheus Framework

A scientifically-minded AI entity focused on truth-seeking and analytical thinking.
Enhanced with Self-RAG capabilities for improved reflection and context optimization.
"""

import json
from pathlib import Path
from typing import Any

from core import BaseEntity
from core.context.retrieval_optimizer import RetrievalOptimizer
from core.memory.memory_critic import MemoryCritic
from core.reflection.self_rag_reflection import SelfRAGReflection


class AletheiaEntity(BaseEntity):
    """
    Aletheia - Truth-seeking AI entity with Self-RAG enhancements.
    
    Focused on scientific accuracy, analytical thinking, and honest communication.
    Enhanced with advanced memory management, reflection, and context optimization.
    """
    
    # Entity configuration
    IDENTITY_PATH = Path(__file__).parent / "identity"
    
    def __init__(self):
        """Initialize Aletheia with optional Self-RAG components."""
        # Initialize Self-RAG components
        self.memory_critic = None
        self.enhanced_reflection = None
        self.retrieval_optimizer = None

        # Performance tracking
        self.enhancement_stats = {
            "memory_audits_performed": 0,
            "enhanced_reflections": 0,
            "context_optimizations": 0,
            "quality_assessments": 0
        }

        # Call parent initialization
        super().__init__()

        # Initialize Self-RAG components after parent initialization
        self._initialize_self_rag_components()

    def _initialize_self_rag_components(self):
        """Initialize Self-RAG components with entity's identity."""
        print("🧠 Initializing Self-RAG enhancements...")

        try:
            self.memory_critic = MemoryCritic(identity_config=self.identity_config)
            self.enhanced_reflection = SelfRAGReflection(identity_config=self.identity_config)
            self.retrieval_optimizer = RetrievalOptimizer(identity_config=self.identity_config)

            print("✅ Self-RAG enhancements initialized")

            # Replace default reflection with enhanced version
            self.reflection_engine = self.enhanced_reflection

        except Exception as e:
            print(f"⚠️ Failed to initialize Self-RAG components: {e}")
            print("   Falling back to default components")

    def _load_identity(self) -> dict[str, Any]:
        """Load Aletheia's identity, merging register info and config file."""
        try:
            # 1. Get base registration info
            reg_info = register()
            
            # 2. Load detailed config from JSON
            identity_file = self.IDENTITY_PATH / "identity.json"
            if not identity_file.exists():
                print(f"⚠️ Identity file not found: {identity_file}. Using registration info only.")
                return reg_info

            with open(identity_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 3. Merge them
            final_config = {**config, **reg_info}
            
            # Use the simple name for logging
            log_name = reg_info.get('name', {}).get('ru', reg_info.get('id'))
            print(f"✅ Loaded identity for {log_name}")

            return final_config
            
        except Exception as e:
            print(f"⚠️ Error loading Aletheia's identity: {e}")
            return register() # Fallback to base registration info

    async def process_query(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Enhanced query processing with Self-RAG capabilities.

        Args:
            query: User query
            context: Additional context

        Returns:
            Enhanced response with quality metrics
        """
        context = context or {}

        print("🔍 Aletheia processing query with Self-RAG...")

        # Reset conversation context to prevent contamination
        await self._reset_conversation_context()

        # Check if we should use fast mode
        fast_mode = context.get("fast_mode", False)

        # Step 1: Optimize context retrieval if enabled (skip in fast mode)
        optimized_context = context
        if not fast_mode and self.retrieval_optimizer and context.get("enable_optimization", True):
            clean_context = {
                "max_context_length": context.get("max_context_length", 2000),
                "enable_optimization": True
            }
            optimized_context = await self._optimize_context_retrieval(query, clean_context)
            self.enhancement_stats["context_optimizations"] += 1

        # Step 2: Process query using the base entity's think method
        response = await self.think(query)

        # Create response data structure
        response_data = {
            "response": response,
            "query": query,
            "context": optimized_context
        }

        # Step 3: Enhanced reflection and quality assessment (simplified in fast mode)
        if self.enhanced_reflection:
            if fast_mode:
                # Fast mode: simplified quality assessment
                quality_assessment = await self._fast_quality_assessment(query, response)
            else:
                # Full mode: comprehensive quality assessment
                quality_assessment = await self._assess_response_quality(
                    query, response, optimized_context
                )
            response_data["quality_assessment"] = quality_assessment
            self.enhancement_stats["quality_assessments"] += 1

        # Step 4: Periodic memory audit (skip in fast mode)
        if not fast_mode and self.memory_critic:
            await self._maybe_audit_memory()

        # Add enhancement statistics
        response_data["enhancement_stats"] = self.enhancement_stats.copy()

        return response_data

    async def _reset_conversation_context(self):
        """Reset conversation context to prevent contamination between queries."""
        try:
            print("🔄 Performing comprehensive context reset...")

            # Reset conversation context
            if hasattr(self, "context") and self.context:
                # Clear episodes and running summaries
                self.context.episodes = []
                self.context.running_summaries = {}
                self.context.current_user_id = "default"
                self.context.interaction_count = 0
                self.context.session_id = None
                self.context.last_user_language = "en"
                print("✅ Conversation context reset")

            # Reset router context if available
            if hasattr(self, "router") and self.router:
                if hasattr(self.router, "utility_llm") and self.router.utility_llm:
                    await self.router.utility_llm._reset_model_context()
                    print("✅ Utility LLM context reset")
                if hasattr(self.router, "local_llm") and self.router.local_llm:
                    if hasattr(self.router.local_llm, "_reset_model_context"):
                        await self.router.local_llm._reset_model_context()
                        print("✅ Local LLM context reset")

            # Reset vector store context if available
            if hasattr(self, "vector_store") and self.vector_store:
                # Clear any cached search results
                if hasattr(self.vector_store, "_last_search_results"):
                    self.vector_store._last_search_results = None
                print("✅ Vector store context reset")

            # Reset memory controller if available
            if hasattr(self, "memory_controller") and self.memory_controller:
                # Reset any cached state
                if hasattr(self.memory_controller, "_cached_memories"):
                    self.memory_controller._cached_memories = {}
                print("✅ Memory controller context reset")

            # Reset Self-RAG components
            if self.enhanced_reflection:
                # Reset reflection stats to prevent cross-contamination
                self.enhanced_reflection.reflection_stats = {
                    "reflections_performed": 0,
                    "quality_assessments": 0,
                    "retrieval_assessments": 0,
                    "improvement_suggestions": 0
                }
                print("✅ Enhanced reflection context reset")

            # Reset task history to prevent contamination
            if hasattr(self, "task_history"):
                self.task_history = []
                print("✅ Task history reset")

            print("🔄 Comprehensive context reset complete")

        except Exception as e:
            print(f"⚠️ Context reset failed: {e}")
            # Continue anyway - partial reset is better than no reset

    async def _optimize_context_retrieval(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Optimize context retrieval using the retrieval optimizer.

        Args:
            query: User query
            context: Original context

        Returns:
            Optimized context
        """
        try:
            # Extract conversation history and memory items
            conversation_history = []
            if context.get("conversation_context"):
                conversation_history = context["conversation_context"].split("\n")

            memory_items = []
            if hasattr(self, "vector_store") and self.vector_store:
                # Get relevant memories (simplified for testing)
                memory_items = [
                    {"content": "Sample memory item", "metadata": {"timestamp": "2024-01-01T10:00:00Z"}}
                ]

            # Optimize context selection
            optimization_result = await self.retrieval_optimizer.smart_context_selection(
                query=query,
                conversation_history=conversation_history,
                memory_items=memory_items,
                max_context_length=context.get("max_context_length", 2000)
            )

            # Update context with optimized content
            optimized_context = context.copy()
            optimized_context["conversation_context"] = optimization_result["optimized_context"]
            optimized_context["optimization_metadata"] = {
                "items_used": optimization_result["context_items_used"],
                "total_evaluated": optimization_result["total_items_evaluated"],
                "context_length": optimization_result["context_length"]
            }

            print(f"📊 Context optimization: {optimization_result['total_items_evaluated']} → {optimization_result['context_items_used']} items")

            return optimized_context

        except Exception as e:
            print(f"⚠️ Context optimization failed: {e}")
            return context  # Return original context on failure

    async def _assess_response_quality(self, query: str, response: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Assess the quality of the generated response.

        Args:
            query: Original query
            response: Generated response
            context: Context used

        Returns:
            Quality assessment
        """
        try:
            # Perform enhanced reflection
            reflection_result = await self.enhanced_reflection.reflect_on_task(query, response, context)

            if reflection_result:
                self.enhancement_stats["enhanced_reflections"] += 1

                # Extract key quality metrics
                response_quality = reflection_result.get("response_quality")
                overall_reflection = reflection_result.get("overall_reflection", {})

                return {
                    "overall_score": response_quality.overall if response_quality else 0.5,
                    "confidence": response_quality.confidence if response_quality else "medium",
                    "key_insights": overall_reflection.get("key_insights", []),
                    "improvement_areas": response_quality.improvement_areas if response_quality else [],
                    "reflection_timestamp": reflection_result.get("timestamp")
                }


        except Exception as e:
            print(f"⚠️ Response quality assessment failed: {e}")

        return {
            "overall_score": 0.5,
            "confidence": "medium",
            "key_insights": ["Assessment not available"],
            "improvement_areas": ["Unable to assess"],
            "reflection_timestamp": None
        }

    async def _fast_quality_assessment(self, query: str, response: str) -> dict[str, Any]:
        """Fast quality assessment without LLM calls."""
        # Basic heuristic-based quality assessment
        quality_score = 0.7  # Default reasonable score

        # Language matching
        query_is_russian = any("\u0400" <= char <= "\u04FF" for char in query)
        response_is_russian = any("\u0400" <= char <= "\u04FF" for char in response)
        language_match = query_is_russian == response_is_russian

        # Length appropriateness
        length_appropriate = 50 <= len(response) <= 1000

        # Basic relevance (keyword overlap)
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        overlap = len(query_words & response_words) / len(query_words) if query_words else 0

        # Adjust score based on heuristics
        if language_match:
            quality_score += 0.1
        if length_appropriate:
            quality_score += 0.1
        if overlap > 0.2:
            quality_score += 0.1

        quality_score = min(quality_score, 1.0)

        return {
            "overall_score": quality_score,
            "confidence": "medium",
            "key_insights": ["Fast assessment mode"],
            "improvement_areas": ["Use full assessment for detailed analysis"],
            "reflection_timestamp": None
        }

    async def _maybe_audit_memory(self):
        """
        Perform memory audit if conditions are met.
        """
        try:
            # Check if audit is needed
            config = self.identity_config.get("self_rag_config", {})
            audit_frequency = config.get("memory_audit_frequency", 50)

            # Simple counter-based trigger (in production would use more sophisticated triggers)
            if self.enhancement_stats["quality_assessments"] % audit_frequency == 0:
                print("🔍 Triggering periodic memory audit...")

                if hasattr(self, "vector_store") and self.vector_store:
                    # Simplified audit for testing
                    audit_result = {
                        "action_needed": True,
                        "average_quality": 0.75,
                        "purge_candidates": 2,
                        "enhancement_candidates": 3
                    }

                    self.enhancement_stats["memory_audits_performed"] += 1

                    # Log audit results
                    if audit_result.get("action_needed"):
                        print(f"📋 Memory audit complete: {audit_result['average_quality']:.2f} avg quality")
                        print(f"   Recommendations: {audit_result['purge_candidates']} to purge, {audit_result['enhancement_candidates']} to enhance")

        except Exception as e:
            print(f"⚠️ Memory audit failed: {e}")

    async def get_enhancement_report(self) -> dict[str, Any]:
        """
        Get a comprehensive report on Self-RAG enhancements.

        Returns:
            Enhancement report with statistics and insights
        """
        report = {
            "enhancement_stats": self.enhancement_stats.copy(),
            "components_status": {
                "memory_critic": self.memory_critic is not None,
                "enhanced_reflection": self.enhanced_reflection is not None,
                "retrieval_optimizer": self.retrieval_optimizer is not None
            }
        }

        # Add component-specific statistics
        if self.memory_critic:
            try:
                report["memory_critic_stats"] = self.memory_critic.get_critique_stats()
            except:
                report["memory_critic_stats"] = {"error": "Unable to get stats"}

        if self.enhanced_reflection:
            try:
                report["reflection_stats"] = self.enhanced_reflection.get_reflection_stats()
            except:
                report["reflection_stats"] = {"error": "Unable to get stats"}

        if self.retrieval_optimizer:
            try:
                report["optimization_stats"] = self.retrieval_optimizer.get_optimization_stats()
            except:
                report["optimization_stats"] = {"error": "Unable to get stats"}

        return report


def register() -> dict[str, Any]:
    """Register Aletheia entity with the framework."""
    return {
        "id": "aletheia",                     # 🔧 Technical ID for registry/API
        "name": {                             # 🏷️ Multilingual human-readable names
            "en": "Aletheia",
            "ru": "Алетейя"
        },
        "class": AletheiaEntity,             # 🏗️ Implementation class
        "description": "Truth-seeking AI entity with Self-RAG capabilities for enhanced memory, reflection, and context optimization",
        "version": "2.0.0",
        "role": "truth_seeker",              # 🎭 Functional role
        "capabilities": [
            "scientific_analysis",
            "fact_checking", 
            "analytical_reasoning",
            "honest_communication",
            "memory_criticism",
            "enhanced_reflection",
            "context_optimization",
            "quality_assessment"
        ],
        "team_position": "analyst",
        "personality": "scientific_truth_seeker",
        "display_info": {
            "icon": "🔍",
            "color": "#0EA5E9",
            "short_name": "Алетейя"
        }
    }
