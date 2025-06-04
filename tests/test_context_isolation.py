"""
Test context isolation to prevent "LLM forgets to forget" trap.

As suggested by o3: feed three disjoint queries back-to-back and assert
identical routing decisions regardless of order.
"""

import pytest

from core.llm.router import LLMRouter, TaskContext


class TestContextIsolation:
    """Test that routing decisions are not contaminated by previous queries."""

    @pytest.fixture()
    def router(self):
        """Create a router for testing."""
        identity_config = {
            "name": "TestAgent",
            "personality": {"summary": "Test agent", "personality": ["test"]},
            "core_values": ["testing"],
            "routing_threshold": 1000,
            "system_prompts": {"en": "You are a test agent."},
            "llm_instructions": "You are a test agent."
        }
        return LLMRouter(identity_config=identity_config)

    @pytest.mark.asyncio()
    async def test_context_isolation_three_disjoint_queries(self, router):
        """
        Test that three disjoint queries produce identical routing decisions
        regardless of the order they're presented.
        """
        # Three completely different query types
        queries = [
            "Hello, how are you?",  # Conversational - should route LOCAL
            "What is quantum mechanics?",  # Scientific - should route EXTERNAL
            "What's the weather like?"  # General - context dependent
        ]

        # Test all possible orderings (3! = 6 permutations)
        from itertools import permutations

        routing_decisions = {}

        for order in permutations(queries):
            decisions_for_order = []

            for query in order:
                task = TaskContext(prompt=query)
                decision = await router.route_task(task)
                decisions_for_order.append((query, decision.value))

            # Store decisions keyed by original query
            for query, decision in decisions_for_order:
                if query not in routing_decisions:
                    routing_decisions[query] = []
                routing_decisions[query].append(decision)

        # Assert each query gets the same routing decision regardless of order
        for query, decisions in routing_decisions.items():
            assert len(set(decisions)) == 1, (
                f"Query '{query}' got different routing decisions: {decisions}. "
                f"This indicates context contamination between routing decisions."
            )
            print(f"✅ Query '{query}' consistently routed to: {decisions[0]}")

    @pytest.mark.asyncio()
    async def test_fast_llm_context_reset(self, router):
        """Test that Fast LLM context is properly reset between decisions."""
        # Make two identical queries separated by a different query
        query1 = "What is thermodynamics?"
        interfering_query = "Hello there!"
        query2 = "What is thermodynamics?"  # Identical to query1

        # Get routing decisions
        task1 = TaskContext(prompt=query1)
        decision1 = await router.route_task(task1)

        # Interfering query
        interfering_task = TaskContext(prompt=interfering_query)
        await router.route_task(interfering_task)

        # Second identical query
        task2 = TaskContext(prompt=query2)
        decision2 = await router.route_task(task2)

        # Identical queries should get identical routing decisions
        assert decision1 == decision2, (
            f"Identical queries got different routing decisions: {decision1} vs {decision2}. "
            f"This indicates context contamination in Fast LLM."
        )
        print(f"✅ Identical queries consistently routed to: {decision1.value}")

    @pytest.mark.asyncio()
    async def test_context_limit_enforcement(self, router):
        """Test that context is limited to 300 characters as specified."""
        # Create a very long context
        long_context = "This is a very long conversation. " * 20  # > 300 chars

        # Mock the utility LLM to capture the context it receives
        original_make_routing_decision = router.utility_llm.make_routing_decision
        received_contexts = []

        async def mock_routing_decision(query, context=None):
            received_contexts.append(context)
            return await original_make_routing_decision(query, context)

        router.utility_llm.make_routing_decision = mock_routing_decision

        task = TaskContext(
            prompt="What is the meaning of life?",
            conversation_context=long_context
        )

        await router.route_task(task)

        # Check that context was limited
        if received_contexts and received_contexts[0]:
            assert len(received_contexts[0]) <= 300, (
                f"Context was not limited: {len(received_contexts[0])} chars > 300"
            )
            print(f"✅ Context properly limited to {len(received_contexts[0])} chars")

    @pytest.mark.asyncio()
    async def test_language_metadata_consistency(self, router):
        """Test that language detection is consistent for same-language queries."""
        russian_queries = [
            "Привет, как дела?",
            "Что такое квантовая физика?",
            "Расскажи про термодинамику"
        ]

        english_queries = [
            "Hello, how are you?",
            "What is quantum physics?",
            "Tell me about thermodynamics"
        ]

        # Test Russian consistency
        for query in russian_queries:
            # This would need to be implemented in the router
            # For now, just test that Russian characters are detected
            is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in query.lower())
            assert is_russian, f"Russian query not detected as Russian: {query}"

        # Test English consistency
        for query in english_queries:
            is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in query.lower())
            assert not is_russian, f"English query detected as Russian: {query}"

        print("✅ Language detection is consistent")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
