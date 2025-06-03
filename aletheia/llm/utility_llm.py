"""Utility LLM implementation using small model for fast, simple tasks."""

import asyncio
from typing import Any, Optional

try:
    from llama_cpp import Llama
except ImportError:
    print("Warning: llama-cpp-python not installed. Utility LLM will not work.")
    Llama = None

from ..config import config
from ..identity import identity


class UtilityLLM:
    """Small, fast LLM for utility tasks like classification, extraction, preprocessing."""

    def __init__(self) -> None:
        """Initialize the utility LLM."""
        self.model: Optional[Llama] = None
        self.model_loaded = False
        self._init_lock = asyncio.Lock()
        
        # Utility model path (should be set in config)
        self.model_path = getattr(config, 'utility_model_path', None)
        if not self.model_path:
            # Fallback to a reasonable default
            self.model_path = config.local_model_path.parent / "phi-3-mini-3.8b-q4_k.gguf"

    async def _load_model(self) -> None:
        """Load the utility model with optimized settings for speed."""
        if self.model_loaded or not Llama:
            return

        if not self.model_path.exists():
            print(f"⚠️ Utility model not found at {self.model_path}")
            print("   Falling back to main model for utility tasks")
            return

        print(f"🔄 Loading utility model: {self.model_path}")

        # Optimized settings for small, fast model
        model_kwargs = {
            "model_path": str(self.model_path),
            "n_ctx": 2048,  # Small context for utility tasks
            "verbose": False,
            "n_batch": 256,  # Smaller batch for speed
            "n_threads": None,  # Auto-detect
            # Speed optimizations
            "use_mmap": True,
            "use_mlock": True,
            "f16_kv": True,
        }

        # Hardware acceleration with fewer layers for small model
        if config.use_metal:
            model_kwargs["n_gpu_layers"] = 32  # Fewer layers for mini model
            print(f"🚀 Utility model using Metal with {model_kwargs['n_gpu_layers']} GPU layers")
        elif config.use_cuda:
            model_kwargs["n_gpu_layers"] = 32
            print(f"🚀 Utility model using CUDA with {model_kwargs['n_gpu_layers']} GPU layers")
        else:
            model_kwargs["n_gpu_layers"] = 0
            print("💻 Utility model using CPU-only mode")

        # Load model in thread pool
        self.model = await asyncio.get_event_loop().run_in_executor(
            None, lambda: Llama(**model_kwargs)
        )

        self.model_loaded = True
        print("✅ Utility model loaded successfully")

    async def ensure_loaded(self) -> None:
        """Ensure model is loaded, thread-safe."""
        if not self.model_loaded:
            async with self._init_lock:
                if not self.model_loaded:
                    await self._load_model()

    async def classify_query(self, query: str) -> str:
        """Classify user query into semantic categories."""
        await self.ensure_loaded()
        
        if not self.model:
            # Fallback to rule-based classification
            return self._fallback_classify_query(query)

        system_prompt = """You are a fast query classifier. Classify the user query into ONE category:

CATEGORIES:
- technical: Scientific, engineering, physics, chemistry, mathematics
- explanation: Questions asking how/what/why about processes
- conversational: Greetings, personal chat, introductions
- personal_data: Questions about user data, measurements, stats
- general: Everything else

Respond with ONLY the category name."""

        formatted_prompt = f"<|system|>{system_prompt}<|end|>\n<|user|>{query}<|end|>\n<|assistant|>"

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model(
                    formatted_prompt,
                    max_tokens=10,
                    temperature=0.1,  # Very low for consistent classification
                    stop=["<|end|>", "<|user|>"],
                    echo=False
                )
            )
            
            classification = result["choices"][0]["text"].strip().lower()
            
            # Validate classification
            valid_categories = ['technical', 'explanation', 'conversational', 'personal_data', 'general']
            if classification in valid_categories:
                return classification
            else:
                # Fallback if invalid response
                return self._fallback_classify_query(query)
                
        except Exception as e:
            print(f"⚠️ Utility model classification failed: {e}")
            return self._fallback_classify_query(query)

    async def classify_memory_content(self, content: str) -> str:
        """Classify memory content for semantic matching."""
        await self.ensure_loaded()
        
        if not self.model:
            return self._fallback_classify_memory(content)

        # Extract key part for classification if it's a task memory
        content_to_classify = content
        if content.startswith('Task:'):
            lines = content.split('\n')
            task_line = next((line for line in lines if line.startswith('Task:')), '')
            content_to_classify = task_line.replace('Task:', '').strip()

        system_prompt = """You are a memory content classifier. Classify the content into ONE category:

CATEGORIES:
- technical: Scientific, engineering, physics topics
- conversational: Greetings, personal conversation
- personal_data: User measurements, personal information
- general: Other topics

Respond with ONLY the category name."""

        formatted_prompt = f"<|system|>{system_prompt}<|end|>\n<|user|>{content_to_classify}<|end|>\n<|assistant|>"

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model(
                    formatted_prompt,
                    max_tokens=10,
                    temperature=0.1,
                    stop=["<|end|>", "<|user|>"],
                    echo=False
                )
            )
            
            classification = result["choices"][0]["text"].strip().lower()
            
            valid_categories = ['technical', 'conversational', 'personal_data', 'general']
            if classification in valid_categories:
                return classification
            else:
                return self._fallback_classify_memory(content)
                
        except Exception as e:
            print(f"⚠️ Utility model memory classification failed: {e}")
            return self._fallback_classify_memory(content)

    async def extract_topic(self, text: str, max_length: int = 50) -> str:
        """Extract main topic from text."""
        await self.ensure_loaded()
        
        if not self.model:
            return self._fallback_extract_topic(text, max_length)

        system_prompt = f"""Extract the main topic from the text in {max_length} characters or less.
Respond with ONLY the topic, no explanations."""

        formatted_prompt = f"<|system|>{system_prompt}<|end|>\n<|user|>{text}<|end|>\n<|assistant|>"

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model(
                    formatted_prompt,
                    max_tokens=20,
                    temperature=0.2,
                    stop=["<|end|>", "<|user|>"],
                    echo=False
                )
            )
            
            topic = result["choices"][0]["text"].strip()
            
            # Truncate if too long
            if len(topic) > max_length:
                topic = topic[:max_length-3] + "..."
                
            return topic if topic else self._fallback_extract_topic(text, max_length)
                
        except Exception as e:
            print(f"⚠️ Utility model topic extraction failed: {e}")
            return self._fallback_extract_topic(text, max_length)

    async def detect_language(self, text: str) -> str:
        """Detect primary language of text."""
        await self.ensure_loaded()
        
        # Simple fallback that's very fast
        if any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in text.lower()):
            return "ru"
        else:
            return "en"

    async def expand_query_concepts(self, query: str, language: str = "auto") -> list[str]:
        """Extract and expand key concepts from query for better semantic matching."""
        await self.ensure_loaded()
        
        if not self.model:
            return self._fallback_expand_concepts(query, language)

        if language == "auto":
            language = await self.detect_language(query)

        lang_name = "Russian" if language == "ru" else "English"
        
        system_prompt = f"""Extract 3-5 key concepts from the query and provide related synonyms in {lang_name}.
Format: concept1, synonym1, synonym2; concept2, synonym3, synonym4

Example: 
Query: "how does a car engine work"
Response: engine, motor, mechanism; work, function, operate"""

        formatted_prompt = f"<|system|>{system_prompt}<|end|>\n<|user|>{query}<|end|>\n<|assistant|>"

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model(
                    formatted_prompt,
                    max_tokens=50,
                    temperature=0.3,
                    stop=["<|end|>", "<|user|>"],
                    echo=False
                )
            )
            
            concepts_text = result["choices"][0]["text"].strip()
            
            # Parse concepts
            concepts = []
            for group in concepts_text.split(';'):
                group_concepts = [c.strip() for c in group.split(',') if c.strip()]
                concepts.extend(group_concepts)
            
            # Limit to 8 concepts max
            return concepts[:8] if concepts else self._fallback_expand_concepts(query, language)
                
        except Exception as e:
            print(f"⚠️ Utility model concept expansion failed: {e}")
            return self._fallback_expand_concepts(query, language)

    # Fallback methods using rule-based logic
    def _fallback_classify_query(self, query: str) -> str:
        """Rule-based query classification fallback."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['двигатель', 'тепловой', 'физик', 'квантов', 'механизм', 'принцип', 'engine', 'thermal', 'physics', 'quantum', 'mechanism', 'principle']):
            return 'technical'
        elif any(word in query_lower for word in ['как', 'что такое', 'расскажи', 'объясни', 'устроен', 'работает', 'how', 'what is', 'explain', 'tell me', 'works']):
            return 'explanation'
        elif any(word in query_lower for word in ['привет', 'как дела', 'кто', 'меня зовут', 'hello', 'how are', 'who are', 'my name']):
            return 'conversational'
        elif any(word in query_lower for word in ['данные', 'рост', 'вес', 'возраст', 'data', 'height', 'weight', 'age']):
            return 'personal_data'
        else:
            return 'general'

    def _fallback_classify_memory(self, content: str) -> str:
        """Rule-based memory classification fallback."""
        content_lower = content.lower()
        
        if content.startswith('Task:'):
            lines = content.split('\n')
            task_line = next((line for line in lines if line.startswith('Task:')), '')
            task_content = task_line.replace('Task:', '').strip().lower()
            
            if any(word in task_content for word in ['двигатель', 'тепловой', 'физик', 'квантов', 'механизм', 'engine', 'thermal', 'physics', 'quantum']):
                return 'technical'
            elif any(word in task_content for word in ['привет', 'как дела', 'кто', 'зовут', 'hello', 'how are', 'who are']):
                return 'conversational'
            elif any(word in task_content for word in ['данные', 'рост', 'вес', 'data', 'height', 'weight']):
                return 'personal_data'
            else:
                return 'general'
        
        if any(word in content_lower for word in ['двигатель', 'тепловой', 'физик', 'квантов', 'engine', 'thermal', 'physics', 'quantum']):
            return 'technical'
        elif any(word in content_lower for word in ['привет', 'hello', 'как дела', 'how are']):
            return 'conversational'
        else:
            return 'general'

    def _fallback_extract_topic(self, text: str, max_length: int) -> str:
        """Rule-based topic extraction fallback."""
        # Simple extraction - first meaningful words
        words = text.split()
        topic_words = []
        
        for word in words[:8]:  # Look at first 8 words
            clean_word = word.strip('.,!?:;()[]{}"\'-')
            if len(clean_word) > 2 and not clean_word.lower() in ['the', 'and', 'or', 'but', 'что', 'как', 'это']:
                topic_words.append(clean_word)
                if len(' '.join(topic_words)) >= max_length - 10:
                    break
        
        topic = ' '.join(topic_words)
        if len(topic) > max_length:
            topic = topic[:max_length-3] + "..."
        
        return topic if topic else "general_topic"

    def _fallback_expand_concepts(self, query: str, language: str) -> list[str]:
        """Rule-based concept expansion fallback."""
        query_lower = query.lower()
        concepts = []
        
        if language == "ru":
            concept_map = {
                'двигатель': ['мотор', 'механизм', 'устройство'],
                'тепловой': ['температура', 'нагрев', 'термический'],
                'квантов': ['квант', 'физика', 'частица'],
                'энергия': ['мощность', 'сила', 'работа']
            }
        else:
            concept_map = {
                'engine': ['motor', 'mechanism', 'device'],
                'thermal': ['temperature', 'heat', 'thermodynamic'],
                'quantum': ['physics', 'particle', 'mechanics'],
                'energy': ['power', 'force', 'work']
            }
        
        for term, synonyms in concept_map.items():
            if term in query_lower:
                concepts.extend([term] + synonyms)
        
        return concepts[:5]  # Limit to 5 concepts

    async def is_available(self) -> bool:
        """Check if utility model is available."""
        try:
            await self.ensure_loaded()
            return self.model is not None
        except Exception:
            return False

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the utility model."""
        return {
            "model_path": str(self.model_path),
            "context_size": 2048,
            "purpose": "utility_tasks",
            "loaded": self.model_loaded,
            "fallback_available": True,  # Always has rule-based fallbacks
        } 