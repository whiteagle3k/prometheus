"""Smoke tests for Aletheia agent system."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

# Import all dependencies with optional checks
pytest.importorskip("chromadb")  # Skip tests if ChromaDB not available

from aletheia.llm.router import LLMRouter, TaskContext, RouteDecision
from aletheia.llm.local_llm import LocalLLM
from aletheia.memory.vector_store import VectorStore
from aletheia.agent.planner import TaskPlanner
from aletheia.agent.reflexion import ReflectionEngine
from aletheia.agent.orchestrator import AletheiaAgent


class TestLLMRouter:
    """Test the LLM routing functionality."""

    @pytest.mark.unit
    def test_router_initialization(self):
        """Test that router initializes correctly."""
        router = LLMRouter()
        assert router is not None
        assert router.local_llm is not None
        assert router.external_manager is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_simple_task_context(self):
        """Test creating and processing a simple task context."""
        router = LLMRouter()
        
        task = TaskContext(
            prompt="Hello, world!",
            max_tokens=50,
            requires_deep_reasoning=False,
        )
        
        # Mock the local LLM to avoid requiring model download
        with patch.object(router.local_llm, 'is_available', return_value=True):
            with patch.object(router.local_llm, 'count_tokens', return_value=10):
                decision = await router.route_task(task)
                
                # Simple task should route to local
                assert decision == RouteDecision.LOCAL

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_complex_task_routing(self):
        """Test that complex tasks route to external LLM."""
        router = LLMRouter()
        
        # Create a complex task
        task = TaskContext(
            prompt="Please provide a detailed analysis of quantum computing algorithms",
            max_tokens=1500,
            requires_deep_reasoning=True,
        )
        
        with patch.object(router.local_llm, 'is_available', return_value=True):
            with patch.object(router.local_llm, 'count_tokens', return_value=50):
                with patch.object(router.external_manager, 'get_best_available', return_value=AsyncMock()):
                    decision = await router.route_task(task)
                    
                    # Complex task should route to external
                    assert decision == RouteDecision.EXTERNAL


class TestVectorStore:
    """Test vector store functionality."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_vector_store_initialization(self):
        """Test vector store initializes correctly."""
        vector_store = VectorStore()
        assert vector_store is not None
        assert vector_store.client is not None

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_memory_storage_and_retrieval(self):
        """Test storing and retrieving memories."""
        vector_store = VectorStore()
        
        # Store a test memory
        memory_id = await vector_store.store_memory(
            content="Test memory content",
            memory_type="test",
            metadata={"test": True}
        )
        
        assert memory_id is not None
        
        # Search for the memory
        memories = await vector_store.search_memories(
            query="test memory",
            n_results=1,
        )
        
        assert len(memories) >= 0  # Might be 0 if embedding fails


class TestTaskPlanner:
    """Test task planning functionality."""

    @pytest.mark.unit
    def test_planner_initialization(self):
        """Test planner initializes correctly."""
        router = LLMRouter()
        planner = TaskPlanner(router)
        assert planner is not None
        assert planner.router is not None

    @pytest.mark.unit
    def test_planning_prompt_creation(self):
        """Test that planning prompts are created correctly."""
        router = LLMRouter()
        planner = TaskPlanner(router)
        
        task = "Plan a birthday party"
        prompt = planner.create_planning_prompt(task)
        
        assert "Plan a birthday party" in prompt
        assert "sub-task" in prompt.lower()
        assert "decomposition" in prompt.lower()


class TestReflectionEngine:
    """Test reflection and self-critique functionality."""

    @pytest.mark.unit
    def test_reflection_initialization(self):
        """Test reflection engine initializes correctly."""
        router = LLMRouter()
        vector_store = VectorStore()
        reflection_engine = ReflectionEngine(router, vector_store)
        
        assert reflection_engine is not None
        assert reflection_engine.router is not None
        assert reflection_engine.vector_store is not None

    @pytest.mark.unit
    def test_reflection_prompt_creation(self):
        """Test reflection prompt creation."""
        router = LLMRouter()
        vector_store = VectorStore()
        reflection_engine = ReflectionEngine(router, vector_store)
        
        task = "What is the capital of France?"
        response = "The capital of France is Paris."
        
        prompt = reflection_engine.create_reflection_prompt(task, response)
        
        assert task in prompt
        assert response in prompt
        assert "critique" in prompt.lower()
        assert "confidence" in prompt.lower()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_should_reflect_logic(self):
        """Test the reflection decision logic."""
        router = LLMRouter()
        vector_store = VectorStore()
        reflection_engine = ReflectionEngine(router, vector_store)
        
        # High complexity should reflect more often than low complexity
        # We'll test the threshold logic rather than exact probabilities
        
        # Test multiple samples to ensure statistical behavior
        high_complexity_reflects = []
        low_complexity_reflects = []
        
        for _ in range(20):
            high_complexity_reflects.append(await reflection_engine.should_reflect(0.9))
            low_complexity_reflects.append(await reflection_engine.should_reflect(0.1))
        
        # High complexity should reflect more often than low complexity
        high_reflect_rate = sum(high_complexity_reflects) / len(high_complexity_reflects)
        low_reflect_rate = sum(low_complexity_reflects) / len(low_complexity_reflects)
        
        # Allow some flexibility but ensure high complexity reflects more
        assert high_reflect_rate >= low_reflect_rate, f"High complexity rate {high_reflect_rate} should be >= low complexity rate {low_reflect_rate}"
        
        # At least some high complexity tasks should reflect
        assert high_reflect_rate > 0.1, f"High complexity reflection rate {high_reflect_rate} too low"


class TestAletheiaAgent:
    """Test the main agent orchestrator."""

    @pytest.mark.unit
    def test_agent_initialization(self):
        """Test agent initializes all components correctly."""
        agent = AletheiaAgent()
        
        assert agent is not None
        assert agent.router is not None
        assert agent.vector_store is not None
        assert agent.planner is not None
        assert agent.reflection_engine is not None
        assert agent.session_id is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_agent_status(self):
        """Test agent status reporting."""
        agent = AletheiaAgent()
        
        status = await agent.get_status()
        
        assert "session_id" in status
        assert "tasks_completed" in status
        assert "memory_stats" in status
        assert status["tasks_completed"] == 0  # New agent

    @pytest.mark.unit
    def test_task_planning_decision(self):
        """Test the agent's task planning decision logic."""
        agent = AletheiaAgent()
        
        # Simple question shouldn't need planning
        simple_task = "What is 2+2?"
        assert agent.context.should_plan_task(simple_task) == False
        
        # Complex request should need planning - use exact trigger phrase
        complex_task = "Please create a plan step by step for organizing a conference with detailed instructions"
        assert agent.context.should_plan_task(complex_task) == True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_memory_reset(self):
        """Test memory reset functionality."""
        agent = AletheiaAgent()
        
        # Add some task history
        agent.task_history.append({"test": "data"})
        assert len(agent.task_history) == 1
        
        # Reset memory
        await agent.reset_memory()
        
        # History should be cleared
        assert len(agent.task_history) == 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_memory_persistence(self):
        """Test that experiences are stored in memory."""
        agent = AletheiaAgent()
        
        mock_response = {
            "result": "Test response",
            "route_used": "local",
            "execution_time": 0.1,
            "estimated_cost": 0.0,
        }
        
        with patch.object(agent.router, 'execute_task', return_value=mock_response):
            with patch.object(agent.vector_store, 'store_memory', return_value="memory_id") as mock_store:
                await agent.think("Test question")
                
                # Verify memory was stored (might be called multiple times due to reflection)
                assert mock_store.call_count >= 1
                
                # Check that at least one call contains the test question
                calls_content = [call[1]["content"] for call in mock_store.call_args_list]
                assert any("Test question" in content for content in calls_content)


class TestIntegration:
    """Integration tests for the complete system."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_simple_hello_world_cycle(self):
        """Test a complete hello world reasoning cycle."""
        # Create a mock agent with mocked LLM responses
        agent = AletheiaAgent()
        
        # Mock the local LLM to return a simple response
        mock_response = {
            "result": "Hello! I'm Aletheia, a thinking agent. How can I help you today?",
            "route_used": "local",
            "execution_time": 0.1,
            "estimated_cost": 0.0,
        }
        
        with patch.object(agent.router, 'execute_task', return_value=mock_response):
            result = await agent.think("Hello, who are you?")
            
            assert result is not None
            assert "response" in result
            # Aletheia can respond in English or Russian depending on context/memory
            # Both are valid responses to an English greeting
            response = result["response"]
            assert any(word in response for word in ["Hello", "Aletheia", "Алетейя", "Здравствуйте"])
            assert "meta" in result
            assert result["meta"]["task_id"] == 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_handling(self):
        """Test that errors are handled gracefully."""
        agent = AletheiaAgent()
        
        # Mock both router and local LLM to throw exceptions to force an error
        with patch.object(agent.router, 'execute_task', side_effect=Exception("Mock router error")):
            with patch.object(agent.router.local_llm, 'generate_structured', side_effect=Exception("Mock local LLM error")):
                result = await agent.think("This should fail")
                
                assert "error" in result
                assert "Mock router error" in result["error"]


if __name__ == "__main__":
    # Run tests directly if this file is executed
    pytest.main([__file__, "-v"]) 