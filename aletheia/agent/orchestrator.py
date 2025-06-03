"""Main orchestrator for the Aletheia thinking agent."""

import asyncio
import re
import traceback
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional
import time

from ..config import config
from ..identity.loader import load_identity_config, get_validation_config
from ..llm.router import LLMRouter, TaskContext
from ..memory.summariser import MemorySummariser
from ..memory.vector_store import VectorStore
from ..memory.hierarchical_store import HierarchicalMemoryStore
from ..memory.user_profile_store import UserProfileStore
from ..processing.config import get_processor_config
from .context_manager import ConversationContext
from .planner import Plan, SubTask, TaskPlanner
from .reflexion import ReflectionEngine


class AletheiaAgent:
    """Main orchestrator for the Aletheia thinking agent."""

    def __init__(self) -> None:
        """Initialize the Aletheia agent."""

        print("🚀 Initializing Aletheia agent...")

        # Suppress asyncio task exceptions from external API clients
        warnings.filterwarnings("ignore", message=".*AsyncHttpxClientWrapper.*", category=Warning)

        # Set a custom exception handler for asyncio to suppress background task errors
        def exception_handler(loop, context):
            exception = context.get("exception")
            if exception and "AsyncHttpxClientWrapper" in str(exception):
                # Silently ignore these compatibility issues
                return
            # For other exceptions, use default handling
            loop.default_exception_handler(context)

        # Apply the exception handler to current event loop if available
        try:
            loop = asyncio.get_event_loop()
            loop.set_exception_handler(exception_handler)
        except RuntimeError:
            # No event loop running yet, that's fine
            pass

        # Initialize agent components
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.task_history: list[dict[str, Any]] = []

        # Load identity configuration
        self.identity_config = load_identity_config()
        self.validation_config = get_validation_config()
        
        # Load scientific routing configuration
        self.scientific_config = get_processor_config("scientific_routing").parameters

        # Initialize conversation context manager
        self.context = ConversationContext(self.identity_config)

        # Initialize components
        self.vector_store = VectorStore()
        self.router = LLMRouter()
        self.planner = TaskPlanner(self.router)
        self.reflection_engine = ReflectionEngine(self.router, self.vector_store)
        self.memory_summariser = MemorySummariser(self.vector_store)
        
        # Initialize user profile storage
        self.user_profile_store = UserProfileStore()
        
        # Initialize hierarchical memory if enabled
        if config.use_hierarchical_memory:
            self.hierarchical_memory = HierarchicalMemoryStore(self.vector_store)
            print("🧠 Using hierarchical memory system")
        else:
            self.hierarchical_memory = None
            print("💾 Using simple memory system")

        print("✅ Aletheia agent initialized")

    async def think(self, user_input: str) -> dict[str, Any]:
        """Main thinking loop for processing user input."""

        print(f"\n🧠 Processing: {user_input[:100]}{'...' if len(user_input) > 100 else ''}")

        start_time = datetime.now()

        # Update conversation context
        self.context.update_from_input(user_input)

        try:
            # Step 0: Extract and store user-provided information
            user_name = self.context.user_name
            is_providing_info = False
            
            if user_name:
                # Check if user is providing information vs asking questions
                is_providing_info = self.user_profile_store.extractor.is_information_providing(user_input)
                
                if is_providing_info:
                    print("📊 Detected user providing information - extracting data...")
                    await self.user_profile_store.update_user_data(
                        user_name, 
                        user_input, 
                        context=f"Session {self.session_id}, Task #{len(self.task_history) + 1}"
                    )
                
                # Check if this is a data query (only if not providing info)
                elif await self.user_profile_store.is_data_query(user_input):
                    print("🔍 Detected user data query - providing profile summary...")
                    summary = await self.user_profile_store.get_user_data_summary(user_name)
                    
                    return {
                        "type": "user_data_query",
                        "response": summary,
                        "execution_details": {
                            "route_used": "user_profile",
                            "execution_time": (datetime.now() - start_time).total_seconds(),
                            "estimated_cost": 0,
                            "data_source": "user_profile_store"
                        },
                        "approach": "user_data_retrieval",
                        "meta": {
                            "processing_time": (datetime.now() - start_time).total_seconds(),
                            "session_id": self.session_id,
                            "task_id": len(self.task_history) + 1,
                            "user_data_query": True
                        }
                    }

            # Step 1: Retrieve relevant memories for better context
            relevant_memories = await self._retrieve_relevant_memories(user_input)

            # Step 2: Determine if task needs planning
            needs_planning = self.context.should_plan_task(user_input)
            
            # Override planning for scientific/technical topics that should go to external LLM
            # Check if this is a scientific/technical question that should use external LLM instead of planning
            scientific_keywords = self.scientific_config.get("scientific_keywords", [])
            
            user_input_lower = user_input.lower()
            is_scientific_query = any(keyword in user_input_lower for keyword in scientific_keywords)
            
            # If it's a scientific query with empty memory, prefer external LLM over planning
            if is_scientific_query and len(relevant_memories) == 0:
                needs_planning = False
                print("🔬 Scientific query with empty memory - routing to external LLM instead of planning")

            if needs_planning:
                # Complex task - use planning approach
                result = await self._handle_complex_task(user_input, relevant_memories)
            else:
                # Simple task - direct execution
                result = await self._handle_simple_task(user_input, relevant_memories)

            # Step 3: Store experience in memory
            await self._store_experience(user_input, result)

            # Step 4: Optional reflection
            if config.reflection_enabled and needs_planning:  # Only reflect on complex tasks
                await self._maybe_reflect(user_input, result)

            # Step 5: Memory management
            await self._manage_memory()

            # Track task in history
            task_record = {
                "timestamp": start_time.isoformat(),
                "user_input": user_input,
                "result": result,
                "session_id": self.session_id,
                "conversation_context": self.context.get_context_summary(),
            }
            self.task_history.append(task_record)

            # Add response to context
            response = result.get("response", "")
            self.context.add_response(response, result.get("execution_details"))

            # Add timing information
            result["meta"] = {
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "session_id": self.session_id,
                "task_id": len(self.task_history),
                "relevant_memories_count": len(relevant_memories),
                "used_planning": needs_planning,
                "conversation_context": self.context.get_context_summary(),
            }

            return result

        except Exception as e:
            error_result = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now().isoformat(),
                "user_input": user_input,
            }

            print(f"❌ Error processing task: {e}")
            return error_result

    async def _retrieve_relevant_memories(self, user_input: str) -> list[dict[str, Any]]:
        """Retrieve relevant memories for context."""

        try:
            # Enhanced query transformation for better memory matching
            query_for_search = user_input
            
            # Special handling for identity/name questions
            identity_keywords = [
                "кто ты", "кто я", "who am i", "who are you", "напомни", "remind",
                "мое имя", "my name", "как меня зовут", "what's my name"
            ]
            
            user_input_lower = user_input.lower()
            is_identity_query = any(keyword in user_input_lower for keyword in identity_keywords)
            
            if is_identity_query:
                # For identity queries, search for introduction/name related content
                if any(word in user_input_lower for word in ["кто я", "who am i", "меня зовут", "my name", "мое имя"]):
                    query_for_search = "меня зовут имя name introduction знакомство"
                    print(f"🔍 Identity query detected, using enhanced search: '{query_for_search}'")
                elif any(word in user_input_lower for word in ["кто ты", "who are you"]):
                    query_for_search = "Алетейя Aletheia agent агент introduction представление"
                    print(f"🔍 Agent identity query, using enhanced search: '{query_for_search}'")
            
            # Use hierarchical memory if available
            if self.hierarchical_memory:
                memories = await self.hierarchical_memory.search_memories(
                    query=query_for_search,
                    n_results=5,  # Get more for identity queries
                )
            else:
                # Fallback to simple vector store
                memories = await self.vector_store.search_memories(
                    query=query_for_search,
                    n_results=7,  # Increased from 5 for better coverage
                )

            if memories:
                print(f"📚 Retrieved {len(memories)} relevant memories")
                
                # Debug: show what memories were retrieved
                for i, memory in enumerate(memories[:3]):  # Show first 3 for debugging
                    content_preview = memory.get('content', '')[:100]
                    distance = memory.get('distance', 'unknown')
                    print(f"  Memory {i+1}: Distance={distance:.3f}, Content='{content_preview}...'")
                
                # For identity queries, be more permissive with distance threshold
                distance_threshold = self.scientific_config.get("memory_relevance_threshold", 0.8) if is_identity_query else self.scientific_config.get("distance_threshold", 0.7)
                
                # Filter out memories that are too distant (less relevant)
                # This helps prevent stale/irrelevant context contamination
                filtered_memories = []
                for memory in memories:
                    distance = memory.get('distance', 1.0)
                    # Only include memories with similarity > threshold
                    if distance < distance_threshold:
                        filtered_memories.append(memory)
                    else:
                        print(f"  🔍 Filtered out distant memory (distance={distance:.3f})")
                
                if len(filtered_memories) != len(memories):
                    print(f"📚 After filtering: {len(filtered_memories)} relevant memories")
                
                return filtered_memories

        except Exception as e:
            print(f"⚠️  Error retrieving memories: {e}")

        return []

    async def _handle_complex_task(
        self,
        user_input: str,
        relevant_memories: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Handle complex tasks that require planning."""

        print("🎯 Handling complex task with planning...")

        # Create a plan with memory context
        enhanced_input = user_input
        if relevant_memories:
            memory_context = self._format_memories_for_context(relevant_memories)
            enhanced_input = f"{user_input}\n\n{memory_context}"
        
        plan = await self.planner.create_plan(enhanced_input)

        if not plan:
            # Fallback to simple task handling
            print("⚠️  Planning failed, falling back to simple execution")
            return await self._handle_simple_task(user_input, relevant_memories)

        # Execute the plan
        execution_results = []
        completed_tasks = []

        print(f"📋 Executing plan with {len(plan.subtasks)} sub-tasks...")

        for i in range(len(plan.subtasks)):
            # Get next task to execute
            next_task = self.planner.get_next_task(plan, completed_tasks)

            if not next_task:
                break

            print(f"🔄 Executing: {next_task.description}")

            # Execute sub-task with memory context
            subtask_result = await self._execute_subtask(next_task, relevant_memories)
            execution_results.append({
                "subtask": next_task,
                "result": subtask_result,
            })

            completed_tasks.append(next_task.id)

        # Synthesize final result with memory context
        final_result = await self._synthesize_plan_results(
            user_input, plan, execution_results, relevant_memories
        )

        return {
            "type": "complex_task",
            "response": final_result,
            "plan": {
                "original_task": plan.original_task,
                "subtasks_completed": len(completed_tasks),
                "total_subtasks": len(plan.subtasks),
                "execution_results": execution_results,
            },
            "approach": "planning",
            "execution_details": {
                "memories_used": len(relevant_memories),
                "planning_enhanced": bool(relevant_memories),
            },
        }

    async def _handle_simple_task(
        self,
        user_input: str,
        relevant_memories: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Handle simple tasks with enhanced LLM-managed context approach."""
        
        start_time = time.time()
        
        # Check if this is a scientific/technical query for forced external routing
        scientific_keywords = self.scientific_config.get("scientific_keywords", [])
        
        user_input_lower = user_input.lower()
        is_scientific_query = any(keyword in user_input_lower for keyword in scientific_keywords)
        
        # Get user name for context
        user_name = self.context.current_user_id
        
        # Check if we should retrieve episodes for additional context
        should_retrieve = self.context.should_retrieve_episodes(user_input)
        relevant_episodes = []
        
        if should_retrieve:
            relevant_episodes = self.context.search_relevant_episodes(user_input, max_episodes=3)
            print(f"📚 Retrieved {len(relevant_episodes)} relevant episodes for context")
        
        # Build enhanced context prompt with running summary
        system_prompt = self.identity_config.get("llm_instructions", "You are Aletheia, a helpful AI assistant.")
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
            # Check if the current query is related to personal data
            personal_data_keywords = [
                "вес", "рост", "жир", "процент", "кг", "см", "данные", "профиль", "информация",
                "тренировк", "диет", "питание", "похуд", "цел", "план", "здоровье",
                "weight", "height", "fat", "data", "profile", "information", "training", 
                "diet", "nutrition", "goal", "plan", "health", "fitness"
            ]
            
            input_lower = user_input.lower()
            is_personal_query = any(keyword in input_lower for keyword in personal_data_keywords)
            
            if is_personal_query:
                user_profile_context = await self.user_profile_store.get_user_data_context(user_name)
                if user_profile_context:
                    context_prompt = context_prompt.replace(
                        "### CONVERSATION",
                        f"### USER PROFILE\n{user_profile_context}\n\n### CONVERSATION"
                    )
                    print("📊 Added user profile context (relevant to query)")
        
        print("⚡ Handling simple task with LLM-managed context...")
        
        # Use the new structured generation approach
        try:
            # Force external routing for complex scientific topics with empty memory
            if is_scientific_query and len(relevant_memories) == 0 and any(word in user_input_lower for word in self.scientific_config.get("complex_query_indicators", [])):
                print("🔬 Forcing external consultation for complex scientific topic")
                
                # Build enhanced context for external LLM
                enhanced_context = self._build_context_summary()
                
                task_context = TaskContext(
                    prompt=user_input,
                    max_tokens=1024,
                    requires_deep_reasoning=True,
                    conversation_context=enhanced_context,
                    user_name=user_name,
                    session_context={
                        "session_id": self.session_id,
                        "interaction_count": self.context.interaction_count,
                        "language": self.context.last_user_language
                    }
                )
                
                external_result = await self.router.execute_task(task_context)
                route_used = "external_forced"
                response_text = external_result.get("result", "")
                
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
                        "estimated_cost": external_result.get("estimated_cost", 0),
                        "approach": "llm_managed_context",
                        "consultation_metadata": external_result.get("consultation_metadata"),
                        "episodes_used": len(relevant_episodes),
                        "user_profile_used": bool(user_profile_context),
                    },
                    "approach": "llm_managed_context",
                }
            
            # Use local LLM with structured CoT generation
            print("💻 Using local LLM with Chain-of-Thought reasoning")
            
            raw_response = await self.router.local_llm.generate(
                prompt=context_prompt,
                max_tokens=1024,
                temperature=0.7,
                system_prompt=""  # System prompt is already in the context_prompt
            )
            
            # Extract Chain-of-Thought and final response
            cot_reasoning, response_text = self.context.extract_cot_and_response(raw_response)
            
            print(f"🧠 CoT reasoning: {cot_reasoning[:100]}..." if cot_reasoning else "🧠 No CoT structure detected")
            
            route_used = "local_cot"
            
            # Add to episodes storage
            self.context.add_episode(user_input, response_text, {
                "route": route_used,
                "cot_reasoning": cot_reasoning,
                "episodes_used": len(relevant_episodes)
            })
            
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
                    "estimated_cost": 0,
                    "approach": "llm_managed_context",
                    "cot_reasoning": cot_reasoning,
                    "raw_response": raw_response,
                    "episodes_used": len(relevant_episodes),
                    "user_profile_used": bool(user_profile_context),
                },
                "approach": "llm_managed_context",
            }
                
        except Exception as e:
            print(f"❌ LLM-managed context failed: {e}")
            # Fallback to external LLM
            enhanced_context = self._build_context_summary()
            
            task_context = TaskContext(
                prompt=user_input,
                max_tokens=1024,
                requires_deep_reasoning=True,
                conversation_context=enhanced_context,
                user_name=user_name,
                session_context={
                    "session_id": self.session_id,
                    "interaction_count": self.context.interaction_count,
                    "language": self.context.last_user_language
                }
            )
            
            external_result = await self.router.execute_task(task_context)
            execution_time = time.time() - start_time
            
            # Add to episodes storage
            response_text = external_result.get("result", "")
            self.context.add_episode(user_input, response_text, {"route": "external_fallback"})
            
            # Update running summary
            await self.context.update_summary_from_exchange(
                user_input, response_text, self.router.local_llm
            )
            
            return {
                "type": "simple_task",
                "response": response_text,
                "execution_details": {
                    "route_used": "external_fallback",
                    "execution_time": execution_time,
                    "estimated_cost": external_result.get("estimated_cost", 0),
                    "approach": "llm_managed_context",
                    "error": str(e),
                    "consultation_metadata": external_result.get("consultation_metadata"),
                    "episodes_used": len(relevant_episodes),
                    "user_profile_used": bool(user_profile_context),
                },
                "approach": "llm_managed_context",
            }

    def _build_context_summary(self) -> str:
        """Build comprehensive conversation context for external LLM calls."""
        if not self.task_history:
            return ""
        
        context_parts = []
        
        # Start with user identification if available
        if self.context.user_name:
            context_parts.append(f"=== CONVERSATION CONTEXT ===")
            context_parts.append(f"User: {self.context.user_name}")
        else:
            context_parts.append(f"=== CONVERSATION CONTEXT ===")
        
        # Add session information
        context_parts.append(f"Session: {self.session_id}")
        context_parts.append(f"Total interactions: {len(self.task_history)}")
        
        # Current topic if available
        if self.context.current_topic:
            context_parts.append(f"Current topic: {self.context.current_topic}")
        
        context_parts.append("") # Empty line for separation
        
        # Build comprehensive conversation summary
        # For recent conversations (last 10 exchanges), include full context
        # For older ones, include condensed summaries
        
        recent_exchanges = min(10, len(self.task_history))
        
        if recent_exchanges > 0:
            context_parts.append("=== RECENT CONVERSATION ===")
            
            for i, task_record in enumerate(self.task_history[-recent_exchanges:]):
                exchange_num = len(self.task_history) - recent_exchanges + i + 1
                user_input = task_record['user_input']
                response = task_record['result'].get('response', 'No response provided')
                route = task_record['result'].get('execution_details', {}).get('route_used', 'unknown')
                
                # Format exchange clearly
                context_parts.append(f"Exchange {exchange_num}:")
                context_parts.append(f"  User: {user_input}")
                context_parts.append(f"  Assistant ({route}): {response}")
                context_parts.append("") # Empty line between exchanges
        
        # If we have older history, provide a summary
        older_exchanges = len(self.task_history) - recent_exchanges
        if older_exchanges > 0:
            context_parts.append(f"=== EARLIER CONVERSATION ===")
            context_parts.append(f"({older_exchanges} earlier exchanges covering various topics)")
            
            # Extract key topics from earlier exchanges
            earlier_topics = []
            for task_record in self.task_history[:-recent_exchanges]:
                conv_context = task_record.get('conversation_context', {})
                topic = conv_context.get('current_topic')
                if topic and topic not in earlier_topics:
                    earlier_topics.append(topic)
            
            if earlier_topics:
                context_parts.append(f"Topics discussed: {', '.join(earlier_topics[:5])}")
            
            context_parts.append("")
        
        # Add current context indicators
        current_input = ""
        if self.context.conversation_history:
            for entry in reversed(self.context.conversation_history):
                if entry["type"] == "user_input":
                    current_input = entry["content"]
                    break
        
        # Detect if current question is a reference/continuation
        if current_input:
            has_references = any(pronoun in current_input.lower() for pronoun in 
                               ["он", "она", "оно", "они", "его", "её", "их", "им", "ей", "ему", "ими", "ним", "ней", "нём", 
                                "это", "то", "такое", "этого", "того", "it", "that", "this", "them", "those"])
            
            implicit_continuation_patterns = [
                r'\bа\s+если\b', r'\bа\s+что\b', r'^\s*(а|но|и)\s+',
                r'\bкогда\s+(это|то)\b', r'\bгде\s+(это|то)\b', r'\bпочему\s+(это|то)\b'
            ]
            has_implicit_continuation = any(re.search(pattern, current_input.lower()) for pattern in implicit_continuation_patterns)
            
            if has_references or has_implicit_continuation:
                context_parts.append("=== CONTEXT NOTE ===")
                context_parts.append("The user's current question contains references to previous conversation.")
                context_parts.append("Please maintain continuity and understand what they're referring to.")
                context_parts.append("")
        
        context_parts.append("=== END CONTEXT ===")
        context_parts.append("")
        
        full_context = "\n".join(context_parts)
        
        # With 128k context window, we can be generous, but still reasonable
        # Limit to ~8000 characters to leave room for the actual question and response
        if len(full_context) > 8000:
            # If too long, keep the recent exchanges and trim older history
            context_parts_trimmed = []
            context_parts_trimmed.append("=== CONVERSATION CONTEXT ===")
            if self.context.user_name:
                context_parts_trimmed.append(f"User: {self.context.user_name}")
            context_parts_trimmed.append(f"Total interactions: {len(self.task_history)} (showing recent)")
            if self.context.current_topic:
                context_parts_trimmed.append(f"Current topic: {self.context.current_topic}")
            context_parts_trimmed.append("")
            
            # Keep last 8 exchanges in full detail
            recent_exchanges = min(8, len(self.task_history))
            context_parts_trimmed.append("=== RECENT CONVERSATION ===")
            
            for i, task_record in enumerate(self.task_history[-recent_exchanges:]):
                exchange_num = len(self.task_history) - recent_exchanges + i + 1
                user_input = task_record['user_input']
                response = task_record['result'].get('response', 'No response provided')
                route = task_record['result'].get('execution_details', {}).get('route_used', 'unknown')
                
                context_parts_trimmed.append(f"Exchange {exchange_num}:")
                context_parts_trimmed.append(f"  User: {user_input}")
                context_parts_trimmed.append(f"  Assistant ({route}): {response}")
                context_parts_trimmed.append("")
            
            if has_references or has_implicit_continuation:
                context_parts_trimmed.append("=== CONTEXT NOTE ===")
                context_parts_trimmed.append("The user's current question contains references to previous conversation.")
                context_parts_trimmed.append("Please maintain continuity and understand what they're referring to.")
                context_parts_trimmed.append("")
            
            context_parts_trimmed.append("=== END CONTEXT ===")
            context_parts_trimmed.append("")
            
            full_context = "\n".join(context_parts_trimmed)
        
        return full_context

    async def _execute_subtask(
        self,
        subtask: SubTask,
        relevant_memories: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Execute a single sub-task."""

        # Build enhanced context with memories
        conversation_context = self._build_context_summary()
        if relevant_memories:
            memory_context = self._format_memories_for_context(relevant_memories)
            conversation_context = f"{conversation_context}\n\n=== RELEVANT MEMORIES FOR SUBTASK ===\n{memory_context}\n"

        # Create context for subtask
        task_context = TaskContext(
            prompt=subtask.description,
            max_tokens=600,
            requires_deep_reasoning=subtask.requires_external_llm,
            cost_sensitive=not subtask.requires_external_llm,
            conversation_context=conversation_context,
            user_name=self.context.user_name,
            session_context={
                "session_id": self.session_id,
                "interaction_count": self.context.interaction_count,
                "language": self.context.last_user_language
            }
        )

        # Execute subtask
        result = await self.router.execute_task(task_context)

        return result

    async def _synthesize_plan_results(
        self,
        original_task: str,
        plan: Plan,
        execution_results: list[dict[str, Any]],
        relevant_memories: list[dict[str, Any]]
    ) -> str:
        """Synthesize results from plan execution into final response."""

        # Compile all sub-task results
        results_text = ""
        for i, exec_result in enumerate(execution_results, 1):
            subtask = exec_result["subtask"]
            result = exec_result["result"]

            results_text += f"\n{i}. {subtask.description}\n"
            results_text += f"Result: {result.get('result', 'No result')}\n"

        # Include memory context in synthesis if available
        memory_context_text = ""
        if relevant_memories:
            memory_context_text = f"\n\nRelevant Past Experiences:\n{self._format_memories_for_context(relevant_memories)}"

        synthesis_prompt = f"""I need to synthesize the results from executing a complex task plan.

Original Task: {original_task}

Plan Execution Results:
{results_text}{memory_context_text}

Please provide a comprehensive, well-structured response that:
1. Directly answers the original question/task
2. Integrates insights from all sub-task results
3. Incorporates relevant information from past experiences when applicable
4. Presents information in a logical, coherent manner
5. Highlights key findings or recommendations
6. Addresses any limitations or areas for further exploration

Focus on creating a cohesive response that feels like a complete answer to the original task."""

        # Build enhanced conversation context for synthesis
        conversation_context = self._build_context_summary()
        if relevant_memories:
            memory_context = self._format_memories_for_context(relevant_memories)
            conversation_context = f"{conversation_context}\n\n=== SYNTHESIS MEMORIES ===\n{memory_context}\n"

        synthesis_context = TaskContext(
            prompt=synthesis_prompt,
            max_tokens=1200,
            requires_deep_reasoning=True,
            conversation_context=conversation_context,
            user_name=self.context.user_name,
            session_context={
                "session_id": self.session_id,
                "interaction_count": self.context.interaction_count,
                "language": self.context.last_user_language
            }
        )

        synthesis_result = await self.router.execute_task(synthesis_context)

        return synthesis_result.get("result", "Unable to synthesize results")

    async def _store_experience(self, user_input: str, result: dict[str, Any]) -> None:
        """Store the task experience in memory."""

        try:
            # Re-enabled memory storage now that conversation continuity is improved
            print("💾 Storing conversation experience in memory...")
            
            # Create experience summary
            experience = f"Task: {user_input}\n"
            experience += f"Approach: {result.get('approach', 'unknown')}\n"
            experience += f"Response: {result.get('response', 'No response')[:500]}...\n"

            # Add execution details
            execution_details = result.get("execution_details", {})
            route_used = execution_details.get("route_used", "unknown")
            
            experience += f"Route: {route_used}\n"
            experience += f"Cost: ${execution_details.get('estimated_cost', 0):.4f}\n"
            
            # Add consultation metadata if available (for external LLM tracking)
            consultation_meta = execution_details.get("consultation_metadata", {})
            if consultation_meta:
                experience += f"External LLM: {consultation_meta.get('provider', 'unknown')}\n"
                experience += f"Model: {consultation_meta.get('model', 'unknown')}\n"

            # Determine detailed source information
            llm_source = "local"
            llm_provider = "phi3_medium"  # Default local model
            llm_model = "phi-3-medium-4k-instruct"
            
            if "external" in route_used:
                llm_source = "external"
                llm_provider = consultation_meta.get("provider", "unknown_external")
                llm_model = consultation_meta.get("model", "unknown_model")
            elif route_used == "local":
                llm_source = "local"
                # Keep default local values

            # Prepare metadata with proper types (ChromaDB only accepts str, int, float, bool)
            metadata = {
                "session_id": self.session_id,
                "approach": result.get("approach", "unknown"),
                "task_type": result.get("type", "unknown"),
                "user_input_length": len(user_input),
                "user_name": self.context.user_name or "unknown",
                "language": self.context.last_user_language,
                "current_topic": self.context.current_topic,
                "route_used": route_used,
                "execution_time": result.get("meta", {}).get("processing_time", 0.0),
                # Enhanced source tracking for multi-LLM architecture
                "llm_source": llm_source,  # "local" or "external"
                "llm_provider": llm_provider,  # "phi3_medium", "anthropic", "openai", etc.
                "llm_model": llm_model,  # specific model name
                "estimated_cost": float(execution_details.get("estimated_cost", 0.0)),
                "local_confidence": execution_details.get("local_confidence", "unknown"),
            }

            # Enhanced importance scoring based on source and complexity
            importance_score = self._calculate_memory_importance(
                user_input=user_input,
                route_used=route_used,
                llm_source=llm_source,
                execution_details=execution_details
            )
            
            # Use hierarchical memory if available
            if self.hierarchical_memory:
                await self.hierarchical_memory.store_memory(
                    content=experience,
                    memory_type="task_experience",
                    metadata=metadata,
                    importance_score=importance_score,
                )
            else:
                # Fallback to simple vector store
                await self.vector_store.store_memory(
                    content=experience,
                    memory_type="task_experience",
                    metadata=metadata,
                )

        except Exception as e:
            print(f"⚠️  Error storing experience: {e}")
    
    def _calculate_memory_importance(
        self,
        user_input: str,
        route_used: str,
        llm_source: str,
        execution_details: dict[str, Any]
    ) -> float:
        """Calculate importance score for memory entry with enhanced scoring for external LLMs."""
        
        importance_score = 0.3  # Base score (reduced from 0.5)
        
        # Input complexity factor
        input_length = len(user_input)
        if input_length > 200:
            importance_score += 0.3
        elif input_length > 100:
            importance_score += 0.2
        elif input_length > 50:
            importance_score += 0.1
        
        # LLM source factor (external much higher value)
        if llm_source == "external":
            importance_score += 0.5  # Significant boost for external LLM results
            
            # Additional boost based on estimated cost (higher cost = more complex)
            cost = execution_details.get("estimated_cost", 0.0)
            if cost > 0.01:  # High cost query
                importance_score += 0.2
            elif cost > 0.005:  # Medium cost query  
                importance_score += 0.1
                
        elif llm_source == "local":
            # Local results get smaller boost
            confidence = execution_details.get("local_confidence", "unknown")
            if confidence == "high":
                importance_score += 0.1
            elif confidence == "medium":
                importance_score += 0.05
        
        # Route complexity factor
        if "external_fallback" in route_used:
            importance_score += 0.3  # Fallback situations are important to remember
        elif "planning" in route_used:
            importance_score += 0.2  # Complex planning tasks
        
        # Approach factor
        approach = execution_details.get("approach", "")
        if approach == "planning":
            importance_score += 0.2
        
        # Cap at 1.0 to prevent extreme scores
        return min(importance_score, 1.0)

    async def _maybe_reflect(self, user_input: str, result: dict[str, Any]) -> None:
        """Optionally perform reflection on the completed task."""

        try:
            # Determine if we should reflect
            task_complexity = self._estimate_task_complexity(user_input, result)

            if await self.reflection_engine.should_reflect(task_complexity):
                response_text = result.get("response", "")
                reflection = await self.reflection_engine.reflect_on_task(
                    task=user_input,
                    response=response_text,
                    context=result,
                )

                if reflection and reflection.confidence_score < 0.6:
                    print(f"⚠️  Low confidence reflection (score: {reflection.confidence_score:.2f})")

                    # Create improvement plan for low confidence tasks
                    await self.reflection_engine.create_improvement_plan(reflection)

        except Exception as e:
            print(f"⚠️  Error during reflection: {e}")

    def _estimate_task_complexity(self, user_input: str, result: dict[str, Any]) -> float:
        """Estimate the complexity of a completed task."""

        complexity_factors = []

        # Input complexity
        input_length = len(user_input.split())
        complexity_factors.append(min(input_length / 50.0, 1.0))

        # Approach complexity
        if result.get("approach") == "planning":
            complexity_factors.append(0.8)
        else:
            complexity_factors.append(0.3)

        # Execution details
        if "execution_details" in result:
            route = result["execution_details"].get("route_used")
            if route == "external":
                complexity_factors.append(0.7)
            else:
                complexity_factors.append(0.4)

        return sum(complexity_factors) / len(complexity_factors)

    async def _manage_memory(self) -> None:
        """Perform memory management tasks."""

        try:
            if self.hierarchical_memory:
                # Use hierarchical memory management (automatic tiering)
                # The hierarchical memory store handles its own management automatically
                # when new memories are stored, but we can also trigger it manually
                await self.hierarchical_memory._manage_memory_tiers()
            else:
                # Fallback to simple memory management
                # Check if summarization is needed (using local LLM as recommended by o3)
                if await self.memory_summariser.should_summarize():
                    print("🧠 Memory threshold reached - starting summarization...")
                    summary_id = await self.memory_summariser.summarize_and_compress(
                        delete_originals=True  # Enable cleanup as recommended by o3
                    )
                    if summary_id:
                        print(f"✅ Memory summarization completed: {summary_id}")
                    else:
                        print("ℹ️ Memory summarization skipped - not enough memories")

                # Cleanup old memories if needed (secondary safety net)
                memory_count = await self.vector_store.get_memory_count()
                if memory_count > config.max_memory_entries:
                    deleted = await self.vector_store.cleanup_old_memories()
                    if deleted > 0:
                        print(f"🗑️ Cleaned up {deleted} old memories (safety cleanup)")

        except Exception as e:
            print(f"⚠️ Error managing memory: {e}")

    async def start_background_tasks(self) -> None:
        """Start background tasks like periodic summarization (o3's nightly task implementation)."""
        print("🚀 Starting background tasks...")
        
        # Start periodic memory summarization (every 24 hours)
        asyncio.create_task(self.memory_summariser.run_periodic_summarization(interval_hours=24))
        print("📅 Started periodic memory summarization task")
        
        # TODO: Add other background tasks here (environment monitoring, health checks, etc.)

    async def get_status(self) -> dict[str, Any]:
        """Get current agent status and diagnostics."""

        router_health = await self.router.health_check()
        
        # Get memory stats based on system type
        if self.hierarchical_memory:
            memory_stats = await self.hierarchical_memory.get_memory_stats()
        else:
            memory_count = await self.vector_store.get_memory_count()
            memory_stats = {"total_memories": memory_count}
            
        # Add summarization statistics
        summarization_stats = await self.memory_summariser.get_summarization_stats()
        memory_stats.update({"summarization": summarization_stats})

        return {
            "session_id": self.session_id,
            "tasks_completed": len(self.task_history),
            "memory_system": "hierarchical" if self.hierarchical_memory else "simple",
            "memory_stats": memory_stats,
            "router_health": router_health,
            "conversation_context": self.context.get_context_summary(),
            "config": {
                "reflection_enabled": config.reflection_enabled,
                "max_memory_entries": config.max_memory_entries,
                "local_token_threshold": config.local_token_threshold,
                "use_hierarchical_memory": config.use_hierarchical_memory,
                "memory_summarization_threshold": config.memory_summarization_threshold,
            },
        }

    async def reset_memory(self) -> None:
        """Reset USER and ENV memory tiers while preserving CORE_SELF (Aletheia's learning)."""

        print("🗑️  Resetting user and environment memory (preserving core self-learning)...")
        
        # Reset user profiles (always safe to reset)
        profiles_deleted = await self.user_profile_store.reset_all_profiles()
        print(f"🗑️  Reset {profiles_deleted} user profiles")
        
        # Reset conversation context but keep identity config
        self.context = ConversationContext(self.identity_config)
        print("✅ Conversation context reset")
        
        # Handle memory reset based on system type
        if self.hierarchical_memory:
            # For hierarchical memory, we need selective reset
            # For now, we'll reset the entire vector store since hierarchical doesn't support tier-specific reset yet
            print("⚠️  Note: Hierarchical memory doesn't support selective reset yet - using full reset")
            await self.vector_store.reset_all()
            self.hierarchical_memory = HierarchicalMemoryStore(self.vector_store)
            print("✅ Hierarchical memory system reinitialized")
        else:
            # For simple vector store, reset everything (no tier support)
            await self.vector_store.reset_all()
            print("✅ Vector store reset complete")
        
        # Clear task history (this is session-specific, safe to reset)
        self.task_history.clear()
        print("✅ Task history cleared")
        
        # Force a small delay to ensure database operations complete
        time.sleep(0.5)
        
        print("✅ Memory reset complete (CORE_SELF preserved)")

    async def reset_all_memory(self) -> None:
        """Reset ALL memory including CORE_SELF (development/debugging only)."""
        
        # Check if complete memory reset is allowed
        if not config.allow_complete_memory_reset:
            print("🚫 Complete memory reset is disabled in production mode")
            print("💡 Use 'reset' to clear user/env memory while preserving core learning")
            return
        
        if not config.development_mode:
            print("⚠️  Complete memory reset is only allowed in development mode")
            return
        
        print("🚨 FULL MEMORY RESET - This will delete Aletheia's learned knowledge!")
        print("🚨 This should only be used during development!")
        
        # Complete reset of all systems
        await self.vector_store.reset_all()
        print("✅ Vector store completely reset")
        
        # If using hierarchical memory, reinitialize it after vector store reset
        if self.hierarchical_memory:
            self.hierarchical_memory = HierarchicalMemoryStore(self.vector_store)
            print("✅ Hierarchical memory system reinitialized")
        
        # Clear task history
        self.task_history.clear()
        print("✅ Task history cleared")
        
        # Reset user profiles
        profiles_deleted = await self.user_profile_store.reset_all_profiles()
        print(f"🗑️  Reset {profiles_deleted} user profiles")
        
        # Reset conversation context but keep identity config
        self.context = ConversationContext(self.identity_config)
        print("✅ Conversation context reset")
        
        # Force a small delay to ensure database operations complete
        time.sleep(0.5)
        
        print("✅ COMPLETE memory reset finished")

    async def _validate_factual_response(self, user_input: str, response_text: str) -> list[str]:
        """Validate a factual response for obvious accuracy issues using config."""
        issues = []
        
        response_lower = response_text.lower()
        user_input_lower = user_input.lower()
        
        # Water vapor confusion check
        water_vapor_config = self.validation_config.get("water_vapor_confusion", {})
        question_terms = water_vapor_config.get("question_terms", [])
        error_terms = water_vapor_config.get("error_terms", [])
        
        if any(term in user_input_lower for term in question_terms):
            if any(error in response_lower for error in error_terms):
                issues.append("confused_water_vapor_with_hydrogen")
        
        # Chemistry errors check
        chemistry_config = self.validation_config.get("chemistry_errors", {})
        context_terms = chemistry_config.get("context_terms", [])
        impossible_combinations = chemistry_config.get("impossible_combinations", [])
        
        if any(term in user_input_lower for term in context_terms):
            for combo in impossible_combinations:
                if all(term in response_lower for term in combo):
                    issues.append("impossible_chemical_process")
        
        # Contradiction pairs check
        contradiction_pairs = self.validation_config.get("contradiction_pairs", [])
        for positive_terms, negative_terms in contradiction_pairs:
            has_positive = any(term in response_lower for term in positive_terms)
            has_negative = any(term in response_lower for term in negative_terms)
            if has_positive and has_negative:
                issues.append("contradictory_statements")
        
        # Vague response check
        vague_indicators = self.validation_config.get("vague_indicators", [])
        vague_count = len([word for word in vague_indicators if word in response_lower])
        if vague_count > 3:
            issues.append("overly_vague_response")
        
        # Definition requirements check
        definition_config = self.validation_config.get("definition_requirements", {})
        question_patterns = definition_config.get("question_patterns", [])
        required_words = definition_config.get("required_words", [])
        
        if any(pattern in user_input_lower for pattern in question_patterns):
            if not any(word in response_lower for word in required_words):
                issues.append("no_definition_provided")
        
        return issues

    def _format_memories_for_context(self, memories: list[dict[str, Any]]) -> str:
        """Format a list of memories into a context string for LLM consumption."""
        if not memories:
            return ""
        
        context_parts = ["=== RELEVANT PAST EXPERIENCES ==="]
        context_parts.append("(Use these experiences to inform your response, but don't copy them verbatim)")
        context_parts.append("")
        
        for i, memory in enumerate(memories, 1):
            content = memory.get('content', 'No content')
            tier = memory.get('tier', 'unknown')
            distance = memory.get('distance', 1.0)
            relevance = 1.0 - distance  # Convert distance to relevance score
            metadata = memory.get('metadata', {})
            
            # Get source information
            llm_source = metadata.get('llm_source', 'unknown')
            llm_provider = metadata.get('llm_provider', 'unknown')
            llm_model = metadata.get('llm_model', 'unknown')
            importance = metadata.get('importance_score', 0.0)
            
            # Create source attribution
            if llm_source == "external":
                source_info = f"External LLM ({llm_provider})"
            elif llm_source == "local":
                source_info = f"Local LLM ({llm_provider})"
            else:
                source_info = f"Unknown source"
            
            # Extract key information from content
            if content.startswith("Task:"):
                # This is a task experience memory
                lines = content.split('\n')
                task_line = next((line for line in lines if line.startswith("Task:")), "")
                response_line = next((line for line in lines if line.startswith("Response:")), "")
                route_line = next((line for line in lines if line.startswith("Route:")), "")
                
                context_parts.append(f"{i}. [{tier.upper()}] Previous Experience (Importance: {importance:.2f}):")
                context_parts.append(f"   Source: {source_info}")
                context_parts.append(f"   {task_line}")
                
                # For data-related queries, show more of the response to capture specific information
                if any(keyword in task_line.lower() for keyword in ["данные", "data", "рост", "вес", "weight", "height", "жир", "fat", "кг", "см", "процент"]):
                    # Show more content for data queries (up to 500 characters)
                    context_parts.append(f"   {response_line[:500]}...")
                    context_parts.append(f"   ⚠️ KEY DATA: This memory may contain specific user information")
                else:
                    # Standard truncation for other queries
                    context_parts.append(f"   {response_line[:200]}...")
                
                if route_line:
                    context_parts.append(f"   {route_line}")
                context_parts.append(f"   Relevance to current query: {relevance:.2f}")
                
                # Add learning note for high-importance external memories
                if llm_source == "external" and importance > 0.7:
                    context_parts.append(f"   📝 Note: High-value external consultation - consider this knowledge carefully")
                
            else:
                # Other types of memories (summaries, key facts)
                context_parts.append(f"{i}. [{tier.upper()}] {source_info} (Importance: {importance:.2f}):")
                context_parts.append(f"   {content[:250]}...")
                context_parts.append(f"   Relevance: {relevance:.2f}")
            
            context_parts.append("")  # Empty line between memories
        
        context_parts.append("=== CONTEXT USAGE GUIDELINES ===")
        context_parts.append("• Use this information to enhance your understanding and provide better responses")
        context_parts.append("• If these experiences contain the answer, you may not need external consultation")
        context_parts.append("• Pay special attention to KEY DATA memories containing specific user information")
        context_parts.append("• Extract exact values (numbers, measurements) when available in memories")
        context_parts.append("• Maintain your natural conversational style while incorporating relevant insights")
        context_parts.append("• Higher importance scores indicate more valuable information")
        context_parts.append("=== END MEMORIES ===")
        context_parts.append("")
        
        return "\n".join(context_parts)


# Simple CLI interface for testing
async def main() -> None:
    """Simple CLI interface for testing the agent."""

    try:
        agent = AletheiaAgent()

        print("\n🤖 Aletheia Agent - Interactive Mode")
        print("Commands:")
        print("  'quit' - Exit")
        print("  'status' - Show diagnostics")
        print("  'reset' - Clear user/env memory (preserves core learning)")
        if config.allow_complete_memory_reset and config.development_mode:
            print("  'reset_all' - Clear ALL memory including core learning (dev only)")
        print("  'plan: <task>' - Force planning mode")
        print("  'reflect: <task>' - Force reflection on task")
        print("  'context' - Show conversation history")
        print("-" * 60)

        while True:
            try:
                user_input = input("\n🧑 You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() == "quit":
                    print("👋 Goodbye!")
                    break

                elif user_input.lower() == "status":
                    status = await agent.get_status()
                    print(f"\n📊 Agent Status: {status}")
                    continue

                elif user_input.lower() == "reset":
                    await agent.reset_memory()
                    continue

                elif user_input.lower() == "reset_all":
                    await agent.reset_all_memory()
                    continue

                elif user_input.lower() == "context":
                    print(f"\n📝 Conversation Context: {agent.context.get_context_summary()}")
                    print(f"Task History ({len(agent.task_history)} entries):")
                    for i, task in enumerate(agent.task_history[-5:], 1):  # Show last 5
                        print(f"{i}. {task['user_input'][:50]}... -> {task['result'].get('response', 'No response')[:50]}...")
                    continue

                elif user_input.lower().startswith("plan:"):
                    task_to_plan = user_input[5:].strip()
                    if task_to_plan:
                        print(f"🎯 Forcing planning mode for: {task_to_plan}")
                        # Override planning decision
                        relevant_memories = await agent._retrieve_relevant_memories(task_to_plan)
                        result = await agent._handle_complex_task(task_to_plan, relevant_memories)
                        print(f"\n🤖 Aletheia: {result.get('response', 'No response')}")
                        print(f"📋 Plan executed with {result.get('plan', {}).get('subtasks_completed', 0)} subtasks")
                    continue

                elif user_input.lower().startswith("reflect:"):
                    task_to_reflect = user_input[8:].strip()
                    if task_to_reflect:
                        print(f"🤔 Forcing reflection on: {task_to_reflect}")
                        # Create a dummy result for reflection
                        dummy_result = {"response": "This is a test reflection", "approach": "direct"}
                        reflection = await agent.reflection_engine.reflect_on_task(
                            task=task_to_reflect,
                            response=dummy_result["response"],
                            context=dummy_result,
                        )
                        if reflection:
                            print(f"✅ Reflection completed with confidence: {reflection.confidence_score:.2f}")
                            print(f"Critique: {reflection.critique[:200]}...")
                        else:
                            print("❌ Reflection failed")
                    continue

                # Process the input normally
                result = await agent.think(user_input)

                print(f"\n🤖 Aletheia: {result.get('response', 'No response')}")

                # Show metadata if available
                if "meta" in result:
                    meta = result["meta"]
                    print(f"\n💭 Thoughts: {meta.get('processing_time', 0):.2f}s | "
                          f"Task #{meta.get('task_id', 0)} | "
                          f"Approach: {result.get('approach', 'unknown')} | "
                          f"Route: {result.get('execution_details', {}).get('route_used', 'unknown')}")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Initialization error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Suppress the KeyboardInterrupt traceback
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import sys
        sys.exit(1)
