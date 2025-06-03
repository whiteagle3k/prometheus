"""Abstract base class for external LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class ProviderType(Enum):
    """Supported external LLM provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    # Future providers can be added here
    # GOOGLE = "google"
    # COHERE = "cohere"


@dataclass
class ProviderCapabilities:
    """Capabilities and constraints of a provider."""
    max_context_size: int
    supports_streaming: bool = True
    supports_system_prompt: bool = True
    supports_function_calling: bool = False
    cost_per_1k_input_tokens: float = 0.0
    cost_per_1k_output_tokens: float = 0.0
    rate_limit_rpm: Optional[int] = None  # Requests per minute
    rate_limit_tpm: Optional[int] = None  # Tokens per minute


@dataclass
class GenerationRequest:
    """Request for text generation."""
    prompt: str
    max_tokens: int = 1000
    temperature: float = 0.7
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    stream: bool = False
    extra_params: Optional[Dict[str, Any]] = None


@dataclass
class GenerationResponse:
    """Response from text generation."""
    text: str
    model_used: str
    tokens_used: int
    cost_estimate: float
    provider_metadata: Optional[Dict[str, Any]] = None


class ExternalLLMProvider(ABC):
    """Abstract base class for external LLM providers.
    
    This defines the interface that all external LLM providers must implement.
    Following the Strategy pattern for different LLM provider implementations.
    """

    def __init__(self, provider_config: Dict[str, Any]) -> None:
        """Initialize provider with configuration from identity.json."""
        self.config = provider_config
        self.provider_type = self._get_provider_type()
        self.capabilities = self._get_capabilities()
        self._client = None

    @abstractmethod
    def _get_provider_type(self) -> ProviderType:
        """Get the provider type enum."""
        pass

    @abstractmethod
    def _get_capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities from configuration."""
        pass

    @abstractmethod
    async def _setup_client(self) -> None:
        """Setup the provider-specific client."""
        pass

    @abstractmethod
    async def _generate_text(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using provider-specific API."""
        pass

    @abstractmethod
    async def _generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Generate text with streaming using provider-specific API."""
        pass

    @abstractmethod
    async def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text using provider-specific method."""
        pass

    @abstractmethod
    async def _health_check(self) -> bool:
        """Check if provider is healthy and responsive."""
        pass

    # Public interface methods (these don't need to be overridden)

    async def initialize(self) -> None:
        """Initialize the provider."""
        if not self.config.get("enabled", False):
            raise RuntimeError(f"Provider {self.provider_type.value} is disabled in configuration")
        
        await self._setup_client()

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text using this provider."""
        request = GenerationRequest(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
            model=kwargs.get("model", self.config.get("model")),
            extra_params=kwargs,
        )

        response = await self._generate_text(request)
        return response.text

    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Generate text with streaming."""
        if not self.capabilities.supports_streaming:
            raise NotImplementedError(f"Provider {self.provider_type.value} doesn't support streaming")

        request = GenerationRequest(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
            model=kwargs.get("model", self.config.get("model")),
            stream=True,
            extra_params=kwargs,
        )

        async for chunk in self._generate_stream(request):
            yield chunk

    async def count_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return await self._estimate_tokens(text)

    async def is_available(self) -> bool:
        """Check if provider is available and healthy."""
        if not self.config.get("enabled", False):
            return False
        
        if self._client is None:
            try:
                await self.initialize()
            except Exception:
                return False
        
        return await self._health_check()

    def get_model_info(self) -> Dict[str, Any]:
        """Get comprehensive model information."""
        return {
            "provider": self.provider_type.value,
            "model": self.config.get("model", "unknown"),
            "enabled": self.config.get("enabled", False),
            "available": self._client is not None,
            "capabilities": {
                "max_context_size": self.capabilities.max_context_size,
                "supports_streaming": self.capabilities.supports_streaming,
                "supports_system_prompt": self.capabilities.supports_system_prompt,
                "supports_function_calling": self.capabilities.supports_function_calling,
            },
            "costs": {
                "per_1k_input": self.capabilities.cost_per_1k_input_tokens,
                "per_1k_output": self.capabilities.cost_per_1k_output_tokens,
            },
            "limits": {
                "requests_per_minute": self.capabilities.rate_limit_rpm,
                "tokens_per_minute": self.capabilities.rate_limit_tpm,
            },
            "use_for": self.config.get("use_for", []),
            "configuration": self.config,
        }

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for token usage."""
        input_cost = (input_tokens / 1000) * self.capabilities.cost_per_1k_input_tokens
        output_cost = (output_tokens / 1000) * self.capabilities.cost_per_1k_output_tokens
        return input_cost + output_cost

    def get_context_size(self) -> int:
        """Get maximum context size."""
        return self.capabilities.max_context_size

    def __str__(self) -> str:
        """String representation."""
        return f"{self.provider_type.value}:{self.config.get('model', 'unknown')}"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"<{self.__class__.__name__}(type={self.provider_type.value}, model={self.config.get('model')}, enabled={self.config.get('enabled')})>" 