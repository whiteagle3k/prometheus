"""Manager for external LLM providers using proper OOP patterns."""

from typing import Any

# TODO: Remove identity dependency - configuration should be passed from entity
# from ...identity.loader import get_external_llm_config
from .base import ExternalLLMProvider, ProviderType
from .factory import ProviderFactory


class ExternalLLMManager:
    """Manager for multiple external LLM providers.

    Uses dependency injection and works with the abstract ExternalLLMProvider interface.
    Follows the Strategy pattern - providers are interchangeable strategies.
    """

    def __init__(self, providers_config: dict[str, Any] | None = None) -> None:
        """Initialize the manager.

        Args:
            providers_config: Configuration dictionary for providers
        """
        self._providers: dict[ProviderType, ExternalLLMProvider] = {}
        self._initialized = False
        self._config = providers_config or {}
        self._setup_providers()

    def _setup_providers(self) -> None:
        """Setup available providers based on configuration."""
        providers_config = self._config.get("providers", {})

        for provider_name, provider_config in providers_config.items():
            if not provider_config.get("enabled", False):
                continue

            try:
                # Use factory to create provider instance
                provider = ProviderFactory.create_provider_by_name(provider_name, provider_config)
                provider_type = provider.provider_type
                self._providers[provider_type] = provider
            except Exception as e:
                # Log but don't fail - just skip this provider
                print(f"Warning: Failed to setup {provider_name} provider: {e}")

    async def initialize_all(self) -> None:
        """Initialize all providers."""
        if self._initialized:
            return

        initialization_errors = []

        for provider_type, provider in self._providers.items():
            try:
                await provider.initialize()
            except Exception as e:
                initialization_errors.append(f"{provider_type.value}: {e}")

        if initialization_errors:
            print(f"Warning: Some providers failed to initialize: {initialization_errors}")

        self._initialized = True

    async def get_best_available(self, prefer_provider: str | None = None) -> ExternalLLMProvider | None:
        """Get the best available external LLM based on configuration preferences.

        Args:
            prefer_provider: Optional provider name to prefer ("openai", "anthropic")

        Returns:
            Best available provider instance or None if none available
        """
        await self.initialize_all()

        # 1. Try the specifically preferred provider first
        if prefer_provider:
            preferred_instance = await self._get_provider_by_name(prefer_provider)
            if preferred_instance and await preferred_instance.is_available():
                print(f"✅ Using preferred provider: {prefer_provider}")
                return preferred_instance
            else:
                print(f"⚠️ Preferred provider '{prefer_provider}' not available, checking primary.")

        # 2. Fallback to the primary provider from config
        primary_provider_name = self._config.get("primary_provider")
        if primary_provider_name:
            primary_instance = await self._get_provider_by_name(primary_provider_name)
            if primary_instance and await primary_instance.is_available():
                # Avoid using the same provider if it was the failed preferred one
                if not (prefer_provider and prefer_provider == primary_provider_name):
                    print(f"✅ Using primary provider: {primary_provider_name}")
                    return primary_instance

        # 3. As a last resort, try any other available provider
        for provider in self._providers.values():
            if await provider.is_available():
                # Avoid providers that have already been checked
                if (prefer_provider and provider.provider_type.value == prefer_provider) or \
                   (primary_provider_name and provider.provider_type.value == primary_provider_name):
                    continue
                
                print(f"✅ Using available fallback: {provider.provider_type.value}")
                return provider

        print("❌ No healthy external LLM provider found.")
        return None

    async def get_provider(self, provider_type: ProviderType) -> ExternalLLMProvider | None:
        """Get specific provider by type if available.

        Args:
            provider_type: The provider type to get

        Returns:
            Provider instance or None if not available
        """
        await self.initialize_all()

        if provider_type not in self._providers:
            return None

        provider = self._providers[provider_type]
        if await provider.is_available():
            return provider

        return None

    async def get_provider_by_name(self, provider_name: str) -> ExternalLLMProvider | None:
        """Get specific provider by name if available.

        Args:
            provider_name: The provider name ("openai", "anthropic")

        Returns:
            Provider instance or None if not available
        """
        return await self._get_provider_by_name(provider_name)

    async def _get_provider_by_name(self, provider_name: str) -> ExternalLLMProvider | None:
        """Internal method to get provider by name."""
        try:
            provider_type = ProviderType(provider_name.lower())
            return await self.get_provider(provider_type)
        except ValueError:
            return None

    def list_available_providers(self) -> list[ProviderType]:
        """List all configured provider types."""
        return list(self._providers.keys())

    def list_available_provider_names(self) -> list[str]:
        """List all configured provider names."""
        return [pt.value for pt in self._providers]

    async def list_healthy_providers(self) -> list[ProviderType]:
        """List all providers that are currently healthy and available."""
        await self.initialize_all()

        healthy_providers = []
        for provider_type, provider in self._providers.items():
            if await provider.is_available():
                healthy_providers.append(provider_type)

        return healthy_providers

    async def list_healthy_provider_names(self) -> list[str]:
        """List all provider names that are currently healthy and available."""
        healthy_types = await self.list_healthy_providers()
        return [pt.value for pt in healthy_types]

    def get_provider_preferences(self) -> dict[str, Any]:
        """Get provider preferences from configuration."""
        return {
            "primary_provider": self._config.get("primary_provider", "openai"),
            "fallback_provider": self._config.get("fallback_provider", "anthropic"),
            "routing_preferences": self._config.get("routing_preferences", {}),
            "configured_providers": self.list_available_provider_names(),
        }

    async def get_all_provider_info(self) -> dict[str, dict[str, Any]]:
        """Get comprehensive information about all configured providers."""
        await self.initialize_all()

        provider_info = {}
        for provider_type, provider in self._providers.items():
            try:
                info = provider.get_model_info()
                info["is_healthy"] = await provider.is_available()
                provider_info[provider_type.value] = info
            except Exception as e:
                provider_info[provider_type.value] = {"error": str(e)}

        return provider_info

    async def health_check_all(self) -> dict[str, bool]:
        """Perform health check on all providers."""
        await self.initialize_all()

        health_status = {}
        for provider_type, provider in self._providers.items():
            try:
                health_status[provider_type.value] = await provider.is_available()
            except Exception:
                health_status[provider_type.value] = False

        return health_status

    def add_provider(self, provider: ExternalLLMProvider) -> None:
        """Add a provider instance to the manager.

        Useful for dependency injection or testing.

        Args:
            provider: Configured provider instance
        """
        self._providers[provider.provider_type] = provider

    def remove_provider(self, provider_type: ProviderType) -> None:
        """Remove a provider from the manager.

        Args:
            provider_type: The provider type to remove
        """
        if provider_type in self._providers:
            del self._providers[provider_type]

    def clear_providers(self) -> None:
        """Clear all providers (useful for testing)."""
        self._providers.clear()
        self._initialized = False

    async def estimate_costs_comparison(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> dict[str, float]:
        """Compare costs across all available providers.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Dictionary mapping provider names to estimated costs
        """
        costs = {}
        for provider_type, provider in self._providers.items():
            try:
                cost = provider.estimate_cost(input_tokens, output_tokens)
                costs[provider_type.value] = cost
            except Exception:
                costs[provider_type.value] = float("inf")  # Mark as unavailable

        return costs
