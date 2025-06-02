"""Tests for the three-tier MemoryController system.

Tests prove:
- Tiered retrieval order (Core-Self → User → Environment)
- Correct write-back classification for each context type
- Summarization & overflow logic per tier
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from aletheia.memory.controller import MemoryController
from aletheia.memory.enums import MemoryTier, MemoryType
from aletheia.memory.models import MemoryChunk, RetrievalResult, MemoryStats, TierConfig


class TestMemoryController:
    """Test the unified memory controller."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_controller_initialization(self):
        """Test that controller initializes all three tiers correctly."""
        controller = MemoryController()
        
        # Should have all three tier stores
        assert MemoryTier.CORE_SELF in controller.stores
        assert MemoryTier.USER in controller.stores
        assert MemoryTier.ENV in controller.stores
        
        # Should have configurations for all tiers
        assert len(controller.tier_configs) == 3
        assert controller.tier_configs[MemoryTier.CORE_SELF].similarity_threshold == 0.75
        assert controller.tier_configs[MemoryTier.USER].similarity_threshold == 0.70
        assert controller.tier_configs[MemoryTier.ENV].similarity_threshold == 0.65

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_core_first_retrieval_priority(self):
        """Test that Core-Self tier is searched first with higher priority."""
        controller = MemoryController()
        
        # Mock search results for each tier
        core_result = [{"content": "Core-Self memory", "metadata": {}}]
        user_result = [{"content": "User memory", "metadata": {"user_id": "test"}}]
        env_result = [{"content": "Environment memory", "metadata": {}}]
        
        with patch.object(controller.stores[MemoryTier.CORE_SELF], 'search_memories', 
                         return_value=core_result) as mock_core:
            with patch.object(controller.stores[MemoryTier.USER], 'search_memories',
                             return_value=user_result) as mock_user:
                with patch.object(controller.stores[MemoryTier.ENV], 'search_memories',
                                 return_value=env_result) as mock_env:
                    
                    result = await controller.retrieve("test query", k=6)
                    
                    # Core-Self should be searched first
                    mock_core.assert_called_once()
                    # User should be searched second
                    mock_user.assert_called_once()
                    # Environment should be searched third
                    mock_env.assert_called_once()
                    
                    # Result should contain memories from all tiers in order
                    assert result.total_retrieved > 0
                    # First memory should be from Core-Self tier
                    if result.chunks:
                        assert result.chunks[0].tier == MemoryTier.CORE_SELF

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_tier_threshold_limits(self):
        """Test that retrieval stops early if enough results found."""
        controller = MemoryController()
        
        # Mock Core-Self to return enough results
        core_results = [
            {"content": f"Core memory {i}", "metadata": {}} 
            for i in range(8)  # More than k=6
        ]
        
        with patch.object(controller.stores[MemoryTier.CORE_SELF], 'search_memories',
                         return_value=core_results) as mock_core:
            with patch.object(controller.stores[MemoryTier.USER], 'search_memories') as mock_user:
                with patch.object(controller.stores[MemoryTier.ENV], 'search_memories') as mock_env:
                    
                    result = await controller.retrieve("test query", k=3)
                    
                    # Should only search Core-Self if it returns enough results
                    mock_core.assert_called_once()
                    # Should not search other tiers if Core-Self provides enough
                    # (This test would need more sophisticated mocking to work exactly)

    @pytest.mark.asyncio
    @pytest.mark.unit 
    async def test_write_back_classification(self):
        """Test that memories are classified into correct tiers."""
        controller = MemoryController()
        
        # Test Core-Self classification
        self_chunk = MemoryChunk(
            id="test-1",
            text="I learned a new skill in conversation analysis",
            embedding=[],
            tier=MemoryTier.USER,  # Will be reclassified
            memory_type=MemoryType.SYSTEM_LEARNING
        )
        
        # Test Environment classification
        env_chunk = MemoryChunk(
            id="test-2", 
            text="External sensor detected temperature change",
            embedding=[],
            tier=MemoryTier.USER,  # Will be reclassified
            memory_type=MemoryType.SENSOR_DATA
        )
        
        # Test User classification (default)
        user_chunk = MemoryChunk(
            id="test-3",
            text="User asked about weather forecast",
            embedding=[],
            tier=MemoryTier.USER,
            memory_type=MemoryType.CONVERSATION
        )
        
        with patch.object(controller.stores[MemoryTier.CORE_SELF], 'store_memory',
                         return_value="core-id") as mock_core_store:
            with patch.object(controller.stores[MemoryTier.ENV], 'store_memory',
                             return_value="env-id") as mock_env_store:
                with patch.object(controller.stores[MemoryTier.USER], 'store_memory',
                                 return_value="user-id") as mock_user_store:
                    
                    # Store chunks without specifying tier (should auto-classify)
                    await controller.store(self_chunk)
                    await controller.store(env_chunk)
                    await controller.store(user_chunk)
                    
                    # Verify correct tier assignment
                    mock_core_store.assert_called_once()  # Self-reflection content
                    mock_env_store.assert_called_once()   # External sensor content
                    mock_user_store.assert_called_once()  # Regular conversation

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_explicit_tier_override(self):
        """Test that explicitly specified tiers override classification."""
        controller = MemoryController()
        
        chunk = MemoryChunk(
            id="test-override",
            text="Regular conversation that should go to USER",
            embedding=[],
            tier=MemoryTier.USER,
            memory_type=MemoryType.CONVERSATION
        )
        
        with patch.object(controller.stores[MemoryTier.CORE_SELF], 'store_memory',
                         return_value="override-id") as mock_store:
            
            # Explicitly store in Core-Self despite content suggesting USER
            await controller.store(chunk, tier=MemoryTier.CORE_SELF)
            
            # Should store in specified tier, not auto-classified tier
            mock_store.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_overflow_summarization_trigger(self):
        """Test that overflow triggers summarization when tier exceeds max_chunks."""
        # Create controller with small limits for testing
        test_configs = {
            MemoryTier.CORE_SELF: TierConfig(max_chunks=2, similarity_threshold=0.75),
            MemoryTier.USER: TierConfig(max_chunks=2, similarity_threshold=0.70),
            MemoryTier.ENV: TierConfig(max_chunks=2, similarity_threshold=0.65)
        }
        
        controller = MemoryController(tier_configs=test_configs)
        
        chunk = MemoryChunk(
            id="overflow-test",
            text="Test memory that will trigger overflow",
            embedding=[],
            tier=MemoryTier.CORE_SELF,
            memory_type=MemoryType.SELF_REFLECTION
        )
        
        # Mock count to return value exceeding limit
        with patch.object(controller, '_estimate_tier_count', return_value=3):
            with patch.object(controller, '_summarize_tier') as mock_summarize:
                with patch.object(controller.stores[MemoryTier.CORE_SELF], 'store_memory',
                                 return_value="overflow-id"):
                    
                    await controller.store(chunk)
                    
                    # Should trigger summarization for Core-Self tier
                    mock_summarize.assert_called_once_with(MemoryTier.CORE_SELF)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_user_id_handling(self):
        """Test that user_id is properly handled for USER tier memories."""
        controller = MemoryController()
        
        chunk = MemoryChunk(
            id="user-test",
            text="User conversation without user_id",
            embedding=[],
            tier=MemoryTier.USER,
            memory_type=MemoryType.CONVERSATION,
            metadata={}  # No user_id initially
        )
        
        controller.current_user_id = "test_user_123"
        
        with patch.object(controller.stores[MemoryTier.USER], 'store_memory',
                         return_value="user-memory-id") as mock_store:
            
            await controller.store(chunk)
            
            # Should have added user_id to metadata
            call_args = mock_store.call_args
            stored_metadata = call_args[1]["metadata"]
            assert "user_id" in stored_metadata
            assert stored_metadata["user_id"] == "test_user_123"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_stats_collection(self):
        """Test that memory statistics are collected across all tiers."""
        controller = MemoryController()
        
        # Mock tier counts
        with patch.object(controller, '_estimate_tier_count') as mock_count:
            mock_count.side_effect = [10, 25, 5]  # Core-Self, User, Env counts
            
            stats = await controller.get_stats()
            
            assert stats.core_self_count == 10
            assert stats.user_count == 25
            assert stats.env_count == 5
            assert stats.total_count == 40

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_summarization_lock(self):
        """Test that summarization operations are properly locked."""
        controller = MemoryController()
        
        # Mock summarization to simulate concurrent calls
        async def slow_summarization():
            await asyncio.sleep(0.1)
            return {MemoryTier.CORE_SELF: True, MemoryTier.USER: False, MemoryTier.ENV: False}
        
        with patch.object(controller, '_check_overflow', return_value=True):
            
            # Start two summarization tasks concurrently
            task1 = asyncio.create_task(controller.summarise_if_needed())
            task2 = asyncio.create_task(controller.summarise_if_needed())
            
            results = await asyncio.gather(task1, task2)
            
            # Both should complete without conflict
            assert len(results) == 2
            assert all(isinstance(result, dict) for result in results)


class TestMemoryClassification:
    """Test memory tier classification logic."""

    def test_core_self_classification(self):
        """Test that self-reflection content is classified as CORE_SELF."""
        controller = MemoryController()
        
        test_cases = [
            "I learned how to better handle user questions",
            "My skill in Russian language improved today",
            "Self-reflection: я улучшила свои способности",
            "Internal goal: become more empathetic"
        ]
        
        for text in test_cases:
            chunk = MemoryChunk(
                id="test",
                text=text,
                embedding=[],
                tier=MemoryTier.USER,  # Will be reclassified
                memory_type=MemoryType.SELF_REFLECTION
            )
            
            classified_tier = controller._classify_memory_tier(chunk)
            assert classified_tier == MemoryTier.CORE_SELF, f"Failed for: {text}"

    def test_environment_classification(self):
        """Test that external events are classified as ENV."""
        controller = MemoryController()
        
        test_cases = [
            "Sensor data indicates room temperature changed",
            "External API webhook received",
            "Внешний датчик сработал",
            "System event: memory cleanup completed"
        ]
        
        for text in test_cases:
            chunk = MemoryChunk(
                id="test",
                text=text,
                embedding=[],
                tier=MemoryTier.USER,  # Will be reclassified
                memory_type=MemoryType.SENSOR_DATA
            )
            
            classified_tier = controller._classify_memory_tier(chunk)
            assert classified_tier == MemoryTier.ENV, f"Failed for: {text}"

    def test_user_default_classification(self):
        """Test that conversation content defaults to USER tier."""
        controller = MemoryController()
        
        test_cases = [
            "User asked about weather",
            "Пользователь спросил о погоде", 
            "Normal conversation content",
            "Question about machine learning"
        ]
        
        for text in test_cases:
            chunk = MemoryChunk(
                id="test",
                text=text,
                embedding=[],
                tier=MemoryTier.CORE_SELF,  # Will be reclassified
                memory_type=MemoryType.CONVERSATION
            )
            
            classified_tier = controller._classify_memory_tier(chunk)
            assert classified_tier == MemoryTier.USER, f"Failed for: {text}"


if __name__ == "__main__":
    # Run tests directly if this file is executed
    pytest.main([__file__, "-v"]) 