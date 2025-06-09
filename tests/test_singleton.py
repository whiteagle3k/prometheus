"""
Test Universal Agent Registry

Tests the new registry system that supports multiple entities
instead of the old singleton pattern.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest


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


# Mock register functions
def mock_aletheia_register():
    return {"name": "Aletheia", "id": "aletheia", "class": MockAletheiaEntity}


def mock_prometheus_register():
    return {"name": "Prometheus", "id": "prometheus", "class": MockPrometheusEntity}


# Mock discovery function
def mock_discover_entities():
    """Mock implementation of discover_entities that returns valid test entities."""
    return {
        "aletheia": {
            "id": "aletheia",
            "name": "Aletheia",
            "class": MockAletheiaEntity,
            "module_path": "entities.aletheia",
            "description": "Mock Aletheia entity"
        },
        "prometheus": {
            "id": "prometheus",
            "name": "Prometheus",
            "class": MockPrometheusEntity,
            "module_path": "entities.prometheus",
            "description": "Mock Prometheus entity"
        }
    }


@pytest.fixture()
def mock_importlib(monkeypatch):
    """Mock importlib to return test entities."""
    mock_modules = {
        "entities.aletheia": Mock(AletheiaEntity=MockAletheiaEntity),
        "entities.prometheus": Mock(PrometheusEntity=MockPrometheusEntity),
    }

    def mock_import_module(module_path):
        if module_path in mock_modules:
            return mock_modules[module_path]
        msg = f"No module named '{module_path}'"
        raise ImportError(msg)

    monkeypatch.setattr("importlib.import_module", mock_import_module)


@pytest.mark.asyncio()
async def test_registry_get_agent_single_entity():
    """Test getting a single agent from registry."""
    with patch("entities.discover_entities", return_value=mock_discover_entities()):
        from core.runtime.registry import _registry, get_agent

        # Clear registry
        _registry._instances.clear()

        # Get agent
        agent = await get_agent("aletheia")

        assert agent is not None
        assert agent.name == "aletheia"

        # Verify it's cached
        agent2 = await get_agent("aletheia")
        assert agent is agent2  # Same instance


@pytest.mark.asyncio()
async def test_registry_multiple_entities():
    """Test managing multiple entities simultaneously."""
    with patch("entities.discover_entities", return_value=mock_discover_entities()):
        from core.runtime.registry import _registry, get_agent, get_running_agents

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


@pytest.mark.asyncio()
async def test_registry_entity_not_found():
    """Test handling of non-existent entities."""
    with patch("entities.discover_entities", return_value=mock_discover_entities()):
        from core.runtime.registry import _registry, get_agent

        # Clear registry
        _registry._instances.clear()

        # Try to get non-existent entity
        with pytest.raises(ImportError):
            await get_agent("nonexistent")


@pytest.mark.asyncio()
async def test_registry_shutdown_single_agent():
    """Test shutting down a single agent."""
    with patch("entities.discover_entities", return_value=mock_discover_entities()):
        from core.runtime.registry import (
            _registry,
            get_agent,
            get_running_agents,
            shutdown_agent,
        )

        # Clear registry
        _registry._instances.clear()

        # Get agent
        await get_agent("aletheia")
        assert "aletheia" in get_running_agents()

        # Shutdown agent
        success = await shutdown_agent("aletheia")
        assert success
        assert "aletheia" not in get_running_agents()


@pytest.mark.asyncio()
async def test_registry_shutdown_all_agents():
    """Test shutting down all agents."""
    with patch("entities.discover_entities", return_value=mock_discover_entities()):
        from core.runtime.registry import (
            _registry,
            get_agent,
            get_running_agents,
            shutdown_all_agents,
        )

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


@pytest.mark.asyncio()
async def test_registry_concurrent_access():
    """Test concurrent access to registry."""
    with patch("entities.discover_entities", return_value=mock_discover_entities()):
        from core.runtime.registry import _registry, get_agent

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


@pytest.mark.asyncio()
async def test_registry_stats():
    """Test registry statistics."""
    with patch("entities.discover_entities", return_value=mock_discover_entities()):
        from core.runtime.registry import _registry, get_agent, get_registry_stats

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


@pytest.mark.asyncio()
async def test_lifecycle_manager():
    """Test lifecycle manager with multiple entities."""
    with patch("entities.discover_entities", return_value=mock_discover_entities()):
        from core.runtime.lifecycle import (
            get_system_status,
            shutdown_system,
            startup_system,
        )

        # Test startup (only test with aletheia to avoid missing entity errors)
        success = await startup_system(["aletheia"])
        assert success
        status = get_system_status()
        assert len(status["running_agents"]) > 0
        assert status["agent_count"] == 1
        assert status["shutdown_initiated"] is False

        # Test shutdown
        await shutdown_system()
        status = get_system_status()
        assert len(status["running_agents"]) == 0
        assert status["agent_count"] == 0
        assert status["shutdown_initiated"] is True


@pytest.mark.asyncio()
async def test_entity_independence():
    """Test that multiple entity instances are independent."""
    with patch("entities.discover_entities", return_value=mock_discover_entities()):
        from core.runtime.registry import _registry, get_agent

        # Clear registry
        _registry._instances.clear()

        # Get independent agents
        aletheia = await get_agent("aletheia")
        prometheus = await get_agent("prometheus")

        # Test independence of operation
        msg1 = "Hello"
        msg2 = "Hi there"

        response1 = await aletheia.think(msg1)
        response2 = await prometheus.think(msg2)

        assert "Aletheia" in response1
        assert "Hello" in response1
        assert "Prometheus" in response2
        assert "Hi there" in response2


@pytest.mark.parametrize("entity_name", ["aletheia"])  # Only test aletheia for now
@pytest.mark.asyncio()
async def test_entity_basic_operations(entity_name):
    """Test basic entity operations."""
    with patch("entities.discover_entities", return_value=mock_discover_entities()):
        from core.runtime.registry import _registry, get_agent

        # Clear registry
        _registry._instances.clear()

        # Get agent
        agent = await get_agent(entity_name)

        # Test agent operations
        assert agent is not None
        assert agent.name == entity_name

        # Test basic interaction
        response = await agent.think("Hello")
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
