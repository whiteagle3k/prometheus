"""
Test Universal Agent Registry

Tests the new registry system that supports multiple entities
instead of the old singleton pattern.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

# Mock entities for testing
class MockAletheiaEntity:
    def __init__(self):
        self.name = "aletheia"
        
    async def think(self, message, user_id=None):
        return f"Aletheia: {message}"
    
    async def save_state(self):
        pass
    
    async def close(self):
        pass


class MockPrometheusEntity:
    def __init__(self):
        self.name = "prometheus"
        
    async def think(self, message, user_id=None):
        return f"Prometheus: {message}"
    
    async def save_state(self):
        pass
    
    async def close(self):
        pass


@pytest.fixture
def mock_importlib(monkeypatch):
    """Mock importlib to return test entities."""
    mock_modules = {
        "entities.aletheia": Mock(AletheiaEntity=MockAletheiaEntity),
        "entities.prometheus": Mock(PrometheusEntity=MockPrometheusEntity),
    }
    
    def mock_import_module(module_path):
        if module_path in mock_modules:
            return mock_modules[module_path]
        raise ImportError(f"No module named '{module_path}'")
    
    monkeypatch.setattr("importlib.import_module", mock_import_module)


@pytest.mark.asyncio
async def test_registry_get_agent_single_entity():
    """Test getting a single agent from registry."""
    with patch('importlib.import_module') as mock_import:
        mock_import.return_value = Mock(AletheiaEntity=MockAletheiaEntity)
        
        from core.runtime.registry import get_agent, _registry
        
        # Clear registry
        _registry._instances.clear()
        
        # Get agent
        agent = await get_agent("aletheia")
        
        assert agent is not None
        assert agent.name == "aletheia"
        
        # Verify it's cached
        agent2 = await get_agent("aletheia")
        assert agent is agent2  # Same instance


@pytest.mark.asyncio
async def test_registry_multiple_entities():
    """Test managing multiple entities simultaneously."""
    with patch('importlib.import_module') as mock_import:
        modules = {
            "entities.aletheia": Mock(AletheiaEntity=MockAletheiaEntity),
            "entities.prometheus": Mock(PrometheusEntity=MockPrometheusEntity)
        }
        mock_import.side_effect = lambda path: modules[path]
        
        from core.runtime.registry import get_agent, get_running_agents, _registry
        
        # Clear registry
        _registry._instances.clear()
        
        # Get multiple agents
        aletheia = await get_agent("aletheia")
        prometheus = await get_agent("prometheus")
        
        assert aletheia is not None
        assert prometheus is not None
        assert aletheia != prometheus
        
        # Check running agents
        running = get_running_agents()
        assert "aletheia" in running
        assert "prometheus" in running
        assert len(running) == 2


@pytest.mark.asyncio
async def test_registry_entity_not_found():
    """Test handling of non-existent entities."""
    with patch('importlib.import_module') as mock_import:
        mock_import.side_effect = ImportError("No module named 'entities.nonexistent'")
        
        from core.runtime.registry import get_agent, _registry
        
        # Clear registry
        _registry._instances.clear()
        
        # Try to get non-existent entity
        with pytest.raises(ImportError):
            await get_agent("nonexistent")


@pytest.mark.asyncio
async def test_registry_shutdown_single_agent():
    """Test shutting down a single agent."""
    with patch('importlib.import_module') as mock_import:
        mock_import.return_value = Mock(AletheiaEntity=MockAletheiaEntity)
        
        from core.runtime.registry import get_agent, shutdown_agent, get_running_agents, _registry
        
        # Clear registry
        _registry._instances.clear()
        
        # Get agent
        agent = await get_agent("aletheia")
        assert "aletheia" in get_running_agents()
        
        # Shutdown agent
        success = await shutdown_agent("aletheia")
        assert success
        assert "aletheia" not in get_running_agents()


@pytest.mark.asyncio
async def test_registry_shutdown_all_agents():
    """Test shutting down all agents."""
    with patch('importlib.import_module') as mock_import:
        modules = {
            "entities.aletheia": Mock(AletheiaEntity=MockAletheiaEntity),
            "entities.prometheus": Mock(PrometheusEntity=MockPrometheusEntity)
        }
        mock_import.side_effect = lambda path: modules[path]
        
        from core.runtime.registry import get_agent, shutdown_all_agents, get_running_agents, _registry
        
        # Clear registry
        _registry._instances.clear()
        
        # Get multiple agents
        await get_agent("aletheia")
        await get_agent("prometheus")
        
        assert len(get_running_agents()) == 2
        
        # Shutdown all
        success = await shutdown_all_agents()
        assert success
        assert len(get_running_agents()) == 0


@pytest.mark.asyncio
async def test_registry_concurrent_access():
    """Test concurrent access to registry."""
    with patch('importlib.import_module') as mock_import:
        mock_import.return_value = Mock(AletheiaEntity=MockAletheiaEntity)
        
        from core.runtime.registry import get_agent, _registry
        
        # Clear registry
        _registry._instances.clear()
        
        # Create multiple concurrent requests for the same entity
        async def get_agent_task():
            return await get_agent("aletheia")
        
        # Run 10 concurrent requests
        tasks = [get_agent_task() for _ in range(10)]
        agents = await asyncio.gather(*tasks)
        
        # All should be the same instance
        first_agent = agents[0]
        for agent in agents:
            assert agent is first_agent


@pytest.mark.asyncio
async def test_registry_stats():
    """Test registry statistics."""
    with patch('importlib.import_module') as mock_import:
        mock_import.return_value = Mock(AletheiaEntity=MockAletheiaEntity)
        
        from core.runtime.registry import get_registry_stats, get_agent, _registry
        
        # Clear registry
        _registry._instances.clear()
        
        # Initial stats
        stats = get_registry_stats()
        assert stats["agent_count"] == 0
        assert stats["registry_status"] == "empty"
        
        # Add agent
        await get_agent("aletheia")
        
        stats = get_registry_stats()
        assert stats["agent_count"] == 1
        assert stats["registry_status"] == "active"
        assert "aletheia" in stats["running_agents"]


@pytest.mark.asyncio
async def test_lifecycle_manager():
    """Test lifecycle manager with multiple entities."""
    with patch('importlib.import_module') as mock_import:
        mock_import.return_value = Mock(AletheiaEntity=MockAletheiaEntity)
        
        from core.runtime.lifecycle import startup_system, shutdown_system, get_system_status
        
        # Test startup (only test with aletheia to avoid missing entity errors)
        success = await startup_system(["aletheia"])
        assert success
        
        # Check status
        status = get_system_status()
        assert status["agent_count"] >= 1
        
        # Test shutdown
        success = await shutdown_system()
        assert success


@pytest.mark.asyncio
async def test_entity_independence():
    """Test that entities operate independently."""
    with patch('importlib.import_module') as mock_import:
        modules = {
            "entities.aletheia": Mock(AletheiaEntity=MockAletheiaEntity),
            "entities.prometheus": Mock(PrometheusEntity=MockPrometheusEntity)
        }
        mock_import.side_effect = lambda path: modules[path]
        
        from core.runtime.registry import get_agent, _registry
        
        # Clear registry
        _registry._instances.clear()
        
        # Get agents
        aletheia = await get_agent("aletheia")
        prometheus = await get_agent("prometheus")
        
        # Test independent operations
        aletheia_response = await aletheia.think("Hello")
        prometheus_response = await prometheus.think("Hello")
        
        assert aletheia_response == "Aletheia: Hello"
        assert prometheus_response == "Prometheus: Hello"
        assert aletheia_response != prometheus_response


# Parametrized tests for entity compatibility
@pytest.mark.parametrize("entity_name", ["aletheia"])  # Only test aletheia for now
@pytest.mark.asyncio
async def test_entity_basic_operations(entity_name):
    """Test basic operations work for any entity."""
    with patch('importlib.import_module') as mock_import:
        mock_import.return_value = Mock(AletheiaEntity=MockAletheiaEntity)
        
        from core.runtime.registry import get_agent, _registry
        
        # Clear registry
        _registry._instances.clear()
        
        # Get agent
        agent = await get_agent(entity_name)
        
        # Test basic functionality
        response = await agent.think("Test message")
        assert entity_name.capitalize() in response
        assert "Test message" in response
        
        # Test state operations
        await agent.save_state()  # Should not raise
        await agent.close()       # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 