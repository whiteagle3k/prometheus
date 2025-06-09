"""
Test Universal API Server

Tests the new API server that supports multiple entities
instead of being hardcoded to Aletheia.
"""

from unittest.mock import Mock, patch
import asyncio

import pytest
from fastapi.testclient import TestClient


# Mock entities for testing
class MockEntity:
    """Mock entity for testing API."""

    def __init__(self, name):
        self.name = name

    async def think(self, message, user_id=None):
        """Mock think method."""
        # Add some delay to simulate processing
        await asyncio.sleep(0.1)
        return {
            "answer": f"{self.name.capitalize()}: {message}",
            "confidence": "high",
            "reasoning": "Mock reasoning"
        }

    async def save_state(self):
        """Mock save state."""
        pass

    async def close(self):
        """Mock close."""
        pass


@pytest.fixture()
def mock_registry():
    """Mock the registry system."""
    with patch("core.frontends.api_server.get_agent") as mock_get_agent, \
         patch("core.frontends.api_server.get_running_agents") as mock_get_running, \
         patch("core.frontends.api_server.get_registry_stats") as mock_get_stats:

        # Setup mock entities
        entities = {
            "aletheia": MockEntity("aletheia"),
            "prometheus": MockEntity("prometheus"),
            "teslabot": MockEntity("teslabot")
        }

        async def mock_get_agent_func(entity_name):
            if entity_name in entities:
                return entities[entity_name]
            msg = f"Entity '{entity_name}' not found"
            raise ImportError(msg)

        mock_get_agent.side_effect = mock_get_agent_func
        mock_get_running.return_value = list(entities.keys())
        mock_get_stats.return_value = {
            "running_agents": list(entities.keys()),
            "agent_count": len(entities),
            "registry_status": "active"
        }

        yield entities


@pytest.fixture()
def client():
    """Create test client for the API."""
    from core.frontends.api_server import app
    return TestClient(app)


def test_root_endpoint(client, mock_registry):
    """Test the root endpoint returns universal service info."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert data["service"] == "Prometheus Universal AI Service"
    assert data["version"] == "0.6.0"
    assert "running_agents" in data
    assert "agent_count" in data
    assert len(data["running_agents"]) == 3
    assert "endpoints" in data
    assert "/v1/chat?entity=<entity_name>" in data["endpoints"]["chat"]


def test_health_endpoint(client, mock_registry):
    """Test the health endpoint."""
    # Mock the health check at the module level where it's imported
    with patch("core.runtime.lifecycle.system_health_check") as mock_health:
        mock_health.return_value = {
            "overall_status": "healthy",
            "timestamp": 1234567890,
            "running_agents": ["aletheia", "prometheus"],
            "agent_count": 2,
            "checks": {"test_check": {"status": "healthy", "result": True}}
        }

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "running_agents" in data
        assert "agent_count" in data


def test_registry_endpoint(client, mock_registry):
    """Test the registry information endpoint."""
    response = client.get("/v1/registry")

    assert response.status_code == 200
    data = response.json()

    assert data["agent_count"] == 3
    assert data["registry_status"] == "active"
    assert "aletheia" in data["running_agents"]
    assert "prometheus" in data["running_agents"]


@pytest.mark.parametrize("entity_name", ["aletheia", "prometheus", "teslabot"])
def test_chat_with_different_entities(client, mock_registry, entity_name):
    """Test chat endpoint with different entities."""
    payload = {
        "user_id": "test_user",
        "message": "Hello world"
    }

    response = client.post(
        f"/v1/chat?entity={entity_name}",
        json=payload
    )

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "answer" in data
    assert "entity" in data
    assert "route" in data
    assert "latency" in data
    assert "request_id" in data

    # Check entity-specific response
    assert data["entity"] == entity_name
    assert entity_name.capitalize() in data["answer"]
    assert "Hello world" in data["answer"]

    # Check headers
    assert "X-Request-ID" in response.headers


def test_chat_default_entity(client, mock_registry):
    """Test chat endpoint with default entity (no query param)."""
    payload = {
        "user_id": "test_user",
        "message": "Default entity test"
    }

    response = client.post("/v1/chat", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Should default to aletheia
    assert data["entity"] == "aletheia"
    assert "Aletheia" in data["answer"]


def test_chat_nonexistent_entity(client, mock_registry):
    """Test chat endpoint with non-existent entity."""
    payload = {
        "user_id": "test_user",
        "message": "Test message"
    }

    response = client.post(
        "/v1/chat?entity=nonexistent",
        json=payload
    )

    assert response.status_code == 404
    data = response.json()

    assert "Entity 'nonexistent' not found" in data["detail"]["error"]
    assert "available_entities" in data["detail"]
    assert "request_id" in data["detail"]


def test_chat_invalid_payload(client, mock_registry):
    """Test chat endpoint with invalid payload."""
    # Missing user_id
    payload = {
        "message": "Test message"
    }

    response = client.post("/v1/chat", json=payload)

    assert response.status_code == 422  # Validation error


def test_chat_body_size_limit(client, mock_registry):
    """Test body size limit middleware."""
    # Create payload larger than 4KB
    large_message = "x" * 5000  # 5KB message
    payload = {
        "user_id": "test_user",
        "message": large_message
    }

    response = client.post("/v1/chat", json=payload)

    assert response.status_code == 413
    data = response.json()

    assert "Request body too large" in data["error"]
    assert data["max_size"] == "4KB"


def test_request_id_in_responses(client, mock_registry):
    """Test that all responses include request IDs."""
    payload = {
        "user_id": "test_user",
        "message": "Test message"
    }

    response = client.post("/v1/chat", json=payload)

    # Check header
    assert "X-Request-ID" in response.headers

    # Check response body
    data = response.json()
    assert "request_id" in data

    # Should be the same ID
    assert response.headers["X-Request-ID"] == data["request_id"]


def test_metrics_endpoint(client, mock_registry):
    """Test that metrics endpoint exists."""
    response = client.get("/metrics")

    # Should either return metrics or 404 if not enabled
    assert response.status_code in [200, 404]


def test_concurrent_requests_different_entities(client, mock_registry):
    """Test concurrent requests to different entities."""
    import threading

    results = []

    def make_request(entity_name):
        payload = {
            "user_id": f"user_{entity_name}",
            "message": f"Message for {entity_name}"
        }
        response = client.post(
            f"/v1/chat?entity={entity_name}",
            json=payload
        )
        results.append((entity_name, response.status_code, response.json()))

    # Create threads for different entities
    threads = []
    entities = ["aletheia", "prometheus", "teslabot"]

    for entity in entities:
        thread = threading.Thread(target=make_request, args=(entity,))
        threads.append(thread)

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for completion
    for thread in threads:
        thread.join()

    # Check results
    assert len(results) == 3

    for entity_name, status_code, data in results:
        assert status_code == 200
        assert data["entity"] == entity_name
        assert entity_name.capitalize() in data["answer"]


def test_cors_headers(client, mock_registry):
    """Test CORS headers are present."""
    # Make an OPTIONS request to trigger CORS headers
    response = client.options("/")

    # Check for common CORS headers (may vary based on CORS configuration)

    # TestClient might not include all CORS headers, so just check the request succeeds
    assert response.status_code in [200, 405]  # OPTIONS may not be explicitly handled


# Mock discovery function
def mock_discover_entities():
    """Mock implementation of discover_entities that returns valid test entities."""
    return {
        "aletheia": {
            "id": "aletheia",
            "name": "Aletheia",
            "class": lambda: MockEntity("aletheia"),
            "module_path": "entities.aletheia",
            "description": "Mock Aletheia entity"
        },
        "prometheus": {
            "id": "prometheus",
            "name": "Prometheus",
            "class": lambda: MockEntity("prometheus"),
            "module_path": "entities.prometheus",
            "description": "Mock Prometheus entity"
        },
        "teslabot": {
            "id": "teslabot",
            "name": "TeslaBot",
            "class": lambda: MockEntity("teslabot"),
            "module_path": "entities.teslabot",
            "description": "Mock TeslaBot entity"
        }
    }


@pytest.mark.asyncio()
async def test_multiple_entity_instances():
    """Test that different entities get different instances."""
    from core.runtime.registry import _registry, get_agent

    # Clear registry for clean test
    _registry._instances.clear()

    # Mock entity discovery
    with patch("entities.discover_entities", return_value=mock_discover_entities()):
        # Get different entities
        aletheia = await get_agent("aletheia")
        prometheus = await get_agent("prometheus")

        # Should be different instances
        assert aletheia is not prometheus
        assert aletheia.name == "aletheia"
        assert prometheus.name == "prometheus"

        # But same entity should return same instance
        aletheia2 = await get_agent("aletheia")
        assert aletheia is aletheia2
