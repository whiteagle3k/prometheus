"""
Fast LLM for classification and utility tasks.

Provides fast classification capabilities using a smaller model
for tasks like query categorization, memory filtering, and concept extraction.
"""

import asyncio
from pathlib import Path
from typing import Any, List, Optional

try:
    from llama_cpp import Llama
except ImportError:
    print("Warning: llama-cpp-python not installed. Fast LLM will not work.")
    Llama = None

from ..config import config
# TODO: Remove direct identity import - should be passed from entity
# from ..identity import identity


class FastLLM:
    """Small, fast LLM for utility tasks like classification, extraction, preprocessing."""

    def __init__(self, identity_config: Optional[dict] = None) -> None:
        """Initialize the utility LLM."""
        self.model: Optional[Llama] = None
        self.model_loaded = False
        self._init_lock = asyncio.Lock()
        self.identity_config = identity_config
        
        # Utility model path (should be set in config)
        self.model_path = getattr(config, 'utility_model_path', None)
        if not self.model_path:
            # Fallback to a reasonable default
            self.model_path = config.local_model_path.parent / "phi-3-mini-3.8b-q4_k.gguf"
        
        # Get utility performance config from identity or use defaults
        self.utility_config = self._get_utility_config()

    def _get_utility_config(self) -> dict[str, Any]:
        """Get utility model performance configuration from identity or defaults."""
        if self.identity_config and "module_paths" in self.identity_config:
            utility_config = self.identity_config["module_paths"].get("utility_performance_config", {})
            
            # Use identity config with fallbacks to reasonable defaults
            return {
                "gpu_layers": utility_config.get("gpu_layers", 12),
                "context_size": utility_config.get("context_size", 2048),
                "batch_size": utility_config.get("batch_size", 256),
                "threads": utility_config.get("threads", 4)
            }
        else:
            # Default configuration for utility model
            return {
                "gpu_layers": 12,
                "context_size": 2048,
                "batch_size": 256,
                "threads": 4
            }

    async def _load_model(self) -> None:
        """Load the utility model with optimized settings for speed."""
        if self.model_loaded or not Llama:
            return

        if not self.model_path.exists():
            print(f"⚠️ Utility model not found at {self.model_path}")
            print("   Falling back to main model for utility tasks")
            return

        print(f"🔄 Loading utility model: {self.model_path}")

        # Optimized settings for small, fast model using configuration
        model_kwargs = {
            "model_path": str(self.model_path),
            "n_ctx": self.utility_config["context_size"],
            "verbose": False,
            "n_batch": self.utility_config["batch_size"],
            "n_threads": self.utility_config["threads"],
            # Speed optimizations
            "use_mmap": True,
            "use_mlock": True,
            "f16_kv": True,
        }

        # Hardware acceleration with configurable layers
        gpu_layers = self.utility_config["gpu_layers"]
        if config.use_metal:
            model_kwargs["n_gpu_layers"] = gpu_layers
            print(f"🚀 Utility model using Metal with {gpu_layers} GPU layers")
        elif config.use_cuda:
            model_kwargs["n_gpu_layers"] = gpu_layers
            print(f"🚀 Utility model using CUDA with {gpu_layers} GPU layers")
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

        # Reset context for independent classification
        await self._reset_model_context()

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

        # Reset context for independent classification
        await self._reset_model_context()

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

    async def make_routing_decision(self, query: str, context: Optional[str] = None) -> dict[str, Any]:
        """
        Make a routing decision for the query using fast LLM as neutral arbiter.
        
        This is the core Fast LLM routing oracle that makes unbiased routing decisions
        independent of the main LLM that would handle the query.
        """
        await self.ensure_loaded()
        
        if not self.model:
            print("⚠️ Fast LLM not available for routing, using fallback")
            return self._fallback_routing_decision(query)

        # Reset context to avoid contamination between routing decisions
        await self._reset_model_context()

        # Build clean routing context - limit to prevent contamination
        context_info = ""
        if context and len(context.strip()) > 0:
            # Clean and limit context to prevent overwhelming Fast LLM
            clean_context = context.strip()[:200]  # Max 200 chars
            context_info = f"\nRecent context: {clean_context}"

        # Routing oracle prompt - designed to be neutral and unbiased
        system_prompt = f"""You are a routing oracle. Decide which LLM should handle this query:

LOCAL: Use for general conversation, simple explanations, basic tasks
EXTERNAL: Use for complex analysis, current events, specialized knowledge

Consider:
- Query complexity and depth required
- Whether latest knowledge is needed
- Computational requirements

Format: ROUTE: [LOCAL/EXTERNAL]
CONFIDENCE: [high/medium/low]
COMPLEXITY: [simple/moderate/complex]
REASONING: [brief explanation]"""

        formatted_prompt = f"<|system|>{system_prompt}<|end|>\n<|user|>Query: {query}{context_info}\n\nRouting decision:<|end|>\n<|assistant|>"

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model(
                    formatted_prompt,
                    max_tokens=100,
                    temperature=0.2,  # Low temperature for consistent routing
                    stop=["<|end|>", "<|user|>"],
                    echo=False
                )
            )
            
            response = result["choices"][0]["text"].strip()
            
            # Parse structured response
            route = "LOCAL"
            confidence = "medium"
            complexity = "moderate"
            reasoning = "Fast LLM routing decision"
            
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith("ROUTE:"):
                    route_text = line.split(":", 1)[1].strip().upper()
                    if route_text in ["LOCAL", "EXTERNAL"]:
                        route = route_text
                elif line.startswith("CONFIDENCE:"):
                    conf_text = line.split(":", 1)[1].strip().lower()
                    if conf_text in ["high", "medium", "low"]:
                        confidence = conf_text
                elif line.startswith("COMPLEXITY:"):
                    comp_text = line.split(":", 1)[1].strip().lower()
                    if comp_text in ["simple", "moderate", "complex"]:
                        complexity = comp_text
                elif line.startswith("REASONING:"):
                    reasoning = line.split(":", 1)[1].strip()
                    
            return {
                'route': route,
                'confidence': confidence,
                'complexity': complexity,
                'reasoning': reasoning
            }
            
        except Exception as e:
            print(f"⚠️ Fast LLM routing failed: {e}")
            return self._fallback_routing_decision(query)

    async def classify_prompt(self, prompt: str, classification_type: str) -> dict[str, Any]:
        """
        General-purpose classification method for Self-RAG components.
        
        Args:
            prompt: The prompt to classify/analyze
            classification_type: Type of classification needed
            
        Returns:
            Dictionary with classification result
        """
        await self.ensure_loaded()
        
        if not self.model:
            print(f"⚠️ Fast LLM not available for {classification_type}, using fallback")
            return {"classification": "Unable to classify - model not available"}

        # Reset context for independent classification
        await self._reset_model_context()

        # Create system prompt based on classification type
        if classification_type in ["memory_quality_evaluation", "memory_enhancement"]:
            system_prompt = """You are a memory quality evaluator. Analyze the given prompt and provide a structured response following the exact format requested."""
        elif classification_type in ["response_quality_assessment", "comprehensive_reflection"]:
            system_prompt = """You are a response quality assessor. Analyze the given content and provide detailed evaluation following the exact format requested."""
        elif classification_type in ["context_relevance_assessment", "retrieval_quality_assessment", "context_quality_evaluation"]:
            system_prompt = """You are a context quality evaluator. Assess the relevance and quality of context for given tasks following the exact format requested."""
        else:
            system_prompt = """You are a general classifier. Analyze the given content and provide a structured response following the format requested."""

        formatted_prompt = f"<|system|>{system_prompt}<|end|>\n<|user|>{prompt}<|end|>\n<|assistant|>"

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model(
                    formatted_prompt,
                    max_tokens=300,  # Allow more tokens for detailed analysis
                    temperature=0.3,  # Balanced temperature for analysis
                    stop=["<|end|>", "<|user|>"],
                    echo=False
                )
            )
            
            classification = result["choices"][0]["text"].strip()
            
            return {
                "classification": classification,
                "classification_type": classification_type,
                "model_used": "fast_llm"
            }
            
        except Exception as e:
            print(f"⚠️ Fast LLM classification failed for {classification_type}: {e}")
            return {
                "classification": f"Classification failed: {str(e)}",
                "classification_type": classification_type,
                "model_used": "fallback"
            }

    async def _reset_model_context(self) -> None:
        """Reset model context to prevent contamination between independent tasks."""
        if not self.model:
            return
            
        try:
            # Method 1: Try explicit reset if available
            if hasattr(self.model, 'reset'):
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.model.reset()
                )
                return
            
            # Method 2: Clear internal state if available  
            if hasattr(self.model, '_ctx'):
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: setattr(self.model, '_ctx', None)
                )
                return
                
            # Method 3: Force context separation with explicit tokens
            # This is more aggressive - we'll generate a clearing prompt
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model(
                    "<|system|>Clear context<|end|>\n<|user|>Reset<|end|>\n<|assistant|>",
                    max_tokens=1,
                    temperature=0.1,
                    stop=["<|end|>"],
                    echo=False
                )
            )
            
        except Exception as e:
            # If all reset methods fail, we'll rely on explicit context isolation in prompts
            print(f"⚠️ Could not reset utility model context: {e}")

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
        """Fallback concept expansion using simple keyword matching."""
        # Basic concept expansion based on keywords
        concepts = []
        
        query_lower = query.lower()
        
        # Technical concepts
        if any(word in query_lower for word in ['система', 'механизм', 'принцип', 'процесс']):
            concepts.extend(['технология', 'инженерия', 'принцип работы'])
        
        if any(word in query_lower for word in ['system', 'mechanism', 'principle', 'process']):
            concepts.extend(['technology', 'engineering', 'working principle'])
        
        # Scientific concepts
        if any(word in query_lower for word in ['квантовый', 'физика', 'химия']):
            concepts.extend(['наука', 'исследование', 'теория'])
            
        if any(word in query_lower for word in ['quantum', 'physics', 'chemistry']):
            concepts.extend(['science', 'research', 'theory'])
        
        return concepts[:3]  # Limit to avoid noise

    def _fallback_routing_decision(self, query: str) -> dict[str, Any]:
        """Fallback routing decision using rule-based logic."""
        query_lower = query.lower()
        
        # Scientific/technical keywords that should go to external
        external_keywords = [
            # Russian scientific terms
            'квантов', 'физик', 'химия', 'биология', 'математика', 'инженер',
            'механизм', 'принцип', 'теория', 'формула', 'уравнение',
            'двигатель', 'энергия', 'мощность', 'система', 'процесс',
            # English scientific terms  
            'quantum', 'physics', 'chemistry', 'biology', 'mathematics', 'engineering',
            'mechanism', 'principle', 'theory', 'formula', 'equation',
            'engine', 'energy', 'power', 'system', 'process'
        ]
        
        # Simple conversational keywords that stay local
        local_keywords = [
            'привет', 'hello', 'hi', 'как дела', 'how are you', 'кто ты', 'who are you',
            'спасибо', 'thank', 'пока', 'bye', 'хорошо', 'good', 'да', 'yes', 'нет', 'no'
        ]
        
        # Check for external routing triggers
        if any(keyword in query_lower for keyword in external_keywords):
            return {
                "route": "EXTERNAL",
                "confidence": "high", 
                "reasoning": "Scientific/technical topic detected",
                "complexity": "scientific"
            }
        
        # Check for simple local conversations
        if any(keyword in query_lower for keyword in local_keywords):
            return {
                "route": "LOCAL",
                "confidence": "high",
                "reasoning": "Simple conversation",
                "complexity": "simple"
            }
        
        # Default to local for moderate complexity
        return {
            "route": "LOCAL", 
            "confidence": "medium",
            "reasoning": "General query, trying local first",
            "complexity": "moderate"
        }

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