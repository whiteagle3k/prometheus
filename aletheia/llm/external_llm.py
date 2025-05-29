"""External LLM implementations for Claude and GPT-4."""

from collections.abc import AsyncGenerator
from enum import Enum
from typing import Any, Optional

try:
    import anthropic
except ImportError:
    print("Warning: anthropic not installed. Claude will not work.")
    anthropic = None

try:
    import openai
except ImportError:
    print("Warning: openai not installed. GPT-4 will not work.")
    openai = None

from ..config import config


class ExternalProvider(Enum):
    """External LLM providers."""
    CLAUDE = "claude"
    GPT4 = "gpt4"


class ExternalLLM:
    """Client for external LLM services (Claude, GPT-4)."""

    def __init__(self, provider: ExternalProvider = ExternalProvider.CLAUDE) -> None:
        """Initialize external LLM client."""
        self.provider = provider
        self._anthropic_client: Optional[anthropic.AsyncAnthropic] = None
        self._openai_client: Optional[openai.AsyncOpenAI] = None

        self._setup_clients()

    def _setup_clients(self) -> None:
        """Setup API clients based on available keys."""
        if config.anthropic_api_key and anthropic:
            try:
                # Suppress warnings for compatibility issues
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    self._anthropic_client = anthropic.AsyncAnthropic(
                        api_key=config.anthropic_api_key
                    )
            except Exception:
                # Silently skip anthropic setup if there are compatibility issues
                pass

        if config.openai_api_key and openai:
            try:
                # Suppress warnings for compatibility issues
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    self._openai_client = openai.AsyncOpenAI(
                        api_key=config.openai_api_key
                    )
            except Exception:
                # Silently skip openai setup if there are compatibility issues
                pass

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text using external LLM."""
        if self.provider == ExternalProvider.CLAUDE:
            return await self._generate_claude(
                prompt, max_tokens, temperature, system_prompt, **kwargs
            )
        elif self.provider == ExternalProvider.GPT4:
            return await self._generate_gpt4(
                prompt, max_tokens, temperature, system_prompt, **kwargs
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def _generate_claude(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str],
        **kwargs: Any,
    ) -> str:
        """Generate using Claude."""
        if not self._anthropic_client:
            raise RuntimeError("Claude client not available. Check ANTHROPIC_API_KEY.")

        messages = [{"role": "user", "content": prompt}]

        request_kwargs = {
            "model": kwargs.get("model", "claude-3-opus-20240229"),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system_prompt:
            request_kwargs["system"] = system_prompt

        try:
            response = await self._anthropic_client.messages.create(**request_kwargs)
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Claude API error: {e}")

    async def _generate_gpt4(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str],
        **kwargs: Any,
    ) -> str:
        """Generate using GPT-4."""
        if not self._openai_client:
            raise RuntimeError("OpenAI client not available. Check OPENAI_API_KEY.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        request_kwargs = {
            "model": kwargs.get("model", "gpt-4.1-mini"),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        try:
            response = await self._openai_client.chat.completions.create(**request_kwargs)
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")

    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Generate text with streaming output."""
        if self.provider == ExternalProvider.CLAUDE:
            async for chunk in self._generate_claude_stream(
                prompt, max_tokens, temperature, system_prompt, **kwargs
            ):
                yield chunk
        elif self.provider == ExternalProvider.GPT4:
            async for chunk in self._generate_gpt4_stream(
                prompt, max_tokens, temperature, system_prompt, **kwargs
            ):
                yield chunk
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def _generate_claude_stream(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream generation using Claude."""
        if not self._anthropic_client:
            raise RuntimeError("Claude client not available. Check ANTHROPIC_API_KEY.")

        messages = [{"role": "user", "content": prompt}]

        request_kwargs = {
            "model": kwargs.get("model", "claude-3-opus-20240229"),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
            "stream": True,
        }

        if system_prompt:
            request_kwargs["system"] = system_prompt

        try:
            async with self._anthropic_client.messages.stream(**request_kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise RuntimeError(f"Claude streaming error: {e}")

    async def _generate_gpt4_stream(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream generation using GPT-4."""
        if not self._openai_client:
            raise RuntimeError("OpenAI client not available. Check OPENAI_API_KEY.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        request_kwargs = {
            "model": kwargs.get("model", "gpt-4"),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
            "stream": True,
        }

        try:
            stream = await self._openai_client.chat.completions.create(**request_kwargs)
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"OpenAI streaming error: {e}")

    async def count_tokens(self, text: str) -> int:
        """Estimate token count (provider-specific)."""
        if self.provider == ExternalProvider.CLAUDE:
            # Claude: roughly 3.5 chars per token
            return len(text) // 3.5
        elif self.provider == ExternalProvider.GPT4:
            # GPT-4: roughly 4 chars per token
            return len(text) // 4
        else:
            return len(text) // 4  # Default estimate

    def get_context_size(self) -> int:
        """Get model context size."""
        if self.provider == ExternalProvider.CLAUDE:
            return 200_000  # Claude 3 Opus
        elif self.provider == ExternalProvider.GPT4:
            return 8_192    # GPT-4 standard
        else:
            return 4_096    # Conservative default

    async def is_available(self) -> bool:
        """Check if the external LLM is available."""
        if self.provider == ExternalProvider.CLAUDE:
            return self._anthropic_client is not None
        elif self.provider == ExternalProvider.GPT4:
            return self._openai_client is not None
        else:
            return False

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the external model."""
        # Check availability synchronously without asyncio.run()
        available = False
        if self.provider == ExternalProvider.CLAUDE:
            available = self._anthropic_client is not None
        elif self.provider == ExternalProvider.GPT4:
            available = self._openai_client is not None

        info = {
            "provider": self.provider.value,
            "available": available,
            "context_size": self.get_context_size(),
        }

        if self.provider == ExternalProvider.CLAUDE:
            info["default_model"] = "claude-3-opus-20240229"
            info["client_available"] = self._anthropic_client is not None
        elif self.provider == ExternalProvider.GPT4:
            info["default_model"] = "gpt-4"
            info["client_available"] = self._openai_client is not None

        return info

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: Optional[str] = None,
    ) -> float:
        """Estimate API cost in USD (rough estimates)."""
        if self.provider == ExternalProvider.CLAUDE:
            # Claude 3 Opus pricing (as of 2024)
            input_cost = input_tokens * 0.000015   # $15 per 1M input tokens
            output_cost = output_tokens * 0.000075  # $75 per 1M output tokens
            return input_cost + output_cost
        elif self.provider == ExternalProvider.GPT4:
            # GPT-4 pricing (as of 2024)
            input_cost = input_tokens * 0.00003    # $30 per 1M input tokens
            output_cost = output_tokens * 0.00006  # $60 per 1M output tokens
            return input_cost + output_cost
        else:
            return 0.0


class ExternalLLMManager:
    """Manager for multiple external LLM providers."""

    def __init__(self) -> None:
        """Initialize the manager."""
        self.providers: dict[ExternalProvider, ExternalLLM] = {}
        self._setup_providers()

    def _setup_providers(self) -> None:
        """Setup available providers."""
        # Only attempt setup if we have API keys
        if config.anthropic_api_key:
            try:
                self.providers[ExternalProvider.CLAUDE] = ExternalLLM(ExternalProvider.CLAUDE)
            except Exception:
                # Silently skip Claude setup if there are compatibility issues
                pass

        if config.openai_api_key:
            try:
                self.providers[ExternalProvider.GPT4] = ExternalLLM(ExternalProvider.GPT4)
            except Exception:
                # Silently skip GPT-4 setup if there are compatibility issues
                pass

    async def get_best_available(self, prefer_claude: bool = True) -> Optional[ExternalLLM]:
        """Get the best available external LLM."""
        if prefer_claude and ExternalProvider.CLAUDE in self.providers:
            claude = self.providers[ExternalProvider.CLAUDE]
            if await claude.is_available():
                return claude

        if ExternalProvider.GPT4 in self.providers:
            gpt4 = self.providers[ExternalProvider.GPT4]
            if await gpt4.is_available():
                return gpt4

        if not prefer_claude and ExternalProvider.CLAUDE in self.providers:
            claude = self.providers[ExternalProvider.CLAUDE]
            if await claude.is_available():
                return claude

        return None

    async def get_provider(self, provider: ExternalProvider) -> Optional[ExternalLLM]:
        """Get specific provider if available."""
        if provider in self.providers:
            llm = self.providers[provider]
            if await llm.is_available():
                return llm
        return None

    def list_available_providers(self) -> list[ExternalProvider]:
        """List all available providers."""
        available = []
        for provider, llm in self.providers.items():
            # Check if client was successfully initialized
            if provider == ExternalProvider.CLAUDE and llm._anthropic_client is not None:
                available.append(provider)
            elif provider == ExternalProvider.GPT4 and llm._openai_client is not None:
                available.append(provider)
        return available
