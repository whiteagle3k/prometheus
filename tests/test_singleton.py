"""
Test Singleton Service

Verifies that the singleton service properly returns the same instance
across multiple concurrent requests.
"""

import asyncio
import pytest

from core.service.singleton import get_agent


class TestSingletonService:
    """Test that singleton service properly manages a single instance."""
    
    @pytest.mark.asyncio
    async def test_singleton_instance_identity(self):
        """Test that two tasks calling get_agent() get the same instance."""
        
        # Create two concurrent tasks that get the agent
        async def get_agent_task():
            return await get_agent()
        
        # Run tasks concurrently
        agent1, agent2 = await asyncio.gather(
            get_agent_task(),
            get_agent_task()
        )
        
        # Assert that both tasks got the same instance
        assert id(agent1) == id(agent2), (
            f"Singleton failed: got different instances {id(agent1)} vs {id(agent2)}"
        )
        print(f"✅ Singleton test passed: both tasks got instance {id(agent1)}")
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests(self):
        """Test that many concurrent requests all get the same instance."""
        
        # Create multiple concurrent tasks
        tasks = [get_agent() for _ in range(10)]
        
        # Run all tasks concurrently
        agents = await asyncio.gather(*tasks)
        
        # All agents should be the same instance
        first_id = id(agents[0])
        for i, agent in enumerate(agents):
            assert id(agent) == first_id, (
                f"Agent {i} has different id: {id(agent)} vs {first_id}"
            )
        
        print(f"✅ Multiple concurrent requests test passed: all got instance {first_id}")
    
    @pytest.mark.asyncio
    async def test_sequential_requests(self):
        """Test that sequential requests also get the same instance."""
        
        # Get agent three times sequentially
        agent1 = await get_agent()
        agent2 = await get_agent()
        agent3 = await get_agent()
        
        # All should be the same instance
        assert id(agent1) == id(agent2) == id(agent3), (
            f"Sequential requests got different instances: "
            f"{id(agent1)}, {id(agent2)}, {id(agent3)}"
        )
        
        print(f"✅ Sequential requests test passed: all got instance {id(agent1)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 