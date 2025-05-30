"""Main orchestrator for the Aletheia thinking agent."""

import asyncio
import re
import traceback
import warnings
from datetime import datetime
from typing import Any
import time

from ..config import config
from ..identity.loader import load_identity_config, get_validation_config
from ..llm.router import LLMRouter, TaskContext
from ..memory.summariser import MemorySummariser
from ..memory.vector_store import VectorStore
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

        # Initialize conversation context manager
        self.context = ConversationContext(self.identity_config)

        # Core components
        self.vector_store = VectorStore()
        self.router = LLMRouter()
        self.planner = TaskPlanner(self.router)
        self.reflection_engine = ReflectionEngine(self.router, self.vector_store)
        self.memory_summariser = MemorySummariser(self.vector_store)

        print("✅ Aletheia agent initialized")

    async def think(self, user_input: str) -> dict[str, Any]:
        """Main thinking loop for processing user input."""

        print(f"\n🧠 Processing: {user_input[:100]}{'...' if len(user_input) > 100 else ''}")

        start_time = datetime.now()

        # Update conversation context
        self.context.update_from_input(user_input)

        try:
            # Step 1: Retrieve relevant memories for better context
            relevant_memories = await self._retrieve_relevant_memories(user_input)

            # Step 2: Determine if task needs planning
            needs_planning = self.context.should_plan_task(user_input)

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
        """Retrieve relevant memories for the current task."""

        try:
            memories = await self.vector_store.search_memories(
                query=user_input,
                n_results=5,
            )

            if memories:
                print(f"📚 Found {len(memories)} relevant memories")

            return memories

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

        # Create a plan
        plan = await self.planner.create_plan(user_input)

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

            # Execute sub-task
            subtask_result = await self._execute_subtask(next_task, relevant_memories)
            execution_results.append({
                "subtask": next_task,
                "result": subtask_result,
            })

            completed_tasks.append(next_task.id)

        # Synthesize final result
        final_result = await self._synthesize_plan_results(
            user_input, plan, execution_results
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
        }

    async def _handle_simple_task(
        self,
        user_input: str,
        relevant_memories: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Handle simple tasks with structured local LLM approach."""
        
        start_time = time.time()
        
        # Build context for the local LLM
        context_prompt = self.context.build_context_prompt(user_input)
        
        print("⚡ Handling simple task with structured local LLM...")
        
        # Use structured generation instead of the old routing assessment
        try:
            # Check if this is a reference question that needs context
            context_info = None
            current_input = user_input.lower()
            
            # Enhanced reference detection
            has_references = any(pronoun in current_input for pronoun in 
                               ["он", "она", "оно", "они", "его", "её", "их", "им", "ей", "ему", "ими", "ним", "ней", "нём", 
                                "это", "то", "такое", "этого", "того", "it", "that", "this", "them", "those"])
            
            # Check for implicit continuation patterns
            implicit_continuation_patterns = [
                r'\bа\s+если\b',  # "а если" (but if)
                r'\bа\s+что\b',   # "а что" (and what)
                r'^\s*(а|но|и)\s+', # Starting with "а", "но", "и" (and, but)
            ]
            has_implicit_continuation = any(re.search(pattern, current_input) for pattern in implicit_continuation_patterns)
            
            # If this is a reference question, build context
            if (has_references or has_implicit_continuation) and self.context.current_topic:
                context_info = self._build_context_summary()
            
            structured_result = await self.router.local_llm.generate_structured(
                prompt=context_prompt,
                context=context_info,  # Pass context for reference questions
                max_tokens=512,  # Reduced from 1024 for better performance
                temperature=0.7
            )
            
            print(f"🎯 Structured response - Confidence: {structured_result['confidence']}")
            if structured_result['reasoning']:
                print(f"💭 Reasoning: {structured_result['reasoning'][:100]}...")
            
            # Check if external consultation is recommended
            if structured_result['external_needed']:
                print("🔬 Local LLM recommends external consultation - routing to external LLM")
                
                # Route to external LLM
                task_context = TaskContext(
                    prompt=user_input,
                    max_tokens=1024,
                    requires_deep_reasoning=True,
                    conversation_context=self._build_context_summary(),
                    user_name=self.context.user_name,
                    session_context={
                        "session_id": self.session_id,
                        "interaction_count": self.context.interaction_count,
                        "language": self.context.last_user_language
                    }
                )
                
                external_result = await self.router.execute_task(task_context)
                route_used = "external"
                response_text = external_result.get("result", "")
                execution_time = time.time() - start_time
                
                return {
                    "type": "simple_task",
                    "response": response_text,
                    "execution_details": {
                        "route_used": route_used,
                        "execution_time": execution_time,
                        "estimated_cost": external_result.get("estimated_cost", 0),
                        "routing_assessment": "structured_local",
                        "local_confidence": structured_result['confidence'],
                        "local_reasoning": structured_result['reasoning'],
                        "consultation_metadata": external_result.get("consultation_metadata"),
                    },
                    "approach": "structured_local",
                }
            else:
                print("💻 Local LLM confident in handling - using structured response")
                
                route_used = "local"
                response_text = structured_result['answer']
                execution_time = time.time() - start_time
                
                return {
                    "type": "simple_task",
                    "response": response_text,
                    "execution_details": {
                        "route_used": route_used,
                        "execution_time": execution_time,
                        "estimated_cost": 0,
                        "routing_assessment": "structured_local",
                        "local_confidence": structured_result['confidence'],
                        "local_reasoning": structured_result['reasoning'],
                        "raw_response": structured_result.get('raw_response', ''),
                    },
                    "approach": "structured_local",
                }
                
        except Exception as e:
            print(f"❌ Structured local LLM failed: {e}")
            # Fallback to external LLM
            task_context = TaskContext(
                prompt=user_input,
                max_tokens=1024,
                requires_deep_reasoning=True,
                conversation_context=self._build_context_summary(),
                user_name=self.context.user_name,
                session_context={
                    "session_id": self.session_id,
                    "interaction_count": self.context.interaction_count,
                    "language": self.context.last_user_language
                }
            )
            
            external_result = await self.router.execute_task(task_context)
            execution_time = time.time() - start_time
            
            return {
                "type": "simple_task",
                "response": external_result.get("result", ""),
                "execution_details": {
                    "route_used": "external_fallback",
                    "execution_time": execution_time,
                    "estimated_cost": external_result.get("estimated_cost", 0),
                    "routing_assessment": "structured_local_failed",
                    "error": str(e),
                    "consultation_metadata": external_result.get("consultation_metadata"),
                },
                "approach": "structured_local",
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

        # Create context for subtask
        task_context = TaskContext(
            prompt=subtask.description,
            max_tokens=600,
            requires_deep_reasoning=subtask.requires_external_llm,
            cost_sensitive=not subtask.requires_external_llm,
            conversation_context=self._build_context_summary(),
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
        execution_results: list[dict[str, Any]]
    ) -> str:
        """Synthesize results from plan execution into final response."""

        # Compile all sub-task results
        results_text = ""
        for i, exec_result in enumerate(execution_results, 1):
            subtask = exec_result["subtask"]
            result = exec_result["result"]

            results_text += f"\n{i}. {subtask.description}\n"
            results_text += f"Result: {result.get('result', 'No result')}\n"

        synthesis_prompt = f"""I need to synthesize the results from executing a complex task plan.

Original Task: {original_task}

Plan Execution Results:
{results_text}

Please provide a comprehensive, well-structured response that:
1. Directly answers the original question/task
2. Integrates insights from all sub-task results
3. Presents information in a logical, coherent manner
4. Highlights key findings or recommendations
5. Addresses any limitations or areas for further exploration

Focus on creating a cohesive response that feels like a complete answer to the original task."""

        synthesis_context = TaskContext(
            prompt=synthesis_prompt,
            max_tokens=1200,
            requires_deep_reasoning=True,
            conversation_context=self._build_context_summary(),
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
            if "execution_details" in result:
                details = result["execution_details"]
                experience += f"Route: {details.get('route_used', 'unknown')}\n"
                experience += f"Cost: ${details.get('estimated_cost', 0):.4f}\n"

            # Prepare metadata with proper types (ChromaDB only accepts str, int, float, bool)
            metadata = {
                "session_id": self.session_id,
                "approach": result.get("approach", "unknown"),
                "task_type": result.get("type", "unknown"),
                "user_input_length": len(user_input),
                "user_name": self.context.user_name or "unknown",
                "language": self.context.last_user_language,
            }

            # Store in vector database
            await self.vector_store.store_memory(
                content=experience,
                memory_type="task_experience",
                metadata=metadata,
            )

        except Exception as e:
            print(f"⚠️  Error storing experience: {e}")

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
            # Check if summarization is needed
            if await self.memory_summariser.should_summarize():
                external_llm = await self.router.external_manager.get_best_available()
                await self.memory_summariser.summarize_and_compress(external_llm)

            # Cleanup old memories if needed
            memory_count = await self.vector_store.get_memory_count()
            if memory_count > config.max_memory_entries:
                deleted = await self.vector_store.cleanup_old_memories()
                if deleted > 0:
                    print(f"🗑️  Cleaned up {deleted} old memories")

        except Exception as e:
            print(f"⚠️  Error managing memory: {e}")

    async def get_status(self) -> dict[str, Any]:
        """Get current agent status and diagnostics."""

        router_health = await self.router.health_check()
        memory_count = await self.vector_store.get_memory_count()

        return {
            "session_id": self.session_id,
            "tasks_completed": len(self.task_history),
            "memory_entries": memory_count,
            "router_health": router_health,
            "conversation_context": self.context.get_context_summary(),
            "config": {
                "reflection_enabled": config.reflection_enabled,
                "max_memory_entries": config.max_memory_entries,
                "local_token_threshold": config.local_token_threshold,
            },
        }

    async def reset_memory(self) -> None:
        """Reset all agent memory (for testing/debugging)."""

        print("🗑️  Resetting agent memory...")
        await self.vector_store.reset_all()
        self.task_history.clear()
        # Reset conversation context but keep identity config
        self.context = ConversationContext(self.identity_config)
        print("✅ Memory reset complete")

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


# Simple CLI interface for testing
async def main() -> None:
    """Simple CLI interface for testing the agent."""

    try:
        agent = AletheiaAgent()

        print("\n🤖 Aletheia Agent - Interactive Mode")
        print("Commands:")
        print("  'quit' - Exit")
        print("  'status' - Show diagnostics")
        print("  'reset' - Clear memory")
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
