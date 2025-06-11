"""Anthropic Claude provider implementation."""

import warnings
from collections.abc import AsyncGenerator
from typing import Any, Dict, List, Optional, Tuple
import logging
import time
import asyncio
import json

from core.config import config

try:
    import anthropic
except ImportError:
    print("Warning: anthropic not installed. Anthropic provider will not work.")
    anthropic = None

from .base import (
    ExternalLLMProvider,
    GenerationRequest,
    GenerationResponse,
    ProviderCapabilities,
    ProviderType,
)

logger = logging.getLogger(__name__)


class AnthropicProvider(ExternalLLMProvider):
    """Anthropic Claude provider implementation."""

    def _get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.ANTHROPIC

    def _get_capabilities(self) -> ProviderCapabilities:
        """Get the provider capabilities."""
        return ProviderCapabilities(
            streaming=True,
            json_mode=True,
            tools=True,
            vision=True,
            function_calling=True
        )

    def _build_system_prompt(self, system_prompt: str) -> str:
        """
        Format the system prompt for Anthropic.
        Claude takes system prompts as-is.
        """
        return system_prompt

    async def _get_client(self) -> Any:
        """
        Get an Anthropic client instance.
        
        Returns:
            An initialized Anthropic client
        """
        if not anthropic:
            raise RuntimeError("anthropic package not installed")
            
        # Get API key from config
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError("No Anthropic API key found in configuration")
            
        # Create client
        client = anthropic.AsyncAnthropic(api_key=api_key)
        return client

    async def store_memory_points(self, memory_points: List[Dict[str, Any]]) -> None:
        """
        Store memory points for future retrieval.
        This is a stub method to maintain compatibility with OpenAI provider.
        Anthropic doesn't have memory points storage yet.
        
        Args:
            memory_points: List of memory points to store
        """
        # This is just a stub method - does nothing in the Anthropic provider
        # but maintains interface compatibility with OpenAI provider
        pass
        
    async def _generate_completion(
        self, 
        request: GenerationRequest
    ) -> GenerationResponse:
        """
        Generate a completion from Anthropic.
        
        Args:
            request: Generation request parameters
            
        Returns:
            Response with text and metadata
        """
        start_time = time.time()
        
        try:
            client = await self._get_client()
            
            # Determine which model to use
            model = request.model or config.anthropic_model or "claude-3-opus-20240229"
            
            # Build message content
            if request.system_prompt:
                system = request.system_prompt
            else:
                system = "You are a helpful, harmless, and honest AI assistant."
            
            # Extract image data if present
            messages = []
            if request.image_data:
                content = [{"type": "text", "text": request.prompt}]
                
                # Add each image
                for i, image_data in enumerate(request.image_data):
                    if isinstance(image_data, str) and image_data.startswith(("http://", "https://")):
                        # URL-based image
                        content.append({
                            "type": "image", 
                            "source": {"type": "url", "url": image_data}
                        })
                    elif isinstance(image_data, bytes) or (isinstance(image_data, str) and image_data.startswith("data:")):
                        # Base64 encoded image
                        if isinstance(image_data, bytes):
                            import base64
                            image_b64 = base64.b64encode(image_data).decode('utf-8')
                            media_type = "image/jpeg"  # Assume JPEG if not specified
                        else:
                            # Extract from data URL
                            media_type = image_data.split(";")[0].split(":")[1]
                            image_b64 = image_data.split(",")[1]
                            
                        content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64
                            }
                        })
                messages = [{"role": "user", "content": content}]
            else:
                # Text-only message
                messages = [{"role": "user", "content": request.prompt}]
            
            # Handle tools/function calling
            request_kwargs = {
                "model": model,
                "system": system,
                "messages": messages,
                "max_tokens": request.max_tokens or 1024,
                "temperature": request.temperature or 0.7,
            }
            
            if request.tools:
                request_kwargs["tools"] = request.tools
                
            # Debug: print outgoing request
            print(f"[ANTHROPIC REQUEST] model={model}, tools={request_kwargs.get('tools')}, prompt={request.prompt[:200]}")
                
            # Make the API call
            response = await client.messages.create(**request_kwargs)
            
            # Parse the response
            generated_text = response.content[0].text
            
            # Handle tools/function calling
            tool_calls = []
            if response.model_extra and "tool_use" in response.model_extra:
                tool_use = response.model_extra["tool_use"]
                if tool_use:
                    tool_call = {
                        "name": tool_use["name"],
                        "arguments": json.loads(tool_use["input"])
                    }
                    tool_calls.append(tool_call)
                    
            # Debug: print raw response
            if config.debug_mode:
                print(f"[ANTHROPIC RAW RESPONSE] {response}")
                    
            elapsed_time = time.time() - start_time
            return GenerationResponse(
                text=generated_text,
                raw_response=response,
                finish_reason=response.stop_reason,
                usage={"prompt_tokens": response.usage.input_tokens, "completion_tokens": response.usage.output_tokens},
                provider="anthropic",
                model=model,
                elapsed_time=elapsed_time,
                tool_calls=tool_calls
            )
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Error in Anthropic provider: {e}")
            return GenerationResponse(
                text=f"Error: {str(e)}",
                raw_response={"error": str(e)},
                finish_reason="error",
                usage={"prompt_tokens": 0, "completion_tokens": 0},
                provider="anthropic",
                model=request.model,
                elapsed_time=elapsed_time,
                error=str(e)
            )

    async def _generate_completion_stream(
        self, 
        request: GenerationRequest
    ) -> AsyncGenerator[GenerationResponse, None]:
        """
        Generate a streaming completion from Anthropic.
        
        Args:
            request: Generation request parameters
            
        Yields:
            Streaming response with partial text and metadata
        """
        start_time = time.time()
        
        try:
            client = await self._get_client()
            
            # Determine which model to use
            model = request.model or config.anthropic_model or "claude-3-opus-20240229"
            
            # Build message content
            if request.system_prompt:
                system = request.system_prompt
            else:
                system = "You are a helpful, harmless, and honest AI assistant."
            
            # Extract image data if present
            messages = []
            if request.image_data:
                content = [{"type": "text", "text": request.prompt}]
                
                # Add each image
                for i, image_data in enumerate(request.image_data):
                    if isinstance(image_data, str) and image_data.startswith(("http://", "https://")):
                        # URL-based image
                        content.append({
                            "type": "image", 
                            "source": {"type": "url", "url": image_data}
                        })
                    elif isinstance(image_data, bytes) or (isinstance(image_data, str) and image_data.startswith("data:")):
                        # Base64 encoded image
                        if isinstance(image_data, bytes):
                            import base64
                            image_b64 = base64.b64encode(image_data).decode('utf-8')
                            media_type = "image/jpeg"  # Assume JPEG if not specified
                        else:
                            # Extract from data URL
                            media_type = image_data.split(";")[0].split(":")[1]
                            image_b64 = image_data.split(",")[1]
                            
                        content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64
                            }
                        })
                messages = [{"role": "user", "content": content}]
            else:
                # Text-only message
                messages = [{"role": "user", "content": request.prompt}]
            
            # Handle tools/function calling
            request_kwargs = {
                "model": model,
                "system": system,
                "messages": messages,
                "max_tokens": request.max_tokens or 1024,
                "temperature": request.temperature or 0.7,
                "stream": True
            }
            
            if request.tools:
                request_kwargs["tools"] = request.tools
            
            # Make the API call
            stream = await client.messages.create(**request_kwargs)
            
            # Return streaming responses
            buffer = ""
            usage = {"prompt_tokens": 0, "completion_tokens": 0}
            
            async for chunk in stream:
                delta = ""
                if hasattr(chunk, 'delta') and chunk.delta and hasattr(chunk.delta, 'text'):
                    delta = chunk.delta.text or ""
                elif hasattr(chunk, 'content') and chunk.content and len(chunk.content) > 0:
                    # If we have content blocks, extract text
                    for content_block in chunk.content:
                        if content_block.type == "text":
                            delta = content_block.text
                
                buffer += delta
                
                # Update token usage if available
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = {
                        "prompt_tokens": getattr(chunk.usage, 'input_tokens', 0),
                        "completion_tokens": getattr(chunk.usage, 'output_tokens', 0)
                    }
                
                elapsed_time = time.time() - start_time
                yield GenerationResponse(
                    text=buffer,
                    raw_response=chunk,
                    finish_reason=None,
                    usage=usage,
                    provider="anthropic",
                    model=model,
                    elapsed_time=elapsed_time,
                    is_chunk=True,
                    delta=delta
                )
            
            # Final response with complete data
            elapsed_time = time.time() - start_time
            
            yield GenerationResponse(
                text=buffer,
                raw_response={"message": buffer},
                finish_reason="stop",
                usage=usage,
                provider="anthropic",
                model=model,
                elapsed_time=elapsed_time,
                is_chunk=False,
                delta=""
            )
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Error in Anthropic streaming: {e}")
            
            yield GenerationResponse(
                text=f"Error: {str(e)}",
                raw_response={"error": str(e)},
                finish_reason="error",
                usage={"prompt_tokens": 0, "completion_tokens": 0},
                provider="anthropic",
                model=model,
                elapsed_time=elapsed_time,
                error=str(e)
            )

    async def _health_check(self) -> bool:
        """Check if Anthropic API is healthy."""
        if not self._client:
            return False

        try:
            # Make a minimal API call to check health
            response = await self._client.messages.create(
                model=self.config.get("model", "claude-3-5-sonnet-20240620"),
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return response is not None
        except Exception:
            return False

    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        return self.config.get("model", "claude-3-5-sonnet-20240620")

    def supports_function_calling(self) -> bool:
        """Check if this provider supports function calling."""
        return True

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
