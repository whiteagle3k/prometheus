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
from ..identity import identity


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

        # Get performance config from identity if available
        try:
            performance_config = identity.module_paths.performance_config or {}
        except:
            performance_config = {}

        # Configure hardware acceleration with optimizations
        model_kwargs = {
            "model_path": str(config.local_model_path),
            "n_ctx": performance_config.get("context_size", config.local_model_context_size),
            "verbose": False,
            "n_batch": performance_config.get("batch_size", 512),  # Default to 512 for better balance
            "n_threads": performance_config.get("threads", None),  # Auto-detect or use configured
            # Performance optimizations
            "use_mmap": True,  # Memory-map model file for faster loading
            "use_mlock": True,  # Lock model in memory to prevent swapping
            "f16_kv": True,  # Use fp16 for key/value cache
        }

        # Hardware-specific optimizations
        if config.use_metal:
            gpu_layers = performance_config.get("gpu_layers", config.local_model_gpu_layers)
            model_kwargs["n_gpu_layers"] = gpu_layers
            print(f"🚀 Using Metal acceleration with {gpu_layers} GPU layers")
        elif config.use_cuda:
            gpu_layers = performance_config.get("gpu_layers", config.local_model_gpu_layers)
            model_kwargs["n_gpu_layers"] = gpu_layers
            print(f"🚀 Using CUDA acceleration with {gpu_layers} GPU layers")
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

        # Clean up any remaining chat tokens and formatting issues
        response = response.replace("<|end|>", "").replace("<|assistant|>", "").strip()
        
        # Detect language for cleanup
        is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in prompt.lower())
        
        # More aggressive cleanup for contamination patterns
        contamination_patterns = [
            r"Written by Assistant:.*",
            r"Written by Aletheia.*", 
            r"Follow-up Question \d+:.*",
            r"\*\*How would.*",
            r"\*\*Solution:\*\*.*",
            r"What if the user.*",
            r"Пользователь:.*",
            r"User:.*",
            r"CV Template.*",
            r"Имя: Алетейя.*",
            r"Omnipotent AI:.*",
            r"Ответ:.*",
            r"Relevant context:.*",
            r"Task:.*Approach:.*Response:.*",
            r"theoretical.*",
            r"аминь.*",
            r"Follow up questions:.*",
            r"\*\*Follow up questions:\*\*.*",
            r"Solutions for follow up questions:.*",
            r"\*\*Solutions.*",
            r"Now, here are three more.*",
            r"How can you ensure.*",
            r"How can you handle.*",
            r"How can AI ensure.*",
            r"--- \*\*Instruction.*",  # New: Training instruction artifacts
            r"AVOID:.*",               # New: Training constraints
            r"Additional Constraint:.*", # New: Training constraints
            r"You are Aletheia,.*advanced analytical.*", # New: Spurious identity descriptions
            r"Вопрос:.*Римской империи.*", # New: Roman Empire training leakage
            r"падения Римской империи.*", # New: Roman Empire training leakage
            r"Эдуард Гиббон.*",        # New: Historical training leakage
            r"работе \"История упадка.*", # New: Historical training leakage
        ]
        
        import re
        for pattern in contamination_patterns:
            response = re.sub(pattern, "", response, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove obvious training artifacts and mixed content
        lines = response.split('\n')
        clean_lines = []
        
        # Skip lines with obvious contamination
        for line in lines:
            line = line.strip()
            # Skip lines with obvious contamination
            if any(marker in line.lower() for marker in [
                "cv template", "имя:", "опыт работы:", "контакты:", "специальности:",
                "task:", "approach:", "response:", "relevant context:",
                "omnipotent ai", "аминь", "theoretical", "follow up questions:",
                "solutions for follow up", "how can you", "how can ai", 
                "now, here are", "gender role representation", "programmed rules",
                "--- **", "**more complex", "avoid:", "additional constraint:",
                "падения римской", "эдуард гиббон", "> # this is", "code|", "|>"
            ]):
                continue
            # Skip very short fragments
            if len(line) < 3:
                continue
            # Skip lines that repeat the same pattern
            if line.count('алетейя') > 2 or line.count('иван') > 1:
                continue
            clean_lines.append(line)
        
        # Rebuild response from clean lines
        if clean_lines:
            response = ' '.join(clean_lines)
        else:
            # If nothing is left, provide fallback based on identity
            response = self._get_fallback_response(is_russian)
        
        # Final cleanup - stop at first major contamination marker
        contamination_stops = [
            "CV Template", "Имя:", "Task:", "Relevant context:", "theoretical",
            "###", "Follow up questions", "Solutions for follow up", 
            "Now, here are", "How can you", "How can AI", "--- **Instruction",
            "AVOID:", "Additional Constraint:", "падения Римской империи", 
            "Эдуард Гиббон", "История упадка", "работе \"История"
        ]
        for stop in contamination_stops:
            if stop in response:
                response = response.split(stop)[0].strip()
                break  # Stop at first contamination found
        
        # Clean up multiple spaces and normalize
        response = re.sub(r'\s+', ' ', response).strip()
        
        # Remove obvious duplications (sentences or phrases that repeat)
        sentences = response.split('. ')
        clean_sentences = []
        seen_sentences = set()
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Normalize sentence for comparison (remove punctuation, lowercase)
            normalized = re.sub(r'[^\w\s]', '', sentence.lower()).strip()
            
            # Skip if we've seen a very similar sentence (70% similarity threshold)
            is_duplicate = False
            for seen in seen_sentences:
                # Simple similarity check: if 70%+ of words are the same
                seen_words = set(seen.split())
                current_words = set(normalized.split())
                if len(current_words) > 0:
                    similarity = len(seen_words & current_words) / len(current_words | seen_words)
                    if similarity > 0.7:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                clean_sentences.append(sentence)
                seen_sentences.add(normalized)
        
        # Rebuild response from clean sentences
        if clean_sentences:
            response = '. '.join(clean_sentences)
            # Add final period if missing and response doesn't end with other punctuation
            if response and not response.endswith(('.', '!', '?')):
                response += '.'
        
        # If response is still too short or seems corrupted, provide a fallback
        if len(response) < 20 or not any(char.isalpha() for char in response):
            response = self._get_fallback_response(is_russian)

        # VERY early and aggressive contamination stopping - cut response at first sign
        early_contamination_stops = [
            "-----", "---", "instruction", "constraint", "ограничения:", "limitations:",
            "you are aletheia,", "ты алетейя,", "core principles:", "key traits:",
            "пользователя зовут анна", "user name is anna", "вопрос:"
        ]
        
        for stop in early_contamination_stops:
            if stop in response.lower():
                response = response.split(stop)[0].strip()
                print(f"🛑 Early contamination stop at: '{stop}'")
                break

        return response

    def _get_fallback_response(self, is_russian: bool) -> str:
        """Get fallback response based on identity configuration."""
        language = "ru" if is_russian else "en"
        return identity.get_fallback_response(language)

    def _format_chat_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Format prompt for Phi-3 chat format using identity configuration."""
        
        # Detect language of the prompt
        is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in prompt.lower())
        
        formatted = ""

        # Use provided system prompt or get from identity
        if system_prompt:
            final_system_prompt = system_prompt
        else:
            # Get system prompt from identity configuration
            language = "ru" if is_russian else "en"
            final_system_prompt = identity.get_system_prompt(language)

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
            "identity": identity.to_dict(),
        }

    async def unload(self) -> None:
        """Unload the model to free memory."""
        if self.model:
            # llama.cpp doesn't have explicit cleanup, but we can remove reference
            self.model = None
            self.model_loaded = False
            print("🗑️  Local model unloaded")
