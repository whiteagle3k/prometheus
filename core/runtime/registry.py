"""
Universal Agent Registry

Centralized registry for managing multiple agent instances.
Provides singleton behavior per entity while remaining entity-agnostic.
Uses proper separation of technical IDs and human names.
"""

import asyncio
import importlib
import logging
import signal
from typing import Any

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Universal registry for managing multiple agent instances.

    Maintains one instance per entity ID while remaining completely
    entity-agnostic. Supports dynamic loading and lifecycle management.
    Uses technical IDs for registration and human names for display.
    """

    def __init__(self):
        """Initialize the agent registry."""
        self._instances: dict[str, Any] = {}
        self._agent_lock = asyncio.Lock()
        self._shutdown_handlers: dict[str, list] = {}
        self._running = False

    async def get_agent(self, entity_id: str = "aletheia") -> Any:
        """
        Get or create agent instance for the specified entity.

        Args:
            entity_id: Technical ID of the entity (e.g., "supervisor", "developer", "qa")

        Returns:
            Agent instance for the specified entity

        Raises:
            ImportError: If entity module/class not found
            Exception: If agent initialization fails
        """
        # Fast path - return existing instance
        if entity_id in self._instances:
            return self._instances[entity_id]

        # Slow path with lock protection
        async with self._agent_lock:
            # Double-check pattern
            if entity_id in self._instances:
                return self._instances[entity_id]

            logger.info(f"🚀 Initializing agent: {entity_id}")

            try:
                # Get entity info from discovery system
                from entities import get_entity_info
                entity_info = get_entity_info(entity_id)
                
                # Extract registration details
                module_path = entity_info["module_path"]
                entity_class = entity_info["class"]
                entity_name = entity_info.get("name", entity_id)
                
                logger.info(f"📋 Entity info: {entity_name} ({entity_class.__name__}) from {module_path}")

                # Create instance directly from class
                instance = entity_class()

                # Store in registry
                self._instances[entity_id] = instance
                self._shutdown_handlers[entity_id] = []

                logger.info(f"✅ Agent initialized: {entity_id} -> {entity_name} ({entity_class.__name__})")
                return instance

            except ValueError as e:
                logger.error(f"❌ Entity '{entity_id}' not found in discovery: {e}")
                raise ImportError(f"Entity '{entity_id}' not found. {e}")

            except Exception as e:
                logger.error(f"❌ Failed to initialize entity '{entity_id}': {e}")
                raise

    def is_agent_running(self, entity_id: str) -> bool:
        """Check if specific agent is running."""
        return entity_id in self._instances

    def get_running_agents(self) -> list[str]:
        """Get list of currently running agent IDs."""
        return list(self._instances.keys())

    def get_agent_count(self) -> int:
        """Get number of running agents."""
        return len(self._instances)

    def get_running_agent_info(self) -> dict[str, dict[str, Any]]:
        """Get detailed info about running agents."""
        from entities import get_entity_info, get_localized_name
        
        result = {}
        for entity_id in self._instances.keys():
            try:
                entity_info = get_entity_info(entity_id)
                result[entity_id] = {
                    "name": get_localized_name(entity_info.get("name", entity_id), "en"),
                    "name_localized": entity_info.get("name", entity_id),  # Full multilingual data
                    "description": entity_info.get("description", ""),
                    "class": entity_info["class"].__name__,
                    "module": entity_info["module_path"],
                    "status": "running"
                }
            except Exception as e:
                result[entity_id] = {
                    "name": entity_id,
                    "name_localized": entity_id,
                    "description": f"Error getting info: {e}",
                    "status": "running"
                }
        return result

    async def add_shutdown_handler(self, entity_id: str, handler):
        """Add shutdown handler for specific entity."""
        if entity_id not in self._shutdown_handlers:
            self._shutdown_handlers[entity_id] = []
        self._shutdown_handlers[entity_id].append(handler)

    async def shutdown_agent(self, entity_id: str) -> bool:
        """Shutdown specific agent instance."""
        if entity_id not in self._instances:
            logger.warning(f"Agent '{entity_id}' not running")
            return False

        logger.info(f"🛑 Shutting down agent: {entity_id}")

        try:
            instance = self._instances[entity_id]

            # Call entity-specific shutdown handlers
            if entity_id in self._shutdown_handlers:
                for handler in self._shutdown_handlers[entity_id]:
                    try:
                        await handler()
                    except Exception as e:
                        logger.error(f"Error in shutdown handler for {entity_id}: {e}")

            # Create memory snapshot if available
            if hasattr(instance, "memory_controller") and instance.memory_controller:
                try:
                    logger.info(f"📸 Creating snapshot for {entity_id}")
                    await instance.memory_controller.create_snapshot(auto=False)
                    await instance.memory_controller.stop_auto_snapshots()
                except Exception as e:
                    logger.error(f"Error creating snapshot for {entity_id}: {e}")

            # Save state if available
            if hasattr(instance, "save_state"):
                try:
                    logger.info(f"💾 Saving state for {entity_id}")
                    await instance.save_state()
                except Exception as e:
                    logger.error(f"Error saving state for {entity_id}: {e}")

            # Close resources
            if hasattr(instance, "close"):
                await instance.close()

            # Remove from registry
            del self._instances[entity_id]
            if entity_id in self._shutdown_handlers:
                del self._shutdown_handlers[entity_id]

            logger.info(f"✅ Agent shutdown complete: {entity_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Error shutting down agent '{entity_id}': {e}")
            return False

    async def shutdown_all(self) -> bool:
        """Shutdown all running agents."""
        if not self._instances:
            logger.info("No agents running")
            return True

        logger.info(f"🛑 Shutting down all agents: {list(self._instances.keys())}")

        shutdown_results = []
        for entity_id in list(self._instances.keys()):
            result = await self.shutdown_agent(entity_id)
            shutdown_results.append(result)

        success = all(shutdown_results)
        if success:
            logger.info("✅ All agents shutdown successfully")
        else:
            logger.warning("⚠️ Some agents failed to shutdown cleanly")

        return success

    async def reload_agent(self, entity_id: str) -> bool:
        """Reload specific agent (shutdown + restart)."""
        logger.info(f"🔄 Reloading agent: {entity_id}")

        # Shutdown existing instance
        await self.shutdown_agent(entity_id)

        # Clear module cache to force reload
        from entities import get_entity_info
        try:
            entity_info = get_entity_info(entity_id)
            module_path = entity_info["module_path"]
            if module_path in importlib.sys.modules:
                importlib.reload(importlib.sys.modules[module_path])
        except Exception as e:
            logger.warning(f"Could not reload module for {entity_id}: {e}")

        # Get fresh instance
        try:
            await self.get_agent(entity_id)
            logger.info(f"✅ Agent reloaded: {entity_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to reload agent '{entity_id}': {e}")
            return False

    def get_registry_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        return {
            "running_agents": self.get_running_agents(),
            "agent_count": self.get_agent_count(),
            "agent_info": self.get_running_agent_info(),
            "registry_status": "active" if self._instances else "empty"
        }


# Module-level registry instance
_registry = AgentRegistry()


async def get_agent(entity_id: str = "aletheia") -> Any:
    """
    Get agent instance from global registry.

    Args:
        entity_id: Technical ID of the entity to get

    Returns:
        Agent instance
    """
    return await _registry.get_agent(entity_id)


def is_agent_running(entity_id: str) -> bool:
    """Check if specific agent is running."""
    return _registry.is_agent_running(entity_id)


def get_running_agents() -> list[str]:
    """Get list of running agent IDs."""
    return _registry.get_running_agents()


def get_agent_count() -> int:
    """Get number of running agents."""
    return _registry.get_agent_count()


async def shutdown_agent(entity_id: str) -> bool:
    """Shutdown specific agent."""
    return await _registry.shutdown_agent(entity_id)


async def shutdown_all_agents() -> bool:
    """Shutdown all agents."""
    return await _registry.shutdown_all()


async def add_shutdown_handler(entity_id: str, handler):
    """Add shutdown handler for specific entity."""
    await _registry.add_shutdown_handler(entity_id, handler)


def get_registry_stats() -> dict[str, Any]:
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
