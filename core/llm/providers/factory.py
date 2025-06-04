"""Factory for creating external LLM provider instances."""

from typing import Any

from .anthropic_provider import AnthropicProvider

# TODO: Remove identity dependency - configuration should be passed from entity
# from ...identity.loader import get_provider_config
from .base import ExternalLLMProvider, ProviderType
from .openai_provider import OpenAIProvider


class ProviderFactory:
    """Factory for creating external LLM provider instances.

    Follows the Factory pattern to encapsulate provider creation logic.
    Makes it easy to add new providers without modifying existing code.
    """

    # Registry of available provider classes
    _PROVIDER_REGISTRY: dict[ProviderType, type[ExternalLLMProvider]] = {
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.ANTHROPIC: AnthropicProvider,
        # Future providers can be registered here:
        # ProviderType.GOOGLE: GoogleProvider,
        # ProviderType.COHERE: CohereProvider,
    }

    @classmethod
    def create_provider(
        self,
        provider_type: ProviderType,
        provider_config: dict[str, Any]
    ) -> ExternalLLMProvider:
        """Create a provider instance by type.

        Args:
            provider_type: The type of provider to create
            provider_config: Provider configuration (required)

        Returns:
            Configured provider instance

        Raises:
            ValueError: If provider type is not supported
            RuntimeError: If provider configuration is invalid
        """
        if provider_type not in self._PROVIDER_REGISTRY:
            available_types = list(self._PROVIDER_REGISTRY.keys())
            msg = f"Unsupported provider type: {provider_type}. Available: {available_types}"
            raise ValueError(msg)

        if not provider_config:
            msg = f"No configuration provided for provider: {provider_type.value}"
            raise RuntimeError(msg)

        # Get the provider class and create instance
        provider_class = self._PROVIDER_REGISTRY[provider_type]
        try:
            return provider_class(provider_config)
        except Exception as e:
            msg = f"Failed to create {provider_type.value} provider: {e}"
            raise RuntimeError(msg)

    @classmethod
    def create_provider_by_name(
        self,
        provider_name: str,
        provider_config: dict[str, Any]
    ) -> ExternalLLMProvider:
        """Create a provider instance by name string.

        Args:
            provider_name: Name of the provider ("openai", "anthropic", etc.)
            provider_config: Provider configuration (required)

        Returns:
            Configured provider instance

        Raises:
            ValueError: If provider name is not recognized
        """
        # Convert string name to ProviderType enum
        try:
            provider_type = ProviderType(provider_name.lower())
        except ValueError:
            available_names = [pt.value for pt in ProviderType]
            msg = f"Unknown provider name: {provider_name}. Available: {available_names}"
            raise ValueError(msg)

        return self.create_provider(provider_type, provider_config)

    @classmethod
    def get_available_providers(self) -> list[ProviderType]:
        """Get list of all available provider types."""
        return list(self._PROVIDER_REGISTRY.keys())

    @classmethod
    def get_available_provider_names(self) -> list[str]:
        """Get list of all available provider names."""
        return [pt.value for pt in self._PROVIDER_REGISTRY]

    @classmethod
    def register_provider(
        self,
        provider_type: ProviderType,
        provider_class: type[ExternalLLMProvider]
    ) -> None:
        """Register a new provider class.

        This allows for runtime registration of new providers,
        useful for plugins or dynamic provider discovery.

        Args:
            provider_type: The provider type enum
            provider_class: The provider implementation class
        """
        if not issubclass(provider_class, ExternalLLMProvider):
            msg = "Provider class must inherit from ExternalLLMProvider"
            raise TypeError(msg)

        self._PROVIDER_REGISTRY[provider_type] = provider_class

    @classmethod
    def is_provider_supported(self, provider_type: ProviderType) -> bool:
        """Check if a provider type is supported."""
        return provider_type in self._PROVIDER_REGISTRY

    @classmethod
    def is_provider_name_supported(self, provider_name: str) -> bool:
        """Check if a provider name is supported."""
        try:
            provider_type = ProviderType(provider_name.lower())
            return self.is_provider_supported(provider_type)
        except ValueError:
            return False

    @classmethod
    def get_provider_info_summary(self) -> dict[str, dict[str, Any]]:
        """Get basic information about all available providers.

        Returns provider types and classes without instantiation.
        """
        summary = {}

        for provider_type, provider_class in self._PROVIDER_REGISTRY.items():
            summary[provider_type.value] = {
                "provider_class": provider_class.__name__,
                "module": provider_class.__module__,
            }

        return summary
