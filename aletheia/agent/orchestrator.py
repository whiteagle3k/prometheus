"""Main orchestrator for the Aletheia thinking agent."""

import asyncio
import re
import traceback
import warnings
from datetime import datetime
from typing import Any

from ..config import config
from ..llm.router import LLMRouter, TaskContext
from ..memory.summariser import MemorySummariser
from ..memory.vector_store import VectorStore
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

        # Conversation state for better context tracking
        self.conversation_context = {
            "user_name": None,
            "conversation_topic": None,
            "interaction_count": 0,
            "last_user_language": "en",
        }

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
        self._update_conversation_context(user_input)

        try:
            # Step 1: Retrieve relevant memories - TEMPORARILY DISABLED
            # relevant_memories = await self._retrieve_relevant_memories(user_input)
            relevant_memories = []  # Disable memory retrieval to prevent contamination

            # Step 2: Determine if task needs planning
            needs_planning = await self._should_plan_task(user_input)

            if needs_planning:
                # Complex task - use planning approach
                result = await self._handle_complex_task(user_input, relevant_memories)
            else:
                # Simple task - direct execution
                result = await self._handle_simple_task(user_input, relevant_memories)

            # Step 3: Store experience in memory
            await self._store_experience(user_input, result)

            # Step 4: Optional reflection
            if config.reflection_enabled:
                await self._maybe_reflect(user_input, result)

            # Step 5: Memory management
            await self._manage_memory()

            # Track task in history
            task_record = {
                "timestamp": start_time.isoformat(),
                "user_input": user_input,
                "result": result,
                "session_id": self.session_id,
                "conversation_context": self.conversation_context.copy(),
            }
            self.task_history.append(task_record)

            # Add timing information
            result["meta"] = {
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "session_id": self.session_id,
                "task_id": len(self.task_history),
                "relevant_memories_count": len(relevant_memories),
                "used_planning": needs_planning,
                "conversation_context": self.conversation_context.copy(),
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

    def _update_conversation_context(self, user_input: str) -> None:
        """Update conversation context based on user input."""

        self.conversation_context["interaction_count"] += 1

        # Detect language
        # Simple heuristic: if contains Cyrillic characters, it's Russian
        if any("\u0400" <= char <= "\u04FF" for char in user_input):
            self.conversation_context["last_user_language"] = "ru"
        else:
            self.conversation_context["last_user_language"] = "en"

        # Extract user name if mentioned
        name_patterns = [
            r"меня зовут\s+(\w+)",  # Russian: "меня зовут Игорь"
            r"мое имя\s+(\w+)",     # Russian: "мое имя Игорь"
            r"я\s+(\w+)",           # Russian: "я Игорь"
            r"my name is\s+(\w+)",  # English: "my name is Igor"
            r"i'?m\s+(\w+)",        # English: "I'm Igor"
            r"call me\s+(\w+)",     # English: "call me Igor"
        ]

        for pattern in name_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                self.conversation_context["user_name"] = match.group(1).capitalize()
                break

        # Update conversation topic (simple keyword extraction)
        if len(user_input.split()) > 3:  # Only for substantial messages
            # Remove common words and extract potential topics
            important_words = [word for word in user_input.lower().split()
                             if len(word) > 4 and word not in ["привет", "hello", "спасибо", "thanks"]]
            if important_words:
                self.conversation_context["conversation_topic"] = important_words[0]

    def _build_context_summary(self) -> str:
        """Build a clean context summary for external LLM calls."""
        context_parts = []
        
        # Add user information if available
        if self.conversation_context["user_name"]:
            context_parts.append(f"User name: {self.conversation_context['user_name']}")
        
        # Add conversation topic if identified
        if self.conversation_context["conversation_topic"]:
            context_parts.append(f"Topic: {self.conversation_context['conversation_topic']}")
        
        # Add recent interaction summary (last 2-3 exchanges)
        if self.task_history:
            context_parts.append("Recent conversation:")
            for i, task_record in enumerate(self.task_history[-2:], 1):
                user_input = task_record['user_input'][:60]
                response = task_record['result'].get('response', '')[:80]
                
                # Clean up the response preview
                if len(response) > 80:
                    response = response[:80] + "..."
                
                context_parts.append(f"{i}. User: {user_input}")
                context_parts.append(f"   Assistant: {response}")
        
        return "\n".join(context_parts) if context_parts else ""

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

    async def _should_plan_task(self, user_input: str) -> bool:
        """Determine if a task requires detailed planning."""

        # Only trigger planning for clearly complex or multi-step tasks
        planning_indicators = [
            # Multi-word phrases that strongly indicate planning need
            "step by step", "пошагово", "explain how to", "объясни как",
            "teach me how", "научи меня как", "guide me through", "покажи как",
            "what steps", "какие шаги", "process of", "процесс создания",
            "make a plan", "создай план", "составь план", "break down", "разбери детально",
            "comprehensive guide", "полное руководство", "detailed explanation", "подробное объяснение",
            "объясни как пошагово", "покажи пошагово"
        ]

        user_lower = user_input.lower()

        # Check for explicit planning keywords (must be substantial phrases)
        has_strong_planning_keywords = any(
            indicator in user_lower 
            for indicator in planning_indicators
        )

        # Check for very complex questions (much higher threshold)
        is_very_complex = len(user_input.split()) > 30  # Very high threshold

        # Check for multiple clear parts/questions  
        has_multiple_clear_parts = (
            user_input.count('?') > 1 or  # Multiple questions
            any(sep in user_input for sep in [" then ", " next ", " after that ", " затем ", " потом ", " далее "])
        )

        # Explicitly exclude simple conversational phrases
        simple_phrases = [
            "да", "нет", "yes", "no", "ok", "хорошо", "понятно", "спасибо", "thanks",
            "да, я это и спрашиваю", "yes, that's what I'm asking", "конечно", "of course"
        ]
        
        # Use word boundaries to avoid partial matches
        is_simple_response = any(
            re.search(r'\b' + re.escape(phrase) + r'\b', user_lower) 
            for phrase in simple_phrases 
            if len(phrase.split()) == 1  # Single words need word boundaries
        ) or any(
            phrase in user_lower 
            for phrase in simple_phrases 
            if len(phrase.split()) > 1  # Multi-word phrases can use simple contains
        )
        
        # Also check if it's a very short response
        is_simple_response = is_simple_response and len(user_input.split()) < 10

        # Only plan for explicitly complex tasks, not simple follow-ups
        should_plan = (has_strong_planning_keywords or is_very_complex or has_multiple_clear_parts) and not is_simple_response

        return should_plan

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
        """Handle simple tasks with direct execution."""

        print("⚡ Handling simple task with direct execution...")

        # For simple greetings, use minimal context to avoid contamination
        is_simple_greeting = any(greeting in user_input.lower() for greeting in [
            "привет", "hello", "hi", "как дела", "how are you", "ты кто", "who are you",
            "что умеешь", "what can you do", "как тебя зовут", "what's your name"
        ])
        # Exclude questions that specifically need context
        needs_context = any(context_question in user_input.lower() for context_question in [
            "как меня зовут", "what's my name", "who am i", "кто я", "меня зовут", "my name"
        ])
        
        is_simple_greeting = is_simple_greeting and not needs_context

        if is_simple_greeting:
            # Use just the user input without additional context for clean responses
            enhanced_prompt = user_input
        else:
            # Enable basic context for non-greeting interactions to remember names
            enhanced_prompt = user_input
            
            # Build minimal conversation context
            conversation_context = ""

            # Add user name if we know it
            if self.conversation_context["user_name"]:
                if self.conversation_context["last_user_language"] == "ru":
                    conversation_context += f"\n\nПользователь: {self.conversation_context['user_name']}\n"
                else:
                    conversation_context += f"\n\nUser: {self.conversation_context['user_name']}\n"

            # Add only the most recent interaction for basic context (if safe)
            if self.task_history and len(self.task_history) > 0:
                last_task = self.task_history[-1]
                last_response = last_task['result'].get('response', '')
                
                # Only include if response looks clean (no contamination markers)
                if last_response and len(last_response) < 200 and not any(marker in last_response.lower() for marker in [
                    "cv template", "theoretical", "follow up", "task:", "approach:", "аминь"
                ]):
                    cleaned_response = self._clean_context_response(last_response)
                    if len(cleaned_response) > 10:  # Only if meaningful content remains
                        conversation_context += f"\nПоследний обмен:\n"
                        conversation_context += f"Пользователь: {last_task['user_input'][:50]}\n"
                        conversation_context += f"Ассистент: {cleaned_response[:80]}\n"

            # Combine user input with minimal context
            if conversation_context.strip():
                enhanced_prompt = f"{user_input}{conversation_context}"

        # Create task context
        task_context = TaskContext(
            prompt=enhanced_prompt,
            max_tokens=500,  # Reduced to encourage more concise responses
            requires_deep_reasoning=False,  # Don't auto-trigger external LLM
            is_creative="create" in user_input.lower() or "write" in user_input.lower(),
            needs_latest_knowledge="latest" in user_input.lower() or "recent" in user_input.lower(),
            # Only add context information for external LLM calls to avoid local contamination
            conversation_context=self._build_context_summary() if not is_simple_greeting else None,
            user_name=self.conversation_context.get("user_name"),
            session_context={
                "session_id": self.session_id,
                "interaction_count": self.conversation_context["interaction_count"],
                "language": self.conversation_context["last_user_language"]
            }
        )

        # Execute task
        result = await self.router.execute_task(task_context)

        return {
            "type": "simple_task",
            "response": result.get("result", "No response generated"),
            "execution_details": {
                "route_used": result.get("route_used"),
                "execution_time": result.get("execution_time"),
                "estimated_cost": result.get("estimated_cost", 0),
            },
            "approach": "direct",
        }

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
            # Add context for subtasks too
            conversation_context=self._build_context_summary(),
            user_name=self.conversation_context.get("user_name"),
            session_context={
                "session_id": self.session_id,
                "interaction_count": self.conversation_context["interaction_count"],
                "language": self.conversation_context["last_user_language"]
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
            # Add context for synthesis too
            conversation_context=self._build_context_summary(),
            user_name=self.conversation_context.get("user_name"),
            session_context={
                "session_id": self.session_id,
                "interaction_count": self.conversation_context["interaction_count"],
                "language": self.conversation_context["last_user_language"]
            }
        )

        synthesis_result = await self.router.execute_task(synthesis_context)

        return synthesis_result.get("result", "Unable to synthesize results")

    async def _store_experience(self, user_input: str, result: dict[str, Any]) -> None:
        """Store the task experience in memory."""

        try:
            # Temporarily disabled to prevent storing contaminated responses
            print("🚫 Memory storage temporarily disabled to prevent contamination")
            return
            
            # Create experience summary
            experience = f"Task: {user_input}\n"
            experience += f"Approach: {result.get('approach', 'unknown')}\n"
            experience += f"Response: {result.get('response', 'No response')[:500]}...\n"

            # Add execution details
            if "execution_details" in result:
                details = result["execution_details"]
                experience += f"Route: {details.get('route_used', 'unknown')}\n"
                experience += f"Cost: ${details.get('estimated_cost', 0):.4f}\n"

            # Store in vector database
            await self.vector_store.store_memory(
                content=experience,
                memory_type="task_experience",
                metadata={
                    "session_id": self.session_id,
                    "approach": result.get("approach"),
                    "task_type": result.get("type"),
                    "user_input_length": len(user_input),
                },
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
        print("✅ Memory reset complete")

    def _clean_context_response(self, response: str) -> str:
        """Clean the context response to avoid contamination."""
        if not response:
            return response
            
        # Remove known contamination patterns
        contamination_patterns = [
            r"CV Template.*", r"Имя: Алетейя.*", r"Follow-up Question.*", 
            r"theoretical.*", r"аминь.*", r"Task:.*", r"Approach:.*", 
            r"Response:.*", r"Relevant context:.*", r"Solutions for.*",
            r"How can you.*", r"Now, here are.*"
        ]
        
        import re
        cleaned = response
        for pattern in contamination_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove multiple whitespaces and normalize
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # If response is too short after cleaning, return original truncated
        if len(cleaned) < 10:
            return response[:50] + "..." if len(response) > 50 else response
            
        return cleaned


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
                    print(f"\n📝 Conversation History ({len(agent.task_history)} entries):")
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
