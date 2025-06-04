"""Anthropic Claude provider implementation."""

import warnings
from collections.abc import AsyncGenerator

try:
    import anthropic
except ImportError:
    print("Warning: anthropic not installed. Anthropic provider will not work.")
    anthropic = None

from core.config import config

from .base import (
    ExternalLLMProvider,
    GenerationRequest,
    GenerationResponse,
    ProviderCapabilities,
    ProviderType,
)


class AnthropicProvider(ExternalLLMProvider):
    """Anthropic Claude provider implementation."""

    def _get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.ANTHROPIC

    def _get_capabilities(self) -> ProviderCapabilities:
        """Get Anthropic provider capabilities from configuration."""
        return ProviderCapabilities(
            max_context_size=self.config.get("context_size", 200_000),
            supports_streaming=True,
            supports_system_prompt=True,
            supports_function_calling=False,  # Claude doesn't support function calling (as of 2024)
            cost_per_1k_input_tokens=self.config.get("cost_per_1k_input", 0.003),
            cost_per_1k_output_tokens=self.config.get("cost_per_1k_output", 0.015),
            rate_limit_rpm=self.config.get("rate_limit_rpm"),
            rate_limit_tpm=self.config.get("rate_limit_tpm"),
        )

    async def _setup_client(self) -> None:
        """Setup Anthropic client."""
        if not anthropic:
            msg = "anthropic package not installed"
            raise RuntimeError(msg)

        if not config.anthropic_api_key:
            msg = "ANTHROPIC_API_KEY not configured"
            raise RuntimeError(msg)

        try:
            # Suppress warnings for compatibility issues
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)
        except Exception as e:
            msg = f"Failed to setup Anthropic client: {e}"
            raise RuntimeError(msg)

    async def _generate_text(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using Anthropic API."""
        if not self._client:
            await self._setup_client()

        model = request.model or self.config.get("model", "claude-3-5-sonnet-20241022")

        messages = [{"role": "user", "content": request.prompt}]

        request_kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

        # Anthropic uses separate system parameter
        if request.system_prompt:
            request_kwargs["system"] = request.system_prompt

        # Add any extra parameters from the request
        if request.extra_params:
            request_kwargs.update(request.extra_params)

        try:
            response = await self._client.messages.create(**request_kwargs)

            content = response.content[0].text if response.content else ""

            # Anthropic doesn't return token usage in all responses, estimate it
            input_tokens = await self._estimate_tokens(request.prompt + (request.system_prompt or ""))
            output_tokens = await self._estimate_tokens(content)
            total_tokens = input_tokens + output_tokens

            # Calculate cost estimate
            cost_estimate = self.estimate_cost(input_tokens, output_tokens)

            return GenerationResponse(
                text=content,
                model_used=model,
                tokens_used=total_tokens,
                cost_estimate=cost_estimate,
                provider_metadata={
                    "response_id": response.id,
                    "stop_reason": response.stop_reason,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "usage": getattr(response, "usage", None),  # Some models return usage
                },
            )
        except Exception as e:
            msg = f"Anthropic API error: {e}"
            raise RuntimeError(msg)

    async def _generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Generate text with streaming using Anthropic API."""
        if not self._client:
            await self._setup_client()

        model = request.model or self.config.get("model", "claude-3-5-sonnet-20241022")

        messages = [{"role": "user", "content": request.prompt}]

        request_kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }

        # Anthropic uses separate system parameter
        if request.system_prompt:
            request_kwargs["system"] = request.system_prompt

        # Add any extra parameters from the request
        if request.extra_params:
            request_kwargs.update(request.extra_params)

        try:
            async with self._client.messages.stream(**request_kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            msg = f"Anthropic streaming error: {e}"
            raise RuntimeError(msg)

    async def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for Anthropic models."""
        # Claude: roughly 3.5 characters per token
        return int(len(text) / 3.5)

    async def _health_check(self) -> bool:
        """Check if Anthropic API is healthy."""
        if not self._client:
            return False

        try:
            # Make a minimal API call to check health
            response = await self._client.messages.create(
                model=self.config.get("model", "claude-3-5-sonnet-20241022"),
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return response is not None
        except Exception:
            return False

    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        return self.config.get("model", "claude-3-5-sonnet-20241022")

    def supports_function_calling(self) -> bool:
        """Check if this provider supports function calling."""
        return False

    def get_rate_limits(self) -> dict[str, int | None]:
        """Get rate limits for this provider."""
        return {
            "requests_per_minute": self.capabilities.rate_limit_rpm,
            "tokens_per_minute": self.capabilities.rate_limit_tpm,
        }

    def get_context_analysis_capabilities(self) -> dict[str, bool]:
        """Get Claude-specific context analysis capabilities."""
        return {
            "supports_large_context": True,
            "context_size": self.capabilities.max_context_size,
            "good_for_analysis": True,
            "good_for_reasoning": True,
            "good_for_creative_tasks": True,
        }
