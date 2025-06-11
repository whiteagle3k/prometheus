"""
Base Entity Class

Provides the core framework functionality that all entities inherit.
Defines clear contracts for identity, planning, and reflection overrides.
Enhanced with MCP (Model Context Protocol) capabilities for external integrations.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, List, Dict, Optional
import json

from .config import config
from .context.context_manager import ConversationContext
from .goals.goal_manager import GoalManager
from .llm.router import LLMRouter
from .memory.controller import MemoryController
from .memory.summariser import MemorySummariser
from .memory.user_profile_store import UserProfileStore
from .memory.vector_store import VectorStore

# MCP Integration
from .mcp.client.direct_mcp_client import DirectMCPClient

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
    
    Enhanced with MCP capabilities for external integrations:
    - Filesystem operations
    - Git repository management
    - Terminal command execution
    - Web access and search
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
        
        # Initialize MCP client for external capabilities
        self.mcp_client = None
        self.mcp_capabilities = {}
        self._mcp_initialized = False

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

    async def think(self, user_text: str, user_id: str | None = None) -> dict[str, Any]:
        """
        Main thinking interface - processes user input and returns response.
        Enhanced with MCP capabilities for external tool access.

        Args:
            user_text: User input text
            user_id: Optional user identifier for session management

        This is the primary contract method that entities must support.
        """

        print(f"\n🧠 Processing: {user_text[:100]}{'...' if len(user_text) > 100 else ''}")
        if user_id:
            print(f"👤 User session: {user_id}")

        start_time = datetime.now()

        # Ensure MCP is ready
        await self._ensure_mcp()

        # Update conversation context with user_id
        self.context.update_from_input(user_text, user_id=user_id)

        try:
            # Check for MCP capability requests first
            mcp_result = await self._handle_mcp_request(user_text)
            if mcp_result:
                return mcp_result

            # Process through the entity's thinking pipeline
            result = await self._process_input(user_text, user_id=user_id)
            tool_calls = result.get("tool_calls", [])

            # Handle tool calls if present
            tool_call_results = []
            max_tool_iters = 5
            while tool_calls and max_tool_iters > 0:
                for tool_call in tool_calls:
                    method = tool_call["method"]
                    if method.count('_') > 2:
                        parts = method.split('_')
                        method = '_'.join([parts[0]] + parts[-2:])
                    mcp_result = await self.mcp_client.execute_capability(
                        method,
                        tool_call["params"]
                    )
                    tool_call_results.append(mcp_result)
                result = await self._process_input(user_text, user_id=user_id)
                tool_calls = result.get("tool_calls", [])
                max_tool_iters -= 1

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
                user_text, response
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

            # Проброс tool_calls на верхний уровень
            out = dict(result)
            if "tool_calls" in result and result["tool_calls"]:
                out["tool_calls"] = result["tool_calls"]
            return out

        except Exception as e:
            print(f"❌ Error in think: {e}")
            return {"error": str(e)}

    async def _handle_mcp_request(self, user_text: str) -> str | None:
        """Check if the request involves MCP capabilities and handle directly."""
        if not self.mcp_client:
            return None

        # Simple keyword detection for MCP capabilities
        mcp_keywords = {
            "file": ["read", "write", "create", "delete", "list", "directory"],
            "git": ["commit", "push", "pull", "branch", "status", "diff"],
            "terminal": ["run", "execute", "command", "script"],
            "web": ["search", "url", "website", "http", "download"]
        }

        user_lower = user_text.lower()
        
        # Check for direct capability requests
        for category, keywords in mcp_keywords.items():
            if any(keyword in user_lower for keyword in keywords):
                # Enhanced capability detection with simple parsing
                if "read file" in user_lower or "show file" in user_lower:
                    # Try to extract file path
                    import re
                    path_match = re.search(r'(?:file|path)\s+["\']?([^"\']+)["\']?', user_text)
                    if path_match:
                        path = path_match.group(1)
                        result = await self.mcp_client.read_file(path)
                        if result["success"]:
                            return f"📄 File content:\n\n{result['result'][0].text}"
                        else:
                            return f"❌ Error reading file: {result['error']}"
                
                elif "git status" in user_lower:
                    result = await self.mcp_client.git_status()
                    if result["success"]:
                        return f"📋 Git status:\n\n{result['result'][0].text}"
                    else:
                        return f"❌ Git error: {result['error']}"
                
                elif "search" in user_lower and ("web" in user_lower or "internet" in user_lower):
                    # Extract search query
                    import re
                    query_match = re.search(r'search\s+(?:for\s+)?["\']?([^"\']+)["\']?', user_text, re.IGNORECASE)
                    if query_match:
                        query = query_match.group(1)
                        result = await self.mcp_client.web_search(query)
                        if result["success"]:
                            return f"🔍 Search results:\n\n{result['result'][0].text}"
                        else:
                            return f"❌ Search error: {result['error']}"

        return None

    # MCP Integration Methods

    async def get_mcp_capabilities(self) -> List[Dict[str, str]]:
        """Get available MCP capabilities."""
        await self._ensure_mcp()
        if not self.mcp_client:
            return []
        return await self.mcp_client.get_available_capabilities()

    async def execute_mcp_capability(self, capability_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP capability."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        return await self.mcp_client.execute_capability(capability_name, arguments)

    # Convenience methods for common MCP operations

    async def read_file(self, path: str) -> str:
        """Read file contents through MCP filesystem server."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        result = await self.mcp_client.read_file(path)
        return result.get("result", [{}])[0].get("text", "")

    async def write_file(self, path: str, content: str) -> str:
        """Write file through MCP filesystem server."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        result = await self.mcp_client.write_file(path, content)
        if result["success"]:
            return result["result"][0]["text"]
        else:
            return f"Error: {result['error']}"

    async def list_directory(self, path: str) -> str:
        """List directory through MCP filesystem server."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        result = await self.mcp_client.list_directory(path)
        if result["success"]:
            return result["result"][0]["text"]
        else:
            return f"Error: {result['error']}"

    # Git operations
    
    async def git_status(self, cwd: str = ".") -> str:
        """Get git status through MCP git server."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        result = await self.mcp_client.git_status(cwd)
        if result["success"]:
            return result["result"][0]["text"]
        else:
            return f"Error: {result['error']}"
    
    async def git_diff(self, cwd: str = ".", cached: bool = False, file: str = None) -> str:
        """Get git diff through MCP git server."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        result = await self.mcp_client.git_diff(cwd, cached, file)
        if result["success"]:
            return result["result"][0]["text"]
        else:
            return f"Error: {result['error']}"
    
    async def git_add(self, files: List[str], cwd: str = ".") -> str:
        """Add files to git through MCP git server."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        result = await self.mcp_client.git_add(files, cwd)
        if result["success"]:
            return result["result"][0]["text"]
        else:
            return f"Error: {result['error']}"
    
    async def git_commit(self, message: str, cwd: str = ".", amend: bool = False) -> str:
        """Create git commit through MCP git server."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        result = await self.mcp_client.git_commit(message, cwd, amend)
        if result["success"]:
            return result["result"][0]["text"]
        else:
            return f"Error: {result['error']}"
    
    async def git_log(self, limit: int = 10, oneline: bool = True, cwd: str = ".") -> str:
        """Get git log through MCP git server."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        result = await self.mcp_client.git_log(limit, oneline, cwd)
        if result["success"]:
            return result["result"][0]["text"]
        else:
            return f"Error: {result['error']}"

    async def execute_command(self, command: str, cwd: str = ".", timeout: int = 30) -> str:
        """Execute command through MCP terminal server."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        result = await self.mcp_client.execute_command(command, cwd, timeout)
        if result["success"]:
            return result["result"][0]["text"]
        else:
            return f"Error: {result['error']}"

    async def run_script(self, script_path: str, args: List[str] = None, cwd: str = ".", timeout: int = 60) -> str:
        """Run script through MCP terminal server."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        result = await self.mcp_client.run_script(script_path, args, cwd, timeout)
        if result["success"]:
            return result["result"][0]["text"]
        else:
            return f"Error: {result['error']}"

    async def get_env(self, name: str, default: str = None) -> str:
        """Get environment variable through MCP terminal server."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        result = await self.mcp_client.get_env(name, default)
        if result["success"]:
            return result["result"][0]["text"]
        else:
            return f"Error: {result['error']}"

    async def web_search(self, query: str, max_results: int = 5) -> str:
        """Search the web through MCP web server."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        result = await self.mcp_client.web_search(query, max_results)
        if result["success"]:
            return result["result"][0]["text"]
        else:
            return f"Error: {result['error']}"

    async def http_get(self, url: str, headers: Dict[str, str] = None, timeout: int = 10) -> str:
        """Make HTTP GET request through MCP web server."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        result = await self.mcp_client.http_get(url, headers, timeout)
        if result["success"]:
            return result["result"][0]["text"]
        else:
            return f"Error: {result['error']}"

    async def scrape_text(self, url: str, selector: str = None, timeout: int = 10) -> str:
        """Scrape text from web page through MCP web server."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        result = await self.mcp_client.scrape_text(url, selector, timeout)
        if result["success"]:
            return result["result"][0]["text"]
        else:
            return f"Error: {result['error']}"

    def _display_debug_summary(self, user_input: str, result: dict[str, Any], total_time: float) -> None:
        """Display comprehensive debug information about the thinking process."""
        execution_details = result.get("execution_details", {})
        route_used = execution_details.get("route_used", "unknown")
        approach = execution_details.get("approach", "unknown")
        fast_track = execution_details.get("fast_track", False)

        # Get provider info if available
        consultation_metadata = execution_details.get("consultation_metadata", {})
        provider = consultation_metadata.get("provider", "")
        
        # Performance metrics
        execution_time = execution_details.get("execution_time", 0)
        
        # Format route info
        route_str = f"{route_used.upper()}"
        if provider:
            route_str += f" ({provider})"
            
        # Clean format for output - only show response in shell UI
        # All other debug info is logged but not displayed
        # print(f"Route: {route_str}, Time: {execution_time:.1f}s")

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
        """
        Processes user input through the routing and execution pipeline.
        This is the core of the entity's thinking process after initial MCP checks.
        """
        # Create a task context for the router
        # This now includes a callable for deferred memory retrieval
        task_context = self.context.create_task_context(
            user_input, 
            self.mcp_capabilities,
            lambda: self._retrieve_relevant_memories(user_input)
        )

        # Execute the task through the router
        # The router will decide when/if to call the memory_retriever
        result = await self.router.execute_task(task_context)
        return result

    def _should_use_external_fast_track(self, user_input: str) -> bool:
        """
        Determines if the task is simple enough for a direct external API call,
        bypassing the full local routing and memory pipeline.
        
        Returns True if:
        1. Agent has prefer_external: true in config
        2. Not a user data query 
        3. Not an MCP request
        """
        # Check for MCP requests (should not fast-track)
        if self._is_mcp_request(user_input):
            return False
            
        # Check for user data queries (should not fast-track)
        user_name = self.context.user_name
        if user_name and user_name != "default":
            # Quick heuristic check for user data queries
            user_data_keywords = ["my", "me", "mine", "I", "personal", "profile", "data", "information about me"]
            if any(keyword in user_input.lower() for keyword in user_data_keywords):
                return False

        # Check if agent prefers external LLM
        operational_guidelines = self.identity_config.get("operational_guidelines", {})
        routing_policy = operational_guidelines.get("routing_policy", {})
        prefer_external = routing_policy.get("prefer_external", False)
        
        # Check thresholds substructure (Vasya's config structure)
        if not prefer_external:
            thresholds = routing_policy.get("thresholds", {})
            prefer_external = thresholds.get("prefer_external", False)
        
        # Check external_llms.routing_preferences (alternative location)
        if not prefer_external:
            external_prefs = self.identity_config.get("external_llms", {}).get("routing_preferences", {})
            prefer_external = external_prefs.get("prefer_external", False)

        return prefer_external

    def _is_mcp_request(self, user_input: str) -> bool:
        """Quick check if this is an MCP capability request."""
        mcp_keywords = [
            "read file", "write file", "create file", "delete file", "list directory",
            "git status", "git commit", "git push", "git pull", "git diff",
            "run command", "execute", "terminal", "bash", "shell",
            "web search", "search web", "download", "http", "url"
        ]
        user_lower = user_input.lower()
        return any(keyword in user_lower for keyword in mcp_keywords)

    async def _handle_external_fast_track(self, user_input: str, user_id: str | None = None) -> dict[str, Any]:
        """
        Fast-track processing for external-only agents.
        Skips memory processing and goes directly to external LLM.
        """
        import time
        start_time = time.time()

        try:
            # Build minimal context - just running summary and recent exchanges
            user_name = self.context.user_name
            
            # Get basic context without expensive memory operations
            context_prompt = self._build_minimal_context(user_input)
            
            print("🚀 Fast-track: Direct external LLM call...")

            # Get best available external LLM
            external_llm = await self.router.external_manager.get_best_available()
            if not external_llm:
                raise RuntimeError("No external LLM available")

            # Simple system prompt from identity
            system_prompt = self.identity_config.get("llm_instructions", "You are a helpful AI assistant.")
            
            # Enhanced prompt with minimal context
            if context_prompt:
                full_prompt = f"{context_prompt}\n\nUser: {user_input}\nAssistant:"
            else:
                full_prompt = user_input

            # Direct external LLM call (simplified, no consultation overhead)
            response_text = await external_llm.generate(
                prompt=full_prompt,
                system_prompt=system_prompt,
                max_tokens=1024,
                temperature=0.2
            )

            # Get provider info for metadata
            model_info = external_llm.get_model_info()
            provider_info = {
                "provider": external_llm.provider_type.value,
                "model": model_info.get("model", "unknown_model"),
            }

            # Add to episodes storage
            self.context.add_episode(user_input, response_text, {"route": "external_fast_track"})

            # Update running summary
            await self.context.update_summary_from_exchange(user_input, response_text)

            execution_time = time.time() - start_time

            return {
                "type": "fast_track",
                "response": response_text,
                "execution_details": {
                    "route_used": "external",
                    "execution_time": execution_time,
                    "estimated_cost": 0,  # Could estimate if needed
                    "approach": "external_fast_track",
                    "consultation_metadata": provider_info,
                    "episodes_used": 0,
                    "user_profile_used": False,
                    "memories_used": 0,
                    "fast_track": True
                },
                "approach": "external_fast_track",
            }

        except Exception as e:
            print(f"❌ Fast-track failed: {e}")
            execution_time = time.time() - start_time
            return {
                "type": "fast_track_error",
                "response": f"I'm having technical difficulties: {e}",
                "execution_details": {
                    "route_used": "error",
                    "execution_time": execution_time,
                    "estimated_cost": 0,
                    "approach": "error_fallback",
                    "error": str(e),
                    "fast_track": True
                },
                "approach": "error_fallback",
            }

    def _build_minimal_context(self, user_input: str) -> str:
        """Build minimal context for fast-track external calls."""
        context_parts = []

        # User identification
        if self.context.user_name and self.context.user_name != "default":
            context_parts.append(f"User: {self.context.user_name}")

        # Running summary (already computed, no expensive operations)
        summary = self.context.get_or_create_summary()
        if not summary.is_empty():
            current_summary = summary.get_summary()
            if current_summary and len(current_summary.strip()) > 10:
                context_parts.append(f"Context: {current_summary[:200]}...")

        # Last few exchanges only (avoid expensive episode search)
        recent_exchanges = min(3, len(self.task_history))
        if recent_exchanges > 0:
            context_parts.append("\nRecent conversation:")
            for task_record in self.task_history[-recent_exchanges:]:
                user_input_prev = task_record["user_input"][:100]
                response_prev = task_record["result"].get("response", "")[:100]
                context_parts.append(f"User: {user_input_prev}...")
                context_parts.append(f"Assistant: {response_prev}...")

        return "\n".join(context_parts) if context_parts else ""

    async def _retrieve_relevant_memories(self, user_input: str) -> list[dict[str, Any]]:
        """
        Retrieve relevant memories for context using a simplified, robust method.
        """
        try:
            # 1. Get top 8 memories from vector store
            vector_memories = await self.vector_store.search_memories(user_input, n_results=8)
            print(f"📂 Found {len(vector_memories)} memories from vector store.")

            # 2. Get last 3 conversational episodes
            recent_episodes = self.context.search_relevant_episodes(user_input, max_episodes=3)
            print(f"📚 Found {len(recent_episodes)} recent episodes.")

            # 3. Combine and deduplicate
            all_items = vector_memories + recent_episodes
            unique_items = []
            seen_ids = set()

            for item in all_items:
                item_id = item.get("id") or item.get("interaction_id")
                if item_id and item_id not in seen_ids:
                    unique_items.append(item)
                    seen_ids.add(item_id)
                elif not item_id:
                    unique_items.append(item) # Add items without an ID

            # 4. Sort by relevance (if available) and return top 8
            unique_items.sort(key=lambda x: x.get("distance", 1.0)) # Lower distance is better
            final_memories = unique_items[:8]

            print(f"🔧 Filtering complete. Selected {len(final_memories)} unique memories.")
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

            # Получаем инструменты, если они есть (например, из self._tools, установленной тестом)
            tools = getattr(self, '_tools', None)

            task_context = TaskContext(
                prompt=user_input,
                max_tokens=1024,
                tools=tools,
                requires_deep_reasoning=False,  # Let router decide based on content
                conversation_context=enhanced_context,
                user_name=user_name,
                session_context={
                    "session_id": self.session_id,
                    "interaction_count": len(self.task_history),
                    "language": getattr(self.context, "last_user_language", "en")
                }
            )
            print(f'[BaseEntity DEBUG] TaskContext.tools = {tools}')

            # Router makes intelligent local vs external decision
            result = await self.router.execute_task(task_context)
            route_used = result.get("route_used", "router_decision")
            response_text = result.get("result", "")

            # Add to episodes storage
            self.context.add_episode(user_input, response_text, {"route": route_used})

            # Update running summary with the exchange
            await self.context.update_summary_from_exchange(
                user_input, response_text
            )

            execution_time = time.time() - start_time

            out = {
                "type": "complex_task",
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
            if "tool_calls" in result and result["tool_calls"]:
                out["tool_calls"] = result["tool_calls"]
            return out

        except Exception as e:
            print(f"❌ LLM-managed context failed: {e}")
            # Return error response
            return {
                "type": "complex_task",
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
                    id=f"exp_{self.session_id}_{int(datetime.now().timestamp())}",
                    text=experience_text,
                    embedding=[0.0] * 384,  # Generate proper embedding or use placeholder
                    tier=MemoryTier.USER,
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

    async def _ensure_mcp(self):
        """Ensure MCP client is initialized."""
        if not self._mcp_initialized:
            try:
                from core.mcp.client.direct_mcp_client import DirectMCPClient
                self.mcp_client = DirectMCPClient()
                await self.mcp_client.initialize()
                
                # Get available capabilities
                capabilities = await self.mcp_client.get_available_capabilities()
                self.mcp_capabilities = {cap['name']: cap for cap in capabilities}
                
                logger.info(f"🔌 MCP initialized with {len(capabilities)} capabilities")
                for cap in capabilities:
                    logger.info(f"  • {cap['name']}: {cap['description']}")
                    
            except Exception as e:
                logger.warning(f"⚠️ MCP initialization failed: {e}")
                self.mcp_client = None
                self.mcp_capabilities = {}
            
            self._mcp_initialized = True

    # MCP methods with full responses for detailed control
    
    async def mcp_read_file(self, path: str) -> Dict[str, Any]:
        """Read file through MCP with full response."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        return await self.mcp_client.read_file(path)

    async def mcp_write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write file through MCP with full response."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        return await self.mcp_client.write_file(path, content)

    async def mcp_list_directory(self, path: str) -> Dict[str, Any]:
        """List directory through MCP with full response."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        return await self.mcp_client.list_directory(path)

    async def mcp_git_status(self, cwd: str = ".") -> Dict[str, Any]:
        """Get git status through MCP with full response."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        return await self.mcp_client.git_status(cwd)

    async def mcp_git_diff(self, cwd: str = ".", cached: bool = False, file: str = None) -> Dict[str, Any]:
        """Get git diff through MCP with full response."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        return await self.mcp_client.git_diff(cwd, cached, file)

    async def mcp_execute_command(self, command: str, cwd: str = ".", timeout: int = 30) -> Dict[str, Any]:
        """Execute command through MCP with full response."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        return await self.mcp_client.execute_command(command, cwd, timeout)

    async def mcp_web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Perform web search through MCP with full response."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        return await self.mcp_client.web_search(query, max_results)

    async def mcp_http_get(self, url: str, headers: Dict[str, str] = None, timeout: int = 10) -> Dict[str, Any]:
        """Make HTTP GET request through MCP with full response."""
        await self._ensure_mcp()
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        return await self.mcp_client.http_get(url, headers, timeout)
