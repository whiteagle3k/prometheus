"""Local LLM implementation using llama.cpp with Metal acceleration."""

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import os
import sys
import time
import logging
import json

# Set environment variable to quiet llama.cpp
os.environ["LLAMA_DEBUG"] = "0"

# Optional: Redirect stderr during import of llama_cpp
# This will silence output during model loading
import contextlib

# Create null file descriptor
class NullWriter:
    def write(self, x): pass
    def flush(self): pass

# Temporarily redirect stderr during model loading
old_stderr = sys.stderr
sys.stderr = NullWriter()

try:
    # Import llama_cpp with reduced output
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import get_chat_format
except ImportError:
    Llama = None
    get_chat_format = None
    print("⚠️ llama_cpp not installed. Local models will not work.")

# Restore stderr
sys.stderr = old_stderr

from core.config import config

# TODO: Remove direct identity import - should be passed from entity
# from ..identity import identity
from core.processing.pipeline import create_simple_response_pipeline
from core.processing.filters import ContaminationFilter

logger = logging.getLogger(__name__)


class LocalLLM:
    """Local LLM using llama.cpp with hardware acceleration."""

    def __init__(self, identity_config: dict | None = None) -> None:
        """Initialize the local LLM."""
        self.model: Llama | None = None
        self.model_loaded = False
        self._init_lock = asyncio.Lock()

        # TODO: Properly inject identity configuration from entity
        self.identity_config = identity_config or {
            "name": "AI Assistant",
            "personality": {"summary": "A helpful AI assistant"},
            "module_paths": {"performance_config": {}},
            "system_prompts": {
                "en": "You are a helpful AI assistant.",
                "ru": "Вы полезный ИИ-помощник."
            },
            "llm_instructions": "You are a helpful AI assistant."
        }

        # Initialize processing pipeline for response cleanup
        self.response_pipeline = create_simple_response_pipeline()

    async def _load_model(self) -> None:
        """Load the local model with proper hardware acceleration."""
        if self.model_loaded or not Llama:
            return

        # Get model path from identity configuration first, then fall back to config
        model_path = config.local_model_path  # Default fallback

        try:
            if "module_paths" in self.identity_config and "local_model_gguf" in self.identity_config["module_paths"]:
                identity_model_path = Path(self.identity_config["module_paths"]["local_model_gguf"])
                if identity_model_path.exists():
                    model_path = identity_model_path
                    print(f"📁 Using model from identity: {model_path}")
                else:
                    print(f"⚠️ Identity model not found: {identity_model_path}, using default")
        except Exception as e:
            print(f"⚠️ Error reading model path from identity: {e}, using default")

        if not model_path.exists():
            msg = (
                f"Model not found at {model_path}. "
                "Run scripts/download_models.sh first."
            )
            raise FileNotFoundError(msg)

        # Get performance config from identity if available
        try:
            performance_config = self.identity_config["module_paths"]["performance_config"] or {}
        except:
            performance_config = {}

        # Redirect stdout temporarily to suppress llama.cpp output
        import sys
        import os
        original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

        try:
            # Configure hardware acceleration with optimizations
            model_kwargs = {
                "model_path": str(model_path),
                "n_ctx": performance_config.get("context_size", config.local_model_context_size),
                "n_batch": performance_config.get("batch_size", 512),
                "n_threads": 1,  # Single thread to reduce output
                "use_mmap": True,
                "use_mlock": True,
                "f16_kv": True,
                "verbose": False,  # Disable verbose mode
                "log_level": "error",  # Only show errors
                "offload_kqv": True,  # Reduce initialization messages
                "embedding": False,  # Disable embedding initialization messages
                "print_details": False  # Suppress model details printing
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
                print("💻 Using CPU-only mode")

            # Load model in thread pool to avoid blocking
            self.model = await asyncio.get_event_loop().run_in_executor(
                None, lambda: Llama(**model_kwargs)
            )
            self.model_loaded = True
            print("✅ Local model loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load local model: {e}")
            if "GGML_ASSERT" in str(e):
                print("💡 GGML assertion failed. This can happen if the model is not compatible")
                print("   with the current version of llama-cpp-python or if the model file is corrupt.")
                print("   Try rebuilding llama-cpp-python or re-downloading the model.")
            raise RuntimeError(f"Could not load local model at {model_path}") from e
        finally:
            # Restore stdout
            sys.stdout = original_stdout

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
        stop: list | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate text using the local model."""
        await self.ensure_loaded()

        if not self.model:
            msg = "Local model not available"
            raise RuntimeError(msg)

        # Check if we're using Phi-4
        is_phi4 = False
        if hasattr(self, "model") and self.model:
            model_info = self.model.model_path
            is_phi4 = "phi-4" in str(model_info)
            
        # Format prompt for Phi-3/Phi-4 chat format
        formatted_prompt = self._format_chat_prompt(prompt, system_prompt)

        # Select appropriate stop tokens based on model
        if is_phi4:
            default_stop = ["<|im_end|>", "<|im_start|>"]  # Phi-4 stop tokens
        else:
            default_stop = ["<|end|>", "<|user|>"]  # Phi-3 stop tokens

        # Prepare generation parameters
        generate_kwargs = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stop": stop or default_stop,
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
        # Check if we're using Phi-4 (again) for proper token cleanup
        is_phi4 = False
        if hasattr(self, "model") and self.model:
            model_info = self.model.model_path
            is_phi4 = "phi-4" in str(model_info)
            
        if is_phi4:
            # Phi-4 format cleanup
            response = response.replace("<|im_end|>", "").strip()
        else:
            # Phi-3 format cleanup
            response = response.replace("<|end|>", "").replace("<|assistant|>", "").strip()

        # Detect language for fallback
        is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in prompt.lower())

        # If response is too short or corrupted after processing, provide fallback
        if len(response) < 20 or not any(char.isalpha() for char in response):
            response = self._get_fallback_response(is_russian)

        return response

    def _get_fallback_response(self, is_russian: bool) -> str:
        """Get fallback response based on identity configuration."""

        # Fallback greeting if no specific greeting available
        try:
            name = self.identity_config.get('name', 'AI Assistant')
            personality = self.identity_config.get('personality', {})
            summary = personality.get('summary', 'helpful AI assistant')
            return f"Hello! I'm {name}, {summary.lower()}. How can I help you?"
        except Exception as e:
            print(f"⚠️ Error accessing identity config in greeting: {e}")
            return "Hello! I'm an AI assistant. How can I help you?"

    def _format_chat_prompt(self, prompt: str, system_prompt: str | None = None) -> str:
        """Format prompt for Phi-3/Phi-4 chat format using identity configuration."""

        # Detect language of the prompt
        is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in prompt.lower())
        
        # Check if we're using Phi-4
        is_phi4 = False
        if hasattr(self, "model") and self.model:
            model_info = self.model.model_path
            is_phi4 = "phi-4" in str(model_info)

        formatted = ""

        # Use provided system prompt or get from identity
        if system_prompt:
            final_system_prompt = system_prompt
        else:
            # Get system prompt from identity configuration
            language = "ru" if is_russian else "en"
            # For user-facing responses, use language-specific prompts (for gender forms)
            final_system_prompt = self.identity_config["system_prompts"][language]

        # Use different chat templates for Phi-3 vs Phi-4
        if is_phi4:
            # Phi-4 format uses <|im_start|> and <|im_end|>
            formatted += f"<|im_start|>system\n{final_system_prompt}<|im_end|>\n"
            formatted += f"<|im_start|>user\n{prompt}<|im_end|>\n"
            formatted += f"<|im_start|>assistant\n"
        else:
            # Phi-3 format uses <|system|> and <|end|>
            formatted += f"<|system|>{final_system_prompt}<|end|>\n"
            formatted += f"<|user|>{prompt}<|end|>\n<|assistant|>"

        return formatted

    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: list | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Generate text with streaming output."""
        await self.ensure_loaded()

        if not self.model:
            msg = "Local model not available"
            raise RuntimeError(msg)

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
            "identity": self.identity_config,
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
        context: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate structured response with parsing for agent tasks."""
        await self.ensure_loaded()

        if not self.model:
            msg = "Local model not available"
            raise RuntimeError(msg)

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
        parsed_result = self._parse_structured_response(raw_response, prompt)
        
        return parsed_result

    def _format_structured_prompt(self, prompt: str, context: str | None = None) -> str:
        """Format prompt to request structured response from local LLM."""

        # Use the system instructions from identity config directly
        system_prompt = self.identity_config.get("llm_instructions", "You are a helpful AI assistant.")

        # Detect if user is asking in Russian to emphasize feminine forms
        is_russian_query = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in prompt.lower())

        # Enhance system prompt for Russian queries to ensure feminine forms
        if is_russian_query:
            system_prompt += "\n\nIMPORTANT FOR RUSSIAN: Use ONLY feminine forms: готова (never готов), рада (never рад), смогу помочь, могу помочь. Your identity is female."

        # Check if this is an ongoing conversation (similar to external LLM logic)
        is_ongoing_conversation = bool(context and context.strip() and any(
            marker in context
            for marker in ["👤 You:", "🧠", "User:", "Assistant:", "Human:", "AI:", "Exchange", "🤖"]
        ))

        # Add conversation flow instructions
        if is_ongoing_conversation:
            system_prompt += """\n\nCRITICAL INSTRUCTION: This is a CONTINUATION of an ongoing conversation. You are already talking to this user. 
DO NOT SAY: "Привет", "Здравствуйте", "Hello", "Hi", or any greetings.
DO NOT SAY: "Как дела", "How are you", or ask how they are.
DO NOT SAY: "Рада познакомиться", "Nice to meet you", or similar introductions.
CONTINUE the conversation naturally without any greetings or introductions.
The user is asking a follow-up question in an ongoing conversation."""
        
        # Build context section
        context_section = ""
        if context:
            context_section = f"\n\nCONVERSATION CONTEXT: {context}"

        # Simple structured instruction format
        return f"""<|system|>{system_prompt}<|end|>
<|user|>{prompt}{context_section}

Please respond in this format:

ANSWER: [your response to the user]
CONFIDENCE: [high/medium/low]
REASONING: [brief explanation]

Respond naturally in the user's language.<|end|>
<|assistant|>"""


    def _parse_structured_response(self, raw_response: str, original_prompt: str) -> dict[str, Any]:
        """Parse structured response from local LLM using processing pipeline."""

        # Use contamination filter for basic cleanup first
        filter_processor = ContaminationFilter()
        filter_result = filter_processor.process(raw_response)
        response = filter_result.data if filter_result.success else raw_response.strip()

        # Default structure (simplified - no routing logic)
        parsed = {
            "answer": "",
            "confidence": "medium",
            "reasoning": "",
            "raw_response": raw_response
        }

        # Try inline parsing first
        self._parse_inline_format(response, parsed)

        # If inline parsing didn't work well, try line-based parsing
        if not parsed["answer"]:
            self._parse_line_format(response, parsed)

        # Clean any remaining structured markers from the answer
        if parsed["answer"]:
            parsed["answer"] = self._clean_answer_from_markers(parsed["answer"])

        # Enhanced fallback and cleanup
        if not parsed["answer"] or len(parsed["answer"]) < 5:
            self._extract_contextual_answer(response, parsed, original_prompt)
            if parsed["answer"]:
                parsed["answer"] = self._clean_answer_from_markers(parsed["answer"])

        return parsed

    def _clean_answer_from_markers(self, answer: str) -> str:
        """Completely remove any structured field markers from the answer."""
        import re

        # Remove structured field patterns (English and Russian)
        cleaned = re.sub(r"\b(?:ANSWER|CONFIDENCE|REASONING|КОНФИДЕНЦИЯ|РАЗУМЕНИЕ|ОТВЕТ):\s*[^\n]*\n?", "", answer, flags=re.IGNORECASE)

        # Remove any remaining field patterns at start/end
        cleaned = re.sub(r"^(?:ANSWER|CONFIDENCE|REASONING|КОНФИДЕНЦИЯ|РАЗУМЕНИЕ|ОТВЕТ):\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"(?:CONFIDENCE|REASONING|КОНФИДЕНЦИЯ|РАЗУМЕНИЕ):\s*.*$", "", cleaned, flags=re.IGNORECASE)

        # Remove common contamination patterns at start of response
        cleaned = re.sub(r"^[A-ZА-Я]{5,}:\s*", "", cleaned)

        # Clean up extra whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Remove common contamination patterns (English and Russian)
        cleaned = re.sub(r"\b(high|medium|low|высокая|средняя|низкая)\s*(confidence|конфиденция)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(reasoning|разумение):\s*", "", cleaned, flags=re.IGNORECASE)

        # Remove any remaining field markers that might be scattered in text
        cleaned = re.sub(r"\b(CONFIDENCE|КОНФИДЕНЦИЯ)\b[:\s]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(REASONING|РАЗУМЕНИЕ)\b[:\s]*", "", cleaned, flags=re.IGNORECASE)

        # Remove specific Russian contamination patterns seen in output
        cleaned = re.sub(r"КОНФИДЕНЦИЯ:\s*высокая\s*РАЗУМЕНИЕ:\s*[^.]*\.", "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def _parse_inline_format(self, response: str, parsed: dict) -> None:
        """Parse inline format where all fields are on one line."""
        import re

        # Extract answer (from start to first field marker) - English and Russian
        answer_match = re.search(r"(?:ANSWER|Ответ):\s*(.+?)(?=\s+(?:CONFIDENCE|REASONING|Доверие|Причина):|$)", response, re.IGNORECASE)
        if answer_match:
            parsed["answer"] = answer_match.group(1).strip()

        # Extract confidence - English and Russian
        conf_match = re.search(r"(?:CONFIDENCE|Доверие):\s*(\w+)", response, re.IGNORECASE)
        if conf_match:
            conf_text = conf_match.group(1).lower()
            if "high" in conf_text or "высокое" in conf_text or "высокая" in conf_text:
                parsed["confidence"] = "high"
            elif "low" in conf_text or "низкое" in conf_text or "низкая" in conf_text:
                parsed["confidence"] = "low"
            else:
                parsed["confidence"] = "medium"

        # Extract reasoning - English and Russian
        reason_match = re.search(r"(?:REASONING|Причина|Разумение):\s*(.+?)$", response, re.IGNORECASE)
        if reason_match:
            parsed["reasoning"] = reason_match.group(1).strip()

    def _parse_line_format(self, response: str, parsed: dict) -> None:
        """Parse line-based format where each field is on a separate line."""
        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse different fields (English and Russian)
            if line.startswith("ANSWER:") or line.startswith("Ответ:"):
                answer_text = line.split(":", 1)[1].strip()
                if answer_text and not parsed["answer"]:
                    parsed["answer"] = answer_text
            elif line.startswith("CONFIDENCE:") or line.startswith("Доверие:"):
                conf_text = line.split(":", 1)[1].strip().lower()
                if "high" in conf_text or "высокое" in conf_text or "высокая" in conf_text:
                    parsed["confidence"] = "high"
                elif "low" in conf_text or "низкое" in conf_text or "низкая" in conf_text:
                    parsed["confidence"] = "low"
                else:
                    parsed["confidence"] = "medium"
            elif line.startswith("REASONING:") or line.startswith("Причина:") or line.startswith("Разумение:"):
                reasoning_text = line.split(":", 1)[1].strip()
                if reasoning_text and not parsed["reasoning"]:
                    parsed["reasoning"] = reasoning_text

    def _extract_contextual_answer(self, response: str, parsed: dict, original_prompt: str) -> None:
        """Extract answer with better context preservation, avoiding topic loss."""

        # First, try to find any substantial content that could be an answer
        lines = response.split("\n")
        potential_answers = []

        for line in lines:
            line = line.strip()
            if (line and
                not line.upper().startswith(("ANSWER:", "CONFIDENCE:", "REASONING:", "EXTERNAL_NEEDED:")) and
                len(line) > 15 and  # Increase minimum length
                not line.startswith("<|") and  # Skip format tokens
                any(char.isalpha() for char in line) and  # Must contain letters
                not line.startswith(("Привет!", "Hello!", "Здравствуйте"))):  # Skip generic greetings
                potential_answers.append(line)

        # Pick the longest substantial answer
        if potential_answers:
            parsed["answer"] = max(potential_answers, key=len)
            parsed["confidence"] = "low"  # Set low confidence for extracted answers
            parsed["reasoning"] = "Answer extracted from unstructured response"
            return

        # If still no good answer, try to find any content at all
        all_text = " ".join(lines).strip()
        # Remove structured markers
        import re
        clean_text = re.sub(r"\b(?:ANSWER|CONFIDENCE|REASONING|EXTERNAL_NEEDED):\s*[^\n]*", "", all_text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        if clean_text and len(clean_text) > 20:
            parsed["answer"] = clean_text
            parsed["confidence"] = "low"
            parsed["reasoning"] = "Fallback extraction from response"
            return

        # Last resort: Generate contextual fallback instead of generic greeting
        is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in original_prompt.lower())
        parsed["answer"] = self._get_contextual_fallback(original_prompt, is_russian)
        parsed["confidence"] = "low"
        parsed["reasoning"] = "Contextual fallback due to parsing failure"

    def _get_contextual_fallback(self, original_prompt: str, is_russian: bool) -> str:
        """Generate contextual fallback response instead of generic greeting."""

        # Detect topic/domain from the prompt for better fallbacks
        prompt_lower = original_prompt.lower()

        # Technical/scientific topics
        if any(word in prompt_lower for word in ["двигатель", "тепловой", "квантов", "физик", "engine", "thermal", "quantum", "physics"]):
            if is_russian:
                return "Извините, у меня возникли сложности с ответом на ваш технический вопрос. Возможно, стоит обратиться к внешним источникам для получения более точной информации."
            else:
                return "I'm having difficulty providing a complete answer to your technical question. You might want to consult external sources for more accurate information."

        # Questions about processes or explanations
        if any(word in prompt_lower for word in ["как", "что такое", "расскажи", "объясни", "how", "what is", "explain", "tell me"]):
            if is_russian:
                return "Извините, мне нужно больше времени, чтобы правильно ответить на ваш вопрос. Можете переформулировать его или обратиться за более подробной информацией?"
            else:
                return "I need more time to properly answer your question. Could you rephrase it or seek more detailed information elsewhere?"

        # Generic fallback (last resort)
        if is_russian:
            return "Извините, я испытываю технические трудности с обработкой вашего запроса. Попробуйте переформулировать вопрос."
        else:
            return "I'm experiencing technical difficulties processing your request. Please try rephrasing your question."
