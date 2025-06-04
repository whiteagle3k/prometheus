"""OpenAI provider implementation."""

import warnings
from collections.abc import AsyncGenerator
import asyncio
import time

try:
    import openai
except ImportError:
    print("Warning: openai not installed. OpenAI provider will not work.")
    openai = None

from core.config import config

from .base import (
    ExternalLLMProvider,
    GenerationRequest,
    GenerationResponse,
    ProviderCapabilities,
    ProviderType,
)


class OpenAIProvider(ExternalLLMProvider):
    """OpenAI GPT provider implementation."""

    def _get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.OPENAI

    def _get_capabilities(self) -> ProviderCapabilities:
        """Get OpenAI provider capabilities from configuration."""
        return ProviderCapabilities(
            max_context_size=self.config.get("context_size", 128_000),
            supports_streaming=True,
            supports_system_prompt=True,
            supports_function_calling=True,  # OpenAI supports function calling
            cost_per_1k_input_tokens=self.config.get("cost_per_1k_input", 0.0015),
            cost_per_1k_output_tokens=self.config.get("cost_per_1k_output", 0.006),
            rate_limit_rpm=self.config.get("rate_limit_rpm"),
            rate_limit_tpm=self.config.get("rate_limit_tpm"),
        )

    async def _setup_client(self) -> None:
        """Setup OpenAI client."""
        if not openai:
            msg = "openai package not installed"
            raise RuntimeError(msg)

        if not config.openai_api_key:
            msg = "OPENAI_API_KEY not configured"
            raise RuntimeError(msg)

        try:
            # Suppress warnings for compatibility issues
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._client = openai.AsyncOpenAI(api_key=config.openai_api_key)
        except Exception as e:
            msg = f"Failed to setup OpenAI client: {e}"
            raise RuntimeError(msg)

    async def _generate_text(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using OpenAI API."""
        
        if not self._client:
            await self._setup_client()

        model = request.model or self.config.get("model", "gpt-4o-mini")

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        request_kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

        # Add any extra parameters from the request
        if request.extra_params:
            request_kwargs.update(request.extra_params)

        try:
            response = await self._client.chat.completions.create(**request_kwargs)

            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0

            # Calculate cost estimate
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            cost_estimate = self.estimate_cost(input_tokens, output_tokens)

            return GenerationResponse(
                text=content,
                model_used=model,
                tokens_used=tokens_used,
                cost_estimate=cost_estimate,
                provider_metadata={
                    "response_id": response.id,
                    "finish_reason": response.choices[0].finish_reason,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            )
        except Exception as e:
            msg = f"OpenAI API error: {e}"
            raise RuntimeError(msg)

    async def _generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Generate text with streaming using OpenAI API."""
        if not self._client:
            await self._setup_client()

        model = request.model or self.config.get("model", "gpt-4o-mini")

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        request_kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }

        # Add any extra parameters from the request
        if request.extra_params:
            request_kwargs.update(request.extra_params)

        try:
            stream = await self._client.chat.completions.create(**request_kwargs)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            msg = f"OpenAI streaming error: {e}"
            raise RuntimeError(msg)

    async def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for OpenAI models."""
        # OpenAI: roughly 4 characters per token
        # This is a simple estimation - for production use, consider using tiktoken
        return len(text) // 4

    async def _health_check(self) -> bool:
        """Check if OpenAI API is healthy."""
        if not self._client:
            return False

        try:
            # Make a minimal API call to check health
            response = await self._client.chat.completions.create(
                model=self.config.get("model", "gpt-4o-mini"),
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return response is not None
        except Exception:
            return False

    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        return self.config.get("model", "gpt-4o-mini")

    def supports_function_calling(self) -> bool:
        """Check if this provider supports function calling."""
        return True

    def get_rate_limits(self) -> dict[str, int | None]:
        """Get rate limits for this provider."""
        return {
            "requests_per_minute": self.capabilities.rate_limit_rpm,
            "tokens_per_minute": self.capabilities.rate_limit_tpm,
        }
