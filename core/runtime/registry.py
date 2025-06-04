"""
Universal Agent Registry

Centralized registry for managing multiple agent instances.
Provides singleton behavior per entity while remaining entity-agnostic.
"""

import asyncio
import importlib
import logging
import signal
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Universal registry for managing multiple agent instances.
    
    Maintains one instance per entity name while remaining completely
    entity-agnostic. Supports dynamic loading and lifecycle management.
    """
    
    def __init__(self):
        """Initialize the agent registry."""
        self._instances: Dict[str, Any] = {}
        self._agent_lock = asyncio.Lock()
        self._shutdown_handlers: Dict[str, list] = {}
        self._running = False
        
    async def get_agent(self, entity_name: str = "aletheia") -> Any:
        """
        Get or create agent instance for the specified entity.
        
        Args:
            entity_name: Name of the entity (e.g., "aletheia", "prometheus", "teslabot")
            
        Returns:
            Agent instance for the specified entity
            
        Raises:
            ImportError: If entity module/class not found
            Exception: If agent initialization fails
        """
        # Fast path - return existing instance
        if entity_name in self._instances:
            return self._instances[entity_name]
        
        # Slow path with lock protection
        async with self._agent_lock:
            # Double-check pattern
            if entity_name in self._instances:
                return self._instances[entity_name]
            
            logger.info(f"🚀 Initializing agent: {entity_name}")
            
            try:
                # Dynamically import entity module
                module_path = f"entities.{entity_name}"
                entity_module = importlib.import_module(module_path)
                
                # Get entity class (e.g., AletheiaEntity, PrometheusEntity)
                class_name = f"{entity_name.capitalize()}Entity"
                entity_class = getattr(entity_module, class_name)
                
                # Create instance
                instance = entity_class()
                
                # Store in registry
                self._instances[entity_name] = instance
                self._shutdown_handlers[entity_name] = []
                
                logger.info(f"✅ Agent initialized: {entity_name} ({class_name})")
                return instance
                
            except ImportError as e:
                logger.error(f"❌ Failed to import entity '{entity_name}': {e}")
                raise ImportError(f"Entity '{entity_name}' not found. Check entities/{entity_name}/ module.")
            
            except AttributeError as e:
                logger.error(f"❌ Entity class '{class_name}' not found in module: {e}")
                raise AttributeError(f"Class '{class_name}' not found in entities.{entity_name}")
            
            except Exception as e:
                logger.error(f"❌ Failed to initialize entity '{entity_name}': {e}")
                raise
    
    def is_agent_running(self, entity_name: str) -> bool:
        """Check if specific agent is running."""
        return entity_name in self._instances
    
    def get_running_agents(self) -> list[str]:
        """Get list of currently running agent names."""
        return list(self._instances.keys())
    
    def get_agent_count(self) -> int:
        """Get number of running agents."""
        return len(self._instances)
    
    async def add_shutdown_handler(self, entity_name: str, handler):
        """Add shutdown handler for specific entity."""
        if entity_name not in self._shutdown_handlers:
            self._shutdown_handlers[entity_name] = []
        self._shutdown_handlers[entity_name].append(handler)
    
    async def shutdown_agent(self, entity_name: str) -> bool:
        """Shutdown specific agent instance."""
        if entity_name not in self._instances:
            logger.warning(f"Agent '{entity_name}' not running")
            return False
        
        logger.info(f"🛑 Shutting down agent: {entity_name}")
        
        try:
            instance = self._instances[entity_name]
            
            # Call entity-specific shutdown handlers
            if entity_name in self._shutdown_handlers:
                for handler in self._shutdown_handlers[entity_name]:
                    try:
                        await handler()
                    except Exception as e:
                        logger.error(f"Error in shutdown handler for {entity_name}: {e}")
            
            # Create memory snapshot if available
            if hasattr(instance, 'memory_controller') and instance.memory_controller:
                try:
                    logger.info(f"📸 Creating snapshot for {entity_name}")
                    await instance.memory_controller.create_snapshot(auto=False)
                    await instance.memory_controller.stop_auto_snapshots()
                except Exception as e:
                    logger.error(f"Error creating snapshot for {entity_name}: {e}")
            
            # Save state if available
            if hasattr(instance, 'save_state'):
                try:
                    logger.info(f"💾 Saving state for {entity_name}")
                    await instance.save_state()
                except Exception as e:
                    logger.error(f"Error saving state for {entity_name}: {e}")
            
            # Close resources
            if hasattr(instance, 'close'):
                await instance.close()
            
            # Remove from registry
            del self._instances[entity_name]
            if entity_name in self._shutdown_handlers:
                del self._shutdown_handlers[entity_name]
            
            logger.info(f"✅ Agent shutdown complete: {entity_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error shutting down agent '{entity_name}': {e}")
            return False
    
    async def shutdown_all(self) -> bool:
        """Shutdown all running agents."""
        if not self._instances:
            logger.info("No agents running")
            return True
        
        logger.info(f"🛑 Shutting down all agents: {list(self._instances.keys())}")
        
        shutdown_results = []
        for entity_name in list(self._instances.keys()):
            result = await self.shutdown_agent(entity_name)
            shutdown_results.append(result)
        
        success = all(shutdown_results)
        if success:
            logger.info("✅ All agents shutdown successfully")
        else:
            logger.warning("⚠️ Some agents failed to shutdown cleanly")
        
        return success
    
    async def reload_agent(self, entity_name: str) -> bool:
        """Reload specific agent (shutdown + restart)."""
        logger.info(f"🔄 Reloading agent: {entity_name}")
        
        # Shutdown existing instance
        await self.shutdown_agent(entity_name)
        
        # Clear module cache to force reload
        module_path = f"entities.{entity_name}"
        if module_path in importlib.sys.modules:
            importlib.reload(importlib.sys.modules[module_path])
        
        # Get fresh instance
        try:
            await self.get_agent(entity_name)
            logger.info(f"✅ Agent reloaded: {entity_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to reload agent '{entity_name}': {e}")
            return False
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "running_agents": self.get_running_agents(),
            "agent_count": self.get_agent_count(),
            "registry_status": "active" if self._instances else "empty"
        }


# Module-level registry instance
_registry = AgentRegistry()


async def get_agent(entity_name: str = "aletheia") -> Any:
    """
    Get agent instance from global registry.
    
    Args:
        entity_name: Name of the entity to get
        
    Returns:
        Agent instance
    """
    return await _registry.get_agent(entity_name)


def is_agent_running(entity_name: str) -> bool:
    """Check if specific agent is running."""
    return _registry.is_agent_running(entity_name)


def get_running_agents() -> list[str]:
    """Get list of running agent names."""
    return _registry.get_running_agents()


def get_agent_count() -> int:
    """Get number of running agents."""
    return _registry.get_agent_count()


async def shutdown_agent(entity_name: str) -> bool:
    """Shutdown specific agent."""
    return await _registry.shutdown_agent(entity_name)


async def shutdown_all_agents() -> bool:
    """Shutdown all agents."""
    return await _registry.shutdown_all()


async def add_shutdown_handler(entity_name: str, handler):
    """Add shutdown handler for specific entity."""
    await _registry.add_shutdown_handler(entity_name, handler)


def get_registry_stats() -> Dict[str, Any]:
    """Get registry statistics."""
    return _registry.get_registry_stats()


# Signal handling for graceful shutdown
def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down all agents...")
        asyncio.create_task(shutdown_all_agents())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler) 