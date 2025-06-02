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
from ..processing.pipeline import create_simple_response_pipeline


class LocalLLM:
    """Local LLM using llama.cpp with hardware acceleration."""

    def __init__(self) -> None:
        """Initialize the local LLM."""
        self.model: Optional[Llama] = None
        self.model_loaded = False
        self._init_lock = asyncio.Lock()
        
        # Initialize processing pipeline for response cleanup
        self.response_pipeline = create_simple_response_pipeline()

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

        raw_response = result["choices"][0]["text"].strip()

        # Use new processing pipeline instead of hardcoded cleanup
        pipeline_result = self.response_pipeline.process(raw_response)
        response = pipeline_result["processed_text"]

        # Basic cleanup that's still needed
        response = response.replace("<|end|>", "").replace("<|assistant|>", "").strip()
        
        # Detect language for fallback
        is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in prompt.lower())
        
        # If response is too short or corrupted after processing, provide fallback
        if len(response) < 20 or not any(char.isalpha() for char in response):
            response = self._get_fallback_response(is_russian)

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

    async def generate_structured(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate structured response with parsing for agent tasks."""
        await self.ensure_loaded()

        if not self.model:
            raise RuntimeError("Local model not available")

        # Build structured prompt
        structured_prompt = self._format_structured_prompt(prompt, context)

        # Generate response
        generate_kwargs = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stop": ["<|end|>", "<|user|>", "---END---", "\n\nПРИМЕРЫ", "\n\nVAЖНЫЕ", "\n\nIMPORTANT", "\n\nОБЯЗАТЕЛЬНО", "\n\nМОЖНО"],
            "echo": False,
            **kwargs,
        }

        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.model(structured_prompt, **generate_kwargs)
        )

        raw_response = result["choices"][0]["text"].strip()
        
        # Parse structured response
        return self._parse_structured_response(raw_response, prompt)

    def _format_structured_prompt(self, prompt: str, context: Optional[str] = None) -> str:
        """Format prompt to request structured response from local LLM."""
        
        # Detect language
        is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in prompt.lower())
        language = "ru" if is_russian else "en"
        
        # Get system prompt from identity
        system_prompt = identity.get_system_prompt(language)
        
        # Build context section
        context_section = ""
        if context:
            if is_russian:
                context_section = f"\n\nКОНТЕКСТ: {context}"
            else:
                context_section = f"\n\nCONTEXT: {context}"

        # Build structured instruction
        if is_russian:
            instruction = f"""<|system|>{system_prompt}

Ответь в следующем формате:

ОТВЕТ: [прямой ответ пользователю]
УВЕРЕННОСТЬ: [высокая/средняя/низкая]
ОБОСНОВАНИЕ: [краткое объяснение]
ВНЕШНИЙ_ЗАПРОС: [да для технических/научных вопросов, нет для общения]

ПРАВИЛА РАБОТЫ С ПАМЯТЬЮ:
- Если в RELEVANT PAST EXPERIENCES есть нужная информация (особенно с пометкой KEY DATA) - используй её
- Для запросов о данных пользователя (рост, вес, процент жира) ищи конкретные цифры в памяти
- Если память содержит ответ, установи ВНЕШНИЙ_ЗАПРОС=нет
- Если памяти недостаточно для полного ответа, установи ВНЕШНИЙ_ЗАПРОС=да

Используй ВНЕШНИЙ_ЗАПРОС=да для: состав материалов, работа техники, научные факты.
Используй ВНЕШНИЙ_ЗАПРОС=нет для: приветствий, общения, вопросов обо мне, данных из памяти.<|end|>
<|user|>{prompt}{context_section}<|end|>
<|assistant|>"""
        else:
            instruction = f"""<|system|>{system_prompt}

Respond in this format:

ANSWER: [direct response to user]
CONFIDENCE: [high/medium/low]
REASONING: [brief explanation]
EXTERNAL_NEEDED: [yes for technical/scientific, no for conversation]

MEMORY USAGE RULES:
- If RELEVANT PAST EXPERIENCES contains needed information (especially marked KEY DATA) - use it
- For user data queries (height, weight, body fat percentage) look for specific numbers in memory
- If memory contains the answer, set EXTERNAL_NEEDED=no
- If memory is insufficient for complete answer, set EXTERNAL_NEEDED=yes

Use EXTERNAL_NEEDED=yes for: material composition, how things work, scientific facts.
Use EXTERNAL_NEEDED=no for: greetings, chat, questions about me, data from memory.<|end|>
<|user|>{prompt}{context_section}<|end|>
<|assistant|>"""

        return instruction

    def _parse_structured_response(self, raw_response: str, original_prompt: str) -> dict[str, Any]:
        """Parse structured response from local LLM using processing pipeline."""
        
        # Use contamination filter for basic cleanup first
        from ..processing.filters import ContaminationFilter
        filter_processor = ContaminationFilter()
        filter_result = filter_processor.process(raw_response)
        response = filter_result.data if filter_result.success else raw_response.strip()
        
        # Default structure
        parsed = {
            "answer": "",
            "confidence": "medium",
            "reasoning": "",
            "external_needed": False,
            "raw_response": raw_response
        }

        # Try to parse structured format - handle both original and filtered versions
        lines = response.replace('\n', ' ').split()  # Split by any whitespace
        text_parts = []
        
        current_field = None
        current_content = []
        
        for part in lines:
            # Check if this is a field marker
            if part.upper() in ('ОТВЕТ:', 'ANSWER:'):
                if current_field and current_content:
                    # Store previous field
                    if current_field == 'answer':
                        parsed["answer"] = ' '.join(current_content)
                current_field = 'answer'
                current_content = []
            elif part.upper() in ('УВЕРЕННОСТЬ:', 'CONFIDENCE:'):
                if current_field and current_content:
                    # Store previous field
                    if current_field == 'answer':
                        parsed["answer"] = ' '.join(current_content)
                current_field = 'confidence'
                current_content = []
            elif part.upper() in ('ОБОСНОВАНИЕ:', 'REASONING:'):
                if current_field and current_content:
                    # Store previous field
                    if current_field == 'answer':
                        parsed["answer"] = ' '.join(current_content)
                    elif current_field == 'confidence':
                        conf_text = ' '.join(current_content).lower()
                        if 'высокая' in conf_text or 'high' in conf_text:
                            parsed["confidence"] = "high"
                        elif 'низкая' in conf_text or 'low' in conf_text:
                            parsed["confidence"] = "low"
                        else:
                            parsed["confidence"] = "medium"
                current_field = 'reasoning'
                current_content = []
            elif part.upper() in ('ВНЕШНИЙ_ЗАПРОС:', 'EXTERNAL_NEEDED:'):
                if current_field and current_content:
                    # Store previous field
                    if current_field == 'answer':
                        parsed["answer"] = ' '.join(current_content)
                    elif current_field == 'confidence':
                        conf_text = ' '.join(current_content).lower()
                        if 'высокая' in conf_text or 'high' in conf_text:
                            parsed["confidence"] = "high"
                        elif 'низкая' in conf_text or 'low' in conf_text:
                            parsed["confidence"] = "low"
                        else:
                            parsed["confidence"] = "medium"
                    elif current_field == 'reasoning':
                        parsed["reasoning"] = ' '.join(current_content)
                current_field = 'external_needed'
                current_content = []
            else:
                # Add to current field content
                if current_field:
                    current_content.append(part)
        
        # Store final field
        if current_field and current_content:
            if current_field == 'answer':
                parsed["answer"] = ' '.join(current_content)
            elif current_field == 'confidence':
                conf_text = ' '.join(current_content).lower()
                if 'высокая' in conf_text or 'high' in conf_text:
                    parsed["confidence"] = "high"
                elif 'низкая' in conf_text or 'low' in conf_text:
                    parsed["confidence"] = "low"
                else:
                    parsed["confidence"] = "medium"
            elif current_field == 'reasoning':
                parsed["reasoning"] = ' '.join(current_content)
            elif current_field == 'external_needed':
                ext_text = ' '.join(current_content).lower()
                parsed["external_needed"] = 'да' in ext_text or 'yes' in ext_text

        # Fallback parsing if structured parsing didn't work
        if not parsed["answer"]:
            # Try old line-based approach
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Parse different fields
                if line.startswith(('ОТВЕТ:', 'ANSWER:')):
                    parsed["answer"] = line.split(':', 1)[1].strip()
                elif line.startswith(('УВЕРЕННОСТЬ:', 'CONFIDENCE:')):
                    conf_text = line.split(':', 1)[1].strip().lower()
                    if 'высокая' in conf_text or 'high' in conf_text:
                        parsed["confidence"] = "high"
                    elif 'низкая' in conf_text or 'low' in conf_text:
                        parsed["confidence"] = "low"
                    else:
                        parsed["confidence"] = "medium"
                elif line.startswith(('ОБОСНОВАНИЕ:', 'REASONING:')):
                    parsed["reasoning"] = line.split(':', 1)[1].strip()
                elif line.startswith(('ВНЕШНИЙ_ЗАПРОС:', 'EXTERNAL_NEEDED:')):
                    ext_text = line.split(':', 1)[1].strip().lower()
                    parsed["external_needed"] = 'да' in ext_text or 'yes' in ext_text

        # If still no structured answer found, use the whole response as answer
        if not parsed["answer"]:
            # Try to find a reasonable answer in the text
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if (line and 
                    not line.startswith(('ОТВЕТ:', 'ANSWER:', 'УВЕРЕННОСТЬ:', 'CONFIDENCE:', 
                                        'ОБОСНОВАНИЕ:', 'REASONING:', 'ВНЕШНИЙ_ЗАПРОС:', 'EXTERNAL_NEEDED:')) and
                    len(line) > 10):
                    parsed["answer"] = line
                    break
            
            # If still no answer, use cleaned response
            if not parsed["answer"]:
                parsed["answer"] = response

        # Fallback for empty answers
        if not parsed["answer"] or len(parsed["answer"]) < 3:
            is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in original_prompt.lower())
            parsed["answer"] = self._get_fallback_response(is_russian)
            parsed["confidence"] = "low"
            parsed["reasoning"] = "Fallback response due to parsing error"

        return parsed
