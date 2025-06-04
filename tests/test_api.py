"""
Test FastAPI Service

Tests the FastAPI endpoints using httpx.AsyncClient.
"""

import pytest
from httpx import AsyncClient

from core.service.api_server import app


class TestAPIService:
    """Test FastAPI endpoints."""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test the root endpoint returns service information."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "service" in data
            assert "version" in data
            assert "status" in data
            assert data["service"] == "Aletheia AI Service"
            assert data["status"] == "running"
            
            print("✅ Root endpoint test passed")
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test the health check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "status" in data
            assert "timestamp" in data
            assert data["status"] == "healthy"
            
            print("✅ Health endpoint test passed")
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_structure(self):
        """Test that chat endpoint accepts requests and returns proper structure."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Send a simple test message
            chat_request = {
                "user_id": "test_user",
                "message": "Hello, this is a test message"
            }
            
            response = await client.post("/v1/chat", json=chat_request)
            
            # Should return 200 or 500 (depending on if Aletheia initializes)
            assert response.status_code in [200, 500]
            
            data = response.json()
            
            if response.status_code == 200:
                # Success case - check response structure
                assert "answer" in data
                assert "route" in data
                assert "latency" in data
                assert isinstance(data["latency"], (int, float))
                print("✅ Chat endpoint success test passed")
            else:
                # Error case - check error structure
                assert "detail" in data
                assert isinstance(data["detail"], dict)
                assert "error" in data["detail"]
                assert "latency" in data["detail"]
                assert "user_id" in data["detail"]
                print("✅ Chat endpoint error handling test passed")
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_validation(self):
        """Test that chat endpoint validates required fields."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test missing user_id
            response = await client.post("/v1/chat", json={"message": "test"})
            assert response.status_code == 422  # Validation error
            
            # Test missing message
            response = await client.post("/v1/chat", json={"user_id": "test"})
            assert response.status_code == 422  # Validation error
            
            # Test empty request
            response = await client.post("/v1/chat", json={})
            assert response.status_code == 422  # Validation error
            
            print("✅ Chat endpoint validation test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 