"""
Base Entity Class

Provides the core framework functionality that all entities inherit.
Defines clear contracts for identity, planning, and reflection overrides.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import config
from .context.context_manager import ConversationContext
from .goals.goal_manager import GoalManager
from .llm.router import LLMRouter
from .memory.controller import MemoryController
from .memory.summariser import MemorySummariser
from .memory.user_profile_store import UserProfileStore
from .memory.vector_store import VectorStore

logger = logging.getLogger(__name__)


class BasePlanner(ABC):
    """Base planner interface for entities to override."""

    def __init__(self, router: LLMRouter):
        self.router = router

    @abstractmethod
    async def create_plan(self, task: str) -> dict[str, Any] | None:
        """Create a plan for the given task."""


class BaseReflection(ABC):
    """Base reflection interface for entities to override."""

    def __init__(self, router: LLMRouter, vector_store: VectorStore):
        self.router = router
        self.vector_store = vector_store

    @abstractmethod
    async def should_reflect(self, complexity: float) -> bool:
        """Determine if reflection is needed."""

    @abstractmethod
    async def reflect_on_task(self, task: str, response: str, context: dict[str, Any]) -> dict[str, Any] | None:
        """Reflect on a completed task."""


class BaseEntity(ABC):
    """
    Base entity class providing core framework functionality.

    Entities inherit from this and override specific behaviors through:
    - IDENTITY_PATH: Path to identity configuration
    - PlannerClass: Custom planning behavior
    - ReflectionClass: Custom reflection behavior
    """

    # Entity contracts - must be defined by subclasses
    IDENTITY_PATH: Path
    PlannerClass: type[BasePlanner] = None  # Will use default if not overridden
    ReflectionClass: type[BaseReflection] = None  # Will use default if not overridden

    def __init__(self) -> None:
        """Initialize the entity with core framework components."""

        print(f"🚀 Initializing {self.__class__.__name__} entity...")

        # Session management
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.task_history: list[dict[str, Any]] = []

        # Load identity configuration
        self.identity_config = self._load_identity()

        # Initialize core components
        self.vector_store = VectorStore()
        self.router = LLMRouter(identity_config=self.identity_config)
        self.context = ConversationContext(self.identity_config)
        self.goal_manager = GoalManager()
        self.memory_summariser = MemorySummariser(self.vector_store)
        self.user_profile_store = UserProfileStore()

        # Initialize memory system
        if config.use_hierarchical_memory:
            self.memory_controller = MemoryController()
            print("🧠 Using three-tier memory system (Core-Self, User, Environment)")
        else:
            self.memory_controller = None
            print("💾 Using simple memory system")

        # Initialize entity-specific components
        self.planner = self._create_planner()
        self.reflection_engine = self._create_reflection_engine()

        print(f"✅ {self.__class__.__name__} entity initialized")

    @abstractmethod
    def _load_identity(self) -> dict[str, Any]:
        """Load entity-specific identity configuration."""

    def _create_planner(self) -> BasePlanner:
        """Create planner instance (can be overridden by entity)."""
        if self.PlannerClass:
            return self.PlannerClass(self.router)

        # Default planner implementation
        from .planning.default_planner import DefaultPlanner
        return DefaultPlanner(self.router)

    def _create_reflection_engine(self) -> BaseReflection:
        """Create reflection engine instance (can be overridden by entity)."""
        if self.ReflectionClass:
            return self.ReflectionClass(self.router, self.vector_store)

        # Default reflection implementation
        from .reflection.default_reflection import DefaultReflection
        return DefaultReflection(self.router, self.vector_store)

    async def think(self, user_text: str, user_id: str | None = None) -> str:
        """
        Main thinking interface - processes user input and returns response.

        Args:
            user_text: User input text
            user_id: Optional user identifier for session management

        This is the primary contract method that entities must support.
        """

        print(f"\n🧠 Processing: {user_text[:100]}{'...' if len(user_text) > 100 else ''}")
        if user_id:
            print(f"👤 User session: {user_id}")

        start_time = datetime.now()

        # Update conversation context with user_id
        self.context.update_from_input(user_text, user_id=user_id)

        try:
            # Process through the entity's thinking pipeline
            result = await self._process_input(user_text, user_id=user_id)

            # Extract response and execution details
            response = result.get("response", "")
            execution_details = result.get("execution_details", {})

            # Calculate total thinking time
            end_time = datetime.now()
            total_thinking_time = (end_time - start_time).total_seconds()

            # Display comprehensive debug output
            self._display_debug_summary(user_text, result, total_thinking_time)

            # Add to context
            self.context.add_episode(user_text, response, execution_details)

            # Update running summary
            await self.context.update_summary_from_exchange(
                user_text, response, self.router.local_llm
            )

            # Store experience in memory with user_id
            await self._store_experience(user_text, result, user_id=user_id)

            # Optional reflection
            if config.reflection_enabled:
                await self._maybe_reflect(user_text, result)

            # Memory management
            await self._manage_memory()

            # Track in history
            task_record = {
                "timestamp": start_time.isoformat(),
                "user_input": user_text,
                "user_id": user_id,
                "result": result,
                "session_id": self.session_id,
                "conversation_context": self.context.get_context_summary(),
                "total_thinking_time": total_thinking_time,
            }
            self.task_history.append(task_record)

            return response

        except Exception as e:
            error_response = f"I'm experiencing technical difficulties: {e}"
            print(f"❌ Error processing input: {e}")
            return error_response

    def _display_debug_summary(self, user_input: str, result: dict[str, Any], total_time: float) -> None:
        """Display comprehensive debug information about the thinking process."""
        execution_details = result.get("execution_details", {})
        route_used = execution_details.get("route_used", "unknown")
        approach = execution_details.get("approach", "unknown")

        # Route-specific debug info
        if route_used == "local":
            print(f"🎯 Route: Local LLM | Approach: {approach}")
        elif route_used == "external":
            print(f"🌐 Route: External LLM | Approach: {approach}")
            # Show consultation metadata if available
            consultation_metadata = execution_details.get("consultation_metadata")
            if consultation_metadata:
                provider = consultation_metadata.get("provider", "unknown")
                model = consultation_metadata.get("model", "unknown")
                print(f"📡 External: {provider} ({model})")
        elif route_used == "user_profile":
            print("📊 Route: User Profile Store | Instant Response")
        else:
            print(f"🔀 Route: {route_used} | Approach: {approach}")

        # Performance metrics
        execution_time = execution_details.get("execution_time", 0)
        estimated_cost = execution_details.get("estimated_cost", 0)

        # Additional context information
        context_info = []
        if execution_details.get("episodes_used"):
            context_info.append(f"Episodes: {execution_details['episodes_used']}")
        if execution_details.get("user_profile_used"):
            context_info.append("Profile: ✓")
        if execution_details.get("memories_used"):
            context_info.append(f"Memories: {execution_details['memories_used']}")

        context_str = " | ".join(context_info) if context_info else "No additional context"

        # Format performance summary
        performance_parts = [f"Total: {total_time:.1f}s"]
        if execution_time > 0:
            performance_parts.append(f"LLM: {execution_time:.1f}s")
        if estimated_cost > 0:
            performance_parts.append(f"Cost: ${estimated_cost:.4f}")

        performance_str = " | ".join(performance_parts)

        # Final summary line
        print(f"💭 {performance_str} | {context_str}")

        # Clean response confirmation
        response = result.get("response", "")
        if response and not any(marker in response for marker in ["ANSWER:", "CONFIDENCE:", "REASONING:"]):
            print("✅ Clean response: No technical contamination")
        elif any(marker in response for marker in ["ANSWER:", "CONFIDENCE:", "REASONING:"]):
            print("⚠️ Response contains technical markers - check parsing")

    async def autonomous_loop(self) -> None:
        """
        Autonomous operation mode for background entity operation.

        Override this for entity-specific autonomous behaviors.
        """
        print(f"🔄 Starting autonomous loop for {self.__class__.__name__}")

        while True:
            try:
                # Check for autonomous goals/tasks
                await self.goal_manager.process_autonomous_goals()

                # Background memory management
                await self._manage_memory()

                # Sleep between cycles
                await asyncio.sleep(config.autonomous_cycle_interval or 60)

            except KeyboardInterrupt:
                print("🛑 Autonomous loop interrupted")
                break
            except Exception as e:
                print(f"⚠️ Error in autonomous loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying

    async def _process_input(self, user_input: str, user_id: str | None = None) -> dict[str, Any]:
        """Core input processing logic - can be extended by entities."""

        # User data handling
        user_name = self.context.user_name
        if user_name:
            # Check for data providing vs querying
            is_providing_info = self.user_profile_store.extractor.is_information_providing(user_input)

            if is_providing_info:
                print("📊 Detected user providing information - extracting data...")
                await self.user_profile_store.update_user_data(
                    user_name, user_input,
                    context=f"Session {self.session_id}, Task #{len(self.task_history) + 1}"
                )
            elif await self.user_profile_store.is_data_query(user_input):
                print("🔍 Detected user data query - providing profile summary...")
                summary = await self.user_profile_store.get_user_data_summary(user_name)
                return {
                    "type": "user_data_query",
                    "response": summary,
                    "execution_details": {
                        "route_used": "user_profile",
                        "execution_time": 0.0,
                        "estimated_cost": 0,
                        "data_source": "user_profile_store"
                    },
                    "approach": "user_data_retrieval"
                }

        # Retrieve relevant memories
        relevant_memories = await self._retrieve_relevant_memories(user_input)

        # Determine if planning is needed
        needs_planning = self.context.should_plan_task(user_input)

        if needs_planning:
            return await self._handle_complex_task(user_input, relevant_memories)
        else:
            return await self._handle_simple_task(user_input, relevant_memories)

    async def _retrieve_relevant_memories(self, user_input: str) -> list[dict[str, Any]]:
        """Retrieve relevant memories for context."""
        try:
            # Use the fast LLM for query preprocessing if available
            if hasattr(self.router, "utility_llm") and await self.router.utility_llm.is_available():
                print("🔧 Utility model: Classifying query for memory filtering...")

                # Preprocess the query for better memory matching
                query_category = await self.router.utility_llm.classify_query(user_input)
                print(f"🔧 Query categorized as: {query_category}")

                expanded_concepts = await self.router.utility_llm.expand_query_concepts(user_input)

                # Create enhanced query for vector search
                enhanced_query = f"{user_input} {' '.join(expanded_concepts)}"
            else:
                enhanced_query = user_input
                query_category = "general"
                print("⚡ Using direct query (utility model not available)")

            # Retrieve memories from vector store
            memories = await self.vector_store.search_memories(enhanced_query, n_results=8)

            if not memories:
                print("📂 No memories found for current query")
                return []

            print(f"📂 Found {len(memories)} memories, filtering for relevance...")

            # Filter and rank memories by semantic relevance
            relevant_memories = []

            # Use utility model for memory categorization if available
            if hasattr(self.router, "utility_llm") and await self.router.utility_llm.is_available():
                print("🔧 Utility model: Categorizing memories...")

                memory_categories = []
                for i, memory in enumerate(memories):
                    memory_category = await self.router.utility_llm.classify_memory_content(memory["content"])
                    memory_categories.append(memory_category)

                # Show categorization results
                category_summary = {}
                for cat in memory_categories:
                    category_summary[cat] = category_summary.get(cat, 0) + 1

                category_str = ", ".join([f"{cat}: {count}" for cat, count in category_summary.items()])
                print(f"🔧 Memory categories: {category_str}")
            else:
                memory_categories = ["general"] * len(memories)

            # Calculate relevance and filter
            for i, memory in enumerate(memories):
                distance = memory.get("distance", 1.0)
                memory_category = memory_categories[i]

                # Calculate semantic relevance
                relevance_score = self._calculate_semantic_relevance(query_category, memory_category, distance)

                # Include memory if it meets relevance threshold
                if relevance_score >= 0.15:  # FIXED: Lower threshold from 0.3 to 0.15 to find more relevant memories
                    memory["relevance_score"] = relevance_score
                    memory["query_category"] = query_category
                    memory["memory_category"] = memory_category
                    relevant_memories.append(memory)

            # Sort by relevance score
            relevant_memories.sort(key=lambda x: x["relevance_score"], reverse=True)

            # Limit to top 5 most relevant
            final_memories = relevant_memories[:5]

            if final_memories:
                print(f"🔧 Utility model: Filtering complete. {len(final_memories)}/{len(memories)} memories passed filtering")
            else:
                print("📂 No memories met relevance threshold")

            return final_memories

        except Exception as e:
            print(f"⚠️ Error retrieving memories: {e}")
            return []

    def _calculate_semantic_relevance(self, query_category: str, memory_category: str, distance: float) -> float:
        """Calculate semantic relevance between query and memory."""
        # Base score from vector similarity (lower distance = higher relevance)
        base_score = max(0.0, 1.0 - distance)

        # Category matching bonus
        category_bonus = 0.0
        if query_category == memory_category:
            category_bonus = 0.2
        elif query_category in ["technical", "explanation"] and memory_category in ["technical", "explanation"]:
            category_bonus = 0.1

        # Combine scores
        return min(1.0, base_score + category_bonus)


    async def _handle_complex_task(self, user_input: str, memories: list[dict[str, Any]]) -> dict[str, Any]:
        """Handle complex tasks requiring planning."""
        # This logic will be moved from orchestrator.py
        return {"response": "Complex task handling not yet implemented", "route_used": "planning"}

    async def _handle_simple_task(self, user_input: str, memories: list[dict[str, Any]]) -> dict[str, Any]:
        """Handle simple tasks with direct routing through LLM router."""

        start_time = time.time()

        # Get user name for context
        user_name = self.context.user_name

        # Check if we should retrieve episodes for additional context
        should_retrieve = self.context.should_retrieve_episodes(user_input)
        relevant_episodes = []

        if should_retrieve:
            relevant_episodes = self.context.search_relevant_episodes(user_input, max_episodes=3)
            print(f"📚 Retrieved {len(relevant_episodes)} relevant episodes for context")

        # Build enhanced context prompt with running summary
        system_prompt = self.identity_config.get("llm_instructions", "You are a helpful AI assistant.")
        context_prompt = self.context.build_context_prompt(user_input, system_prompt)

        # Add episode context if available
        if relevant_episodes:
            episode_context = "\n".join([
                f"Previous exchange: User asked '{ep['user_input'][:100]}...', I responded with '{ep['assistant_response'][:100]}...'"
                for ep in relevant_episodes
            ])
            # Insert episode context before the conversation section
            context_prompt = context_prompt.replace(
                "### CONVERSATION",
                f"### RELEVANT EPISODES\n{episode_context}\n\n### CONVERSATION"
            )

        # Add user profile data to context if available and relevant
        user_profile_context = ""
        if user_name and user_name != "default":
            user_profile_context = await self.user_profile_store.get_user_data_context(user_name)
            if user_profile_context:
                context_prompt = context_prompt.replace(
                    "### CONVERSATION",
                    f"### USER PROFILE\n{user_profile_context}\n\n### CONVERSATION"
                )
                print("📊 Added user profile context")

        print("⚡ Handling simple task with LLM-managed context...")

        # Use router to make intelligent routing decision
        try:
            # Build enhanced context for router decision
            enhanced_context = self._build_context_summary()

            # Import TaskContext for router
            from .llm.router import TaskContext

            task_context = TaskContext(
                prompt=user_input,
                max_tokens=1024,
                requires_deep_reasoning=False,  # Let router decide based on content
                conversation_context=enhanced_context,
                user_name=user_name,
                session_context={
                    "session_id": self.session_id,
                    "interaction_count": len(self.task_history),
                    "language": getattr(self.context, "last_user_language", "en")
                }
            )

            # Router makes intelligent local vs external decision
            result = await self.router.execute_task(task_context)
            route_used = result.get("route_used", "router_decision")
            response_text = result.get("result", "")

            # Add to episodes storage
            self.context.add_episode(user_input, response_text, {"route": route_used})

            # Update running summary with the exchange
            await self.context.update_summary_from_exchange(
                user_input, response_text, self.router.local_llm
            )

            execution_time = time.time() - start_time

            return {
                "type": "simple_task",
                "response": response_text,
                "execution_details": {
                    "route_used": route_used,
                    "execution_time": execution_time,
                    "estimated_cost": result.get("estimated_cost", 0),
                    "approach": "llm_managed_context",
                    "consultation_metadata": result.get("consultation_metadata"),
                    "episodes_used": len(relevant_episodes),
                    "user_profile_used": bool(user_profile_context),
                    "memories_used": len(memories),
                },
                "approach": "llm_managed_context",
            }

        except Exception as e:
            print(f"❌ LLM-managed context failed: {e}")
            # Return error response
            return {
                "type": "simple_task",
                "response": f"I'm having technical difficulties: {e}",
                "execution_details": {
                    "route_used": "error",
                    "execution_time": time.time() - start_time,
                    "estimated_cost": 0,
                    "approach": "error_fallback",
                    "error": str(e),
                },
                "approach": "error_fallback",
            }

    def _build_context_summary(self) -> str:
        """Build comprehensive conversation context for external LLM calls."""
        if not self.task_history:
            return ""

        context_parts = []

        # Start with user identification if available
        if self.context.user_name:
            context_parts.append("=== CONVERSATION CONTEXT ===")
            context_parts.append(f"User: {self.context.user_name}")
        else:
            context_parts.append("=== CONVERSATION CONTEXT ===")

        # Add session information
        context_parts.append(f"Session: {self.session_id}")
        context_parts.append(f"Total interactions: {len(self.task_history)}")

        # Current topic from running summary if available
        summary = self.context.get_or_create_summary()
        if not summary.is_empty():
            current_summary = summary.get_summary()
            context_parts.append(f"Current context: {current_summary[:100]}...")

        context_parts.append("") # Empty line for separation

        # Build comprehensive conversation summary
        # For recent conversations (last 10 exchanges), include full context
        recent_exchanges = min(10, len(self.task_history))

        if recent_exchanges > 0:
            context_parts.append("=== RECENT CONVERSATION ===")

            for i, task_record in enumerate(self.task_history[-recent_exchanges:]):
                exchange_num = len(self.task_history) - recent_exchanges + i + 1
                user_input = task_record["user_input"]
                response = task_record["result"].get("response", "No response provided")
                route = task_record["result"].get("execution_details", {}).get("route_used", "unknown")

                # Format exchange clearly
                context_parts.append(f"Exchange {exchange_num}:")
                context_parts.append(f"  User: {user_input}")
                context_parts.append(f"  Assistant ({route}): {response}")
                context_parts.append("") # Empty line between exchanges

        # If we have older history, provide a summary
        older_exchanges = len(self.task_history) - recent_exchanges
        if older_exchanges > 0:
            context_parts.append("=== EARLIER CONVERSATION ===")
            context_parts.append(f"({older_exchanges} earlier exchanges covering various topics)")

        return "\n".join(context_parts)

    async def _store_experience(self, user_input: str, result: dict[str, Any], user_id: str | None = None) -> None:
        """Store the task experience in memory with user_id support."""
        try:
            if self.memory_controller:
                # Use three-tier memory system with user_id support
                from .memory.models import MemoryChunk, MemoryTier, MemoryType

                # Create memory chunk for the experience
                experience_text = f"User: {user_input}\nResponse: {result.get('response', '')}"
                metadata = {
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session_id,
                    "route_used": result.get("execution_details", {}).get("route_used", "unknown"),
                    "user_input": user_input,
                    "response": result.get("response", ""),
                    "approach": result.get("approach", "unknown")
                }

                # Add user_id to metadata if provided
                if user_id:
                    metadata["interaction_user_id"] = user_id

                chunk = MemoryChunk(
                    text=experience_text,
                    memory_type=MemoryType.CONVERSATION,
                    metadata=metadata
                )

                # Store in USER tier with user_id (implements USER<id> prefix)
                await self.memory_controller.store(
                    chunk=chunk,
                    tier=MemoryTier.USER,
                    user_id=user_id  # This implements the USER<id> prefix as specified
                )

                logger.debug(f"Stored experience in three-tier memory for user: {user_id or 'default'}")

            else:
                # Fallback to simple vector store
                await self.vector_store.store_memory(
                    content=f"User: {user_input}\nResponse: {result.get('response', '')}",
                    memory_type="conversation",
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "session_id": self.session_id,
                        "user_id": user_id or "default",
                        "route_used": result.get("execution_details", {}).get("route_used", "unknown")
                    }
                )
                logger.debug(f"Stored experience in simple memory for user: {user_id or 'default'}")

        except Exception as e:
            logger.error(f"Failed to store experience: {e}")
            # Don't raise - memory storage failures shouldn't break conversation

    async def _maybe_reflect(self, user_input: str, result: dict[str, Any]) -> None:
        """Optionally perform reflection on the completed task."""
        # This logic will be moved from orchestrator.py

    async def _manage_memory(self) -> None:
        """Perform memory management tasks."""
        # This logic will be moved from orchestrator.py

    async def get_status(self) -> dict[str, Any]:
        """Get current entity status and diagnostics."""

        router_health = await self.router.health_check()

        # Get memory stats based on system type
        if self.memory_controller:
            memory_stats = await self.memory_controller.get_stats()
        else:
            memory_count = await self.vector_store.get_memory_count()
            memory_stats = {"total_memories": memory_count}

        return {
            "entity_name": self.__class__.__name__,
            "session_id": self.session_id,
            "tasks_completed": len(self.task_history),
            "memory_system": "three_tier" if self.memory_controller else "simple",
            "memory_stats": memory_stats,
            "router_health": router_health,
            "conversation_context": self.context.get_context_summary(),
            "identity_path": str(self.IDENTITY_PATH),
        }

    async def reset_memory(self) -> None:
        """Reset memory while preserving entity learning."""
        print(f"🗑️ Resetting memory for {self.__class__.__name__}")

        # Reset user profiles
        profiles_deleted = await self.user_profile_store.reset_all_profiles()
        print(f"🗑️ Reset {profiles_deleted} user profiles")

        # Reset conversation context
        self.context = ConversationContext(self.identity_config)
        print("✅ Conversation context reset")

        # Handle memory reset based on system type
        if self.memory_controller:
            await self.vector_store.reset_all()
            self.memory_controller = MemoryController()
            print("✅ Three-tier memory system reinitialized")
        else:
            await self.vector_store.reset_all()
            print("✅ Vector store reset complete")

        # Clear task history
        self.task_history.clear()
        print("✅ Task history cleared")

        time.sleep(0.5)  # Ensure database operations complete
        print("✅ Memory reset complete")
