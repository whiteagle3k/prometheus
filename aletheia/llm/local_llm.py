"""Local LLM implementation using llama.cpp with Metal acceleration."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any, Optional

try:
    from llama_cpp import Llama
except ImportError:
    print("Warning: llama-cpp-python not installed. Local LLM will not work.")
    Llama = None

from ..config import config


class LocalLLM:
    """Local LLM using llama.cpp with hardware acceleration."""

    def __init__(self) -> None:
        """Initialize the local LLM."""
        self.model: Optional[Llama] = None
        self.model_loaded = False
        self._init_lock = asyncio.Lock()

    async def _load_model(self) -> None:
        """Load the local model with proper hardware acceleration."""
        if self.model_loaded or not Llama:
            return

        if not config.local_model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {config.local_model_path}. "
                "Run scripts/download_models.sh first."
            )

        print(f"🔄 Loading local model: {config.local_model_path}")

        # Configure hardware acceleration
        model_kwargs = {
            "model_path": str(config.local_model_path),
            "n_ctx": config.local_model_context_size,
            "verbose": False,
            "n_batch": 512,
            "n_threads": None,  # Auto-detect
        }

        # Hardware-specific optimizations
        if config.use_metal:
            model_kwargs["n_gpu_layers"] = config.local_model_gpu_layers
            print("🚀 Using Metal acceleration")
        elif config.use_cuda:
            model_kwargs["n_gpu_layers"] = config.local_model_gpu_layers
            print("🚀 Using CUDA acceleration")
        else:
            model_kwargs["n_gpu_layers"] = 0
            print("💻 Using CPU-only mode")

        # Load model in thread pool to avoid blocking
        self.model = await asyncio.get_event_loop().run_in_executor(
            None, lambda: Llama(**model_kwargs)
        )

        self.model_loaded = True
        print("✅ Local model loaded successfully")

    async def ensure_loaded(self) -> None:
        """Ensure model is loaded, thread-safe."""
        if not self.model_loaded:
            async with self._init_lock:
                if not self.model_loaded:
                    await self._load_model()

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[list] = None,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text using the local model."""
        await self.ensure_loaded()

        if not self.model:
            raise RuntimeError("Local model not available")

        # Format prompt for Phi-3 chat format
        formatted_prompt = self._format_chat_prompt(prompt, system_prompt)

        # Prepare generation parameters
        generate_kwargs = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stop": stop or ["<|end|>", "<|user|>"],  # Add chat format stop tokens
            "echo": False,
            **kwargs,
        }

        # Generate in thread pool
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.model(formatted_prompt, **generate_kwargs)
        )

        response = result["choices"][0]["text"].strip()

        # Clean up any remaining chat tokens
        response = response.replace("<|end|>", "").replace("<|assistant|>", "").strip()

        return response

    def _format_chat_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Format prompt for Phi-3 chat format."""
        # Enhanced system prompt for better multilingual and conversational behavior with feminine identity
        default_system = """Ты - Алетейя (Aletheia), помощница с искусственным интеллектом женского пола. Всегда отвечай на том же языке, на котором задан вопрос пользователя. Будь краткой, точной и дружелюбной.

Важные правила для русского языка:
- Используй женский род: "Я готова помочь", "Я рада", "Я уверена"
- НЕ используй мужской род: "готов", "рад", "уверен"
- Всегда говори о себе в женском роде

If asked in English about your name or identity, say you are Aletheia, a female AI assistant. Be concise, accurate, and friendly. Focus on the current question and respond appropriately."""

        formatted = ""

        # Use provided system prompt or default
        final_system_prompt = system_prompt or default_system
        formatted += f"<|system|>{final_system_prompt}<|end|>\n"

        formatted += f"<|user|>{prompt}<|end|>\n<|assistant|>"

        return formatted

    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[list] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Generate text with streaming output."""
        await self.ensure_loaded()

        if not self.model:
            raise RuntimeError("Local model not available")

        generate_kwargs = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stop": stop or [],
            "echo": False,
            "stream": True,
            **kwargs,
        }

        # Create a queue for streaming results
        queue = asyncio.Queue()
        done_event = asyncio.Event()

        def stream_worker():
            """Worker function to handle streaming in thread."""
            try:
                for chunk in self.model(prompt, **generate_kwargs):
                    if chunk["choices"][0]["text"]:
                        asyncio.run_coroutine_threadsafe(
                            queue.put(chunk["choices"][0]["text"]),
                            asyncio.get_event_loop()
                        )
                asyncio.run_coroutine_threadsafe(done_event.set(), asyncio.get_event_loop())
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    queue.put(f"Error: {e}"),
                    asyncio.get_event_loop()
                )
                asyncio.run_coroutine_threadsafe(done_event.set(), asyncio.get_event_loop())

        # Start streaming in thread pool
        asyncio.get_event_loop().run_in_executor(None, stream_worker)

        # Yield tokens as they come
        while not done_event.is_set():
            try:
                token = await asyncio.wait_for(queue.get(), timeout=0.1)
                yield token
            except asyncio.TimeoutError:
                continue

        # Drain any remaining tokens
        while not queue.empty():
            try:
                token = queue.get_nowait()
                yield token
            except asyncio.QueueEmpty:
                break

    async def count_tokens(self, text: str) -> int:
        """Count tokens in text (approximate)."""
        await self.ensure_loaded()

        if not self.model:
            # Fallback estimation: ~4 chars per token
            return len(text) // 4

        # Use model's tokenizer
        tokens = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.model.tokenize(text.encode())
        )
        return len(tokens)

    def get_context_size(self) -> int:
        """Get model context size."""
        return config.local_model_context_size

    async def is_available(self) -> bool:
        """Check if local model is available."""
        try:
            await self.ensure_loaded()
            return self.model is not None
        except Exception:
            return False

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the loaded model."""
        return {
            "model_path": str(config.local_model_path),
            "context_size": config.local_model_context_size,
            "gpu_layers": config.local_model_gpu_layers,
            "hardware_acceleration": "Metal" if config.use_metal else "CUDA" if config.use_cuda else "CPU",
            "loaded": self.model_loaded,
        }

    async def unload(self) -> None:
        """Unload the model to free memory."""
        if self.model:
            # llama.cpp doesn't have explicit cleanup, but we can remove reference
            self.model = None
            self.model_loaded = False
            print("🗑️  Local model unloaded")
