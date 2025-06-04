"""
Singleton Aletheia Service

Manages a single AletheiaEntity instance shared across all frontends.
Provides thread-safe lazy loading with asyncio.Lock protection.
"""

import asyncio
from typing import Optional

from entities.aletheia import AletheiaEntity


class SingletonAletheia:
    """Singleton wrapper for AletheiaEntity with concurrency protection."""
    
    def __init__(self):
        self._instance: Optional[AletheiaEntity] = None
        self._lock = asyncio.Lock()
        self._running = False
    
    async def get_agent(self) -> AletheiaEntity:
        """
        Get the singleton AletheiaEntity instance.
        Creates instance on first call with thread-safe lazy loading.
        
        Returns:
            The singleton AletheiaEntity instance
        """
        if self._instance is None:
            async with self._lock:
                # Double-check pattern to prevent race conditions
                if self._instance is None:
                    print("🚀 Initializing Aletheia service...")
                    self._instance = AletheiaEntity()
                    await self._instance.initialize()
                    self._running = True
                    print("✅ Aletheia service ready")
        
        return self._instance
    
    def is_running(self) -> bool:
        """Check if the service instance is already running."""
        return self._running
    
    async def shutdown(self):
        """Gracefully shutdown the service."""
        if self._instance:
            print("🛑 Shutting down Aletheia service...")
            # Add any cleanup logic if needed
            self._instance = None
            self._running = False
            print("✅ Aletheia service shutdown complete")


# Module-level singleton instance
_singleton = SingletonAletheia()


async def get_agent() -> AletheiaEntity:
    """
    Get the singleton Aletheia agent instance.
    
    Returns:
        The singleton AletheiaEntity instance
    """
    return await _singleton.get_agent()


def is_service_running() -> bool:
    """
    Check if the Aletheia service is already running.
    
    Returns:
        True if service is running, False otherwise
    """
    return _singleton.is_running()


async def shutdown_service():
    """Gracefully shutdown the Aletheia service."""
    await _singleton.shutdown() 