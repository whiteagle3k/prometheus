"""
Agent Lifecycle Manager

Coordinates startup, shutdown, and state management for all agents
in a multi-entity environment.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Callable
from pathlib import Path

from .registry import get_agent, shutdown_all_agents, get_running_agents

logger = logging.getLogger(__name__)


class LifecycleManager:
    """Manages startup, shutdown, and state coordination for all agents."""
    
    def __init__(self):
        """Initialize lifecycle manager."""
        self.startup_hooks: List[Callable] = []
        self.shutdown_hooks: List[Callable] = []
        self.health_checks: Dict[str, Callable] = {}
        self._shutdown_initiated = False
    
    def add_startup_hook(self, hook: Callable):
        """Add startup hook to run after agent initialization."""
        self.startup_hooks.append(hook)
    
    def add_shutdown_hook(self, hook: Callable):
        """Add shutdown hook to run before agent shutdown."""
        self.shutdown_hooks.append(hook)
    
    def add_health_check(self, name: str, check: Callable):
        """Add health check for monitoring."""
        self.health_checks[name] = check
    
    async def startup(self, entities: List[str] = None) -> bool:
        """
        Coordinate startup for specified entities.
        
        Args:
            entities: List of entity names to start (default: ["aletheia"])
            
        Returns:
            True if all entities started successfully
        """
        if entities is None:
            entities = ["aletheia"]
        
        logger.info(f"🚀 Starting lifecycle for entities: {entities}")
        start_time = time.time()
        
        try:
            # Initialize all requested entities
            initialized_agents = []
            for entity_name in entities:
                try:
                    agent = await get_agent(entity_name)
                    initialized_agents.append(entity_name)
                    logger.info(f"✅ Entity initialized: {entity_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize entity '{entity_name}': {e}")
                    # Continue with other entities
            
            if not initialized_agents:
                logger.error("❌ No entities initialized successfully")
                return False
            
            # Run startup hooks
            for hook in self.startup_hooks:
                try:
                    if asyncio.iscoroutinefunction(hook):
                        await hook()
                    else:
                        hook()
                except Exception as e:
                    logger.error(f"Error in startup hook: {e}")
            
            startup_time = time.time() - start_time
            logger.info(f"✅ Lifecycle startup complete: {initialized_agents} ({startup_time:.2f}s)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Lifecycle startup failed: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """
        Coordinate graceful shutdown for all running entities.
        
        Returns:
            True if shutdown completed successfully
        """
        if self._shutdown_initiated:
            logger.warning("Shutdown already in progress")
            return True
        
        self._shutdown_initiated = True
        logger.info("🛑 Initiating graceful shutdown")
        start_time = time.time()
        
        try:
            # Run shutdown hooks first
            for hook in self.shutdown_hooks:
                try:
                    if asyncio.iscoroutinefunction(hook):
                        await hook()
                    else:
                        hook()
                except Exception as e:
                    logger.error(f"Error in shutdown hook: {e}")
            
            # Shutdown all agents
            success = await shutdown_all_agents()
            
            shutdown_time = time.time() - start_time
            if success:
                logger.info(f"✅ Lifecycle shutdown complete ({shutdown_time:.2f}s)")
            else:
                logger.warning(f"⚠️ Lifecycle shutdown completed with errors ({shutdown_time:.2f}s)")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Lifecycle shutdown failed: {e}")
            return False
        finally:
            self._shutdown_initiated = False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Run health checks for all components.
        
        Returns:
            Health status report
        """
        health_report = {
            "timestamp": time.time(),
            "overall_status": "healthy",
            "running_agents": get_running_agents(),
            "agent_count": len(get_running_agents()),
            "checks": {}
        }
        
        failed_checks = 0
        
        # Run registered health checks
        for check_name, check_func in self.health_checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                health_report["checks"][check_name] = {
                    "status": "healthy" if result else "unhealthy",
                    "result": result
                }
                
                if not result:
                    failed_checks += 1
                    
            except Exception as e:
                health_report["checks"][check_name] = {
                    "status": "error", 
                    "error": str(e)
                }
                failed_checks += 1
        
        # Overall status
        if failed_checks > 0:
            health_report["overall_status"] = "degraded" if failed_checks < len(self.health_checks) else "unhealthy"
        
        return health_report
    
    async def create_system_snapshot(self) -> Dict[str, str]:
        """
        Create snapshots for all running agents.
        
        Returns:
            Dictionary of agent_name -> snapshot_path
        """
        snapshots = {}
        running_agents = get_running_agents()
        
        logger.info(f"📸 Creating system snapshot for {len(running_agents)} agents")
        
        for entity_name in running_agents:
            try:
                agent = await get_agent(entity_name)
                if hasattr(agent, 'memory_controller') and agent.memory_controller:
                    snapshot_path = await agent.memory_controller.create_snapshot(auto=False)
                    snapshots[entity_name] = snapshot_path
                    logger.info(f"✅ Snapshot created for {entity_name}: {snapshot_path}")
                else:
                    logger.warning(f"⚠️ Agent {entity_name} has no memory controller")
                    
            except Exception as e:
                logger.error(f"❌ Failed to create snapshot for {entity_name}: {e}")
                snapshots[entity_name] = f"ERROR: {str(e)}"
        
        return snapshots
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "running_agents": get_running_agents(),
            "agent_count": len(get_running_agents()),
            "startup_hooks": len(self.startup_hooks),
            "shutdown_hooks": len(self.shutdown_hooks),
            "health_checks": len(self.health_checks),
            "shutdown_initiated": self._shutdown_initiated
        }


# Global lifecycle manager instance
_lifecycle_manager = LifecycleManager()


def get_lifecycle_manager() -> LifecycleManager:
    """Get the global lifecycle manager."""
    return _lifecycle_manager


async def startup_system(entities: List[str] = None) -> bool:
    """Startup system with specified entities."""
    return await _lifecycle_manager.startup(entities)


async def shutdown_system() -> bool:
    """Shutdown entire system."""
    return await _lifecycle_manager.shutdown()


async def system_health_check() -> Dict[str, Any]:
    """Run system health check."""
    return await _lifecycle_manager.health_check()


async def create_system_snapshot() -> Dict[str, str]:
    """Create snapshots for all agents."""
    return await _lifecycle_manager.create_system_snapshot()


def get_system_status() -> Dict[str, Any]:
    """Get system status."""
    return _lifecycle_manager.get_system_status() 