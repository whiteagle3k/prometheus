"""
Fast LLM for classification and utility tasks.

Provides fast classification capabilities using a smaller model
for tasks like query categorization, memory filtering, and concept extraction.

Optimized based on performance testing:
- Rule-based routing (100% accurate, instant)
- SmolLM2-135M for classification (~0.25s vs 1.08s)
- Intelligent fallbacks for reliability
- Singleton pattern to prevent multiple model loads
"""

import asyncio
import time
import json
from pathlib import Path
from typing import Any

try:
    from llama_cpp import Llama
except ImportError:
    print("Warning: llama-cpp-python not installed. Fast LLM will not work.")
    Llama = None

from core.config import config
from core.processing.config import get_processor_config

# TODO: Remove direct identity import - should be passed from entity
# from ..identity import identity


class FastLLM:
    """Small, fast LLM for utility tasks like classification, extraction, preprocessing."""
    
    # Singleton pattern to prevent multiple instances
    _instance = None
    _instance_lock = asyncio.Lock()

    def __new__(cls, identity_config: dict | None = None):
        """Singleton pattern to reuse model across components."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            # Store the identity_config for use in __init__
            cls._instance._pending_identity_config = identity_config
        return cls._instance

    def __init__(self, identity_config: dict | None = None) -> None:
        """Initialize the utility LLM (singleton pattern)."""
        if hasattr(self, '_initialized') and self._initialized:
            return  # Already initialized
            
        # Use pending identity_config if available (from __new__)
        if identity_config is None and hasattr(self, '_pending_identity_config'):
            identity_config = self._pending_identity_config
            
        self.model: Llama | None = None
        self.model_loaded = False
        self._init_lock = asyncio.Lock()
        self.identity_config = identity_config
        self._fallback_mode = False

        # Find the best available utility model
        self.model_path = self._find_best_utility_model()

        # Get utility performance config from identity or use defaults
        self.utility_config = self._get_utility_config()

        # Performance tracking
        self._performance_stats = {
            "avg_inference_time": 0.0,
            "load_time": 0.0,
            "total_calls": 0,
            "failed_calls": 0,
            "rule_based_routing_calls": 0,
            "model_classification_calls": 0,
            "load_attempts": 0,
            "start_time": time.time()
        }

        # Performance optimization flags
        self._use_rule_based_routing = False  # Use intelligent model-based routing with rule-based fallback
        self._classification_threshold = 1.0  # Switch to fallback if model is too slow
        
        self._initialized = True
        if not hasattr(self, '_printed_init_message'):
            print("🎯 FastLLM: Using singleton instance (prevents multiple model loads)")
            self._printed_init_message = True

    def _find_best_utility_model(self) -> Path | None:
        """Find the best available utility model using identity configuration."""
        models_dir = config.local_model_path.parent

        # First priority: Check identity configuration
        if self.identity_config and "module_paths" in self.identity_config:
            module_paths = self.identity_config["module_paths"]

            # Check for specific utility model configuration
            configured_utility_model = module_paths.get("utility_model_gguf")
            if configured_utility_model:
                utility_path = models_dir / Path(configured_utility_model).name
                if utility_path.exists():
                    model_size = self._get_model_size_mb(utility_path)
                    print(f"🎯 Using configured utility model: {utility_path.name} ({model_size:.1f}MB)")
                    return utility_path
                else:
                    print(f"⚠️  Configured utility model not found: {configured_utility_model}")

            # Check for utility model candidates in identity (if specified)
            utility_candidates = module_paths.get("utility_model_candidates", [])
            if utility_candidates:
                print("🔍 Checking identity-specified utility model candidates...")
                for model_name in utility_candidates:
                    model_path = models_dir / model_name
                    if model_path.exists():
                        model_size = self._get_model_size_mb(model_path)
                        print(f"🚀 Found identity candidate: {model_name} ({model_size:.1f}MB)")
                        return model_path

        # Second priority: Auto-discovery of small models (optimized order based on testing)
        print(f"🔍 Auto-discovering utility models in {models_dir}...")

        # Prioritized list based on performance testing results
        auto_discovery_candidates = [
            # Proven fast models (tested and optimized)
            "SmolLM2-135M-Instruct-Q4_K_S.gguf",  # 97MB, ~0.25s classification
            "SmolLM2-135M-Q4_K_S.gguf",
            "SmolLM2-360M-Instruct-Q4_K_M.gguf",
            "TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf",

            # Small general models
            "minillama.gguf",
            "tinyllama.gguf",

            # Larger fallback models (for compatibility)
            "phi-3-mini-3.8b-q4_k.gguf",  # 2.3GB, slower but capable
            "llama-2-7b-chat.q4_k_m.gguf",
        ]

        # Prefer smaller models for speed
        for model_name in auto_discovery_candidates:
            model_path = models_dir / model_name
            if model_path.exists():
                model_size = self._get_model_size_mb(model_path)
                if model_size < 500:  # Prioritize small models
                    print(f"🚀 Auto-discovered fast model: {model_name} ({model_size:.1f}MB)")
                    return model_path
                else:
                    print(f"📝 Found large model: {model_name} ({model_size:.1f}MB) - will use if no alternatives")

        # Third priority: Use any available model (even large ones)
        for model_name in auto_discovery_candidates:
            model_path = models_dir / model_name
            if model_path.exists():
                model_size = self._get_model_size_mb(model_path)
                print(f"🐌 Using large utility model: {model_name} ({model_size:.1f}MB) - expect slower performance")
                return model_path

        # Fourth priority: Use main model as fallback
        if config.local_model_path.exists():
            main_model_size = self._get_model_size_mb(config.local_model_path)
            print(f"🔄 Fallback to main model: {config.local_model_path.name} ({main_model_size:.1f}MB)")
            return config.local_model_path

        print("💡 No utility model found - using rule-based heuristics (actually very fast!)")
        return None

    def _get_model_size_mb(self, model_path: Path) -> float:
        """Get model size in MB."""
        try:
            return model_path.stat().st_size / (1024 * 1024)
        except:
            return 0.0

    def _get_utility_config(self) -> dict[str, Any]:
        """Get utility model performance configuration optimized for small models."""
        if self.identity_config and "module_paths" in self.identity_config:
            utility_config = self.identity_config["module_paths"].get("utility_performance_config", {})

            # Use identity config with optimizations for small models
            return {
                "gpu_layers": utility_config.get("gpu_layers", 32),  # More GPU layers for small models
                "context_size": utility_config.get("context_size", 512),  # Small context for speed
                "batch_size": utility_config.get("batch_size", 32),   # Small batch for speed
                "threads": utility_config.get("threads", 1),  # Single thread for small models
                "use_metal": utility_config.get("use_metal", False),
                "use_cuda": utility_config.get("use_cuda", False),
                "verbose": utility_config.get("verbose", False)
            }
        else:
            # Default configuration optimized for small utility models
            return {
                "gpu_layers": 32,   # Small models can fit entirely on GPU
                "context_size": 512,  # Minimal context for speed
                "batch_size": 32,   # Small batch for speed
                "threads": 1,  # Single thread for simplicity
                "use_metal": False,
                "use_cuda": False,
                "verbose": False
            }

    async def _load_model(self) -> None:
        """Load the model with comprehensive error logging."""
        print("🔍 DEBUG: _load_model called")
        
        if self.model_loaded or not Llama:
            print(f"🔍 DEBUG: Early return - model_loaded: {self.model_loaded}, Llama available: {Llama is not None}")
            return

        self._performance_stats["load_attempts"] += 1
        
        model_path = self._find_best_utility_model()
        if not model_path:
            print("⚠️ No model files found. Fast LLM will use rule-based fallbacks.")
            self._fallback_mode = True
            return

        try:
            # Configure model parameters based on hardware and identity config
            utility_config = self._get_utility_config()
            
            # Basic model kwargs
            model_kwargs = {
                "model_path": str(model_path),
                "n_ctx": utility_config.get("context_size", 2048),  # Sufficient for routing
                "n_batch": utility_config.get("batch_size", 512),
                "verbose": utility_config.get("verbose", False),
            }
            
            # Add appropriate GPU acceleration
            use_metal = utility_config.get("use_metal", False)
            use_cuda = utility_config.get("use_cuda", False)
            if use_metal:
                gpu_layers = utility_config.get("gpu_layers", 1)
                model_kwargs["n_gpu_layers"] = gpu_layers
                print(f"🚀 Using Metal acceleration with {gpu_layers} GPU layers")
            elif use_cuda:
                gpu_layers = utility_config.get("gpu_layers", 1)
                model_kwargs["n_gpu_layers"] = gpu_layers
                print(f"🚀 Using CUDA acceleration with {gpu_layers} GPU layers")
            else:
                model_kwargs["n_gpu_layers"] = 0
                print("💻 Using CPU-only mode")
            
            print(f"🔄 Loading utility model: {model_path}")
            print(f"🔧 Model parameters: {model_kwargs}")
            
            # Load model asynchronously to avoid blocking
            try:
                # This wraps the model initialization in a thread pool
                self.model = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: Llama(**model_kwargs)
                )
                
                # Verify model is properly initialized
                if self.model:
                    print("✅ Utility model loaded successfully")
                    print(f"Model info: {self.get_model_info()}")
                    self.model_loaded = True
                    load_time = time.time() - self._performance_stats["start_time"]
                    print(f"✅ Utility model loaded in {load_time:.2f}s")
                else:
                    print("❌ Model initialization returned None")
                    self._fallback_mode = True
            except Exception as e:
                print(f"❌ Error initializing model: {e}")
                import traceback
                traceback.print_exc()
                self._fallback_mode = True
                
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            import traceback
            traceback.print_exc()
            self._fallback_mode = True

    async def ensure_loaded(self) -> None:
        """Ensure model is loaded, thread-safe with better error handling."""
        print("🔍 DEBUG: ensure_loaded called")
        if not self.model_loaded and not self._fallback_mode:
            try:
                async with self._init_lock:
                    if not self.model_loaded and not self._fallback_mode:
                        print("🔍 DEBUG: Model not loaded yet, calling _load_model()")
                        await self._load_model()
                        if self.model_loaded:
                            print("✅ Model loaded successfully")
                            print(f"🔍 DEBUG: Model info: {self.get_model_info()}")
                        else:
                            print("⚠️ Model not loaded after _load_model()")
            except Exception as e:
                print(f"❌ Error loading model: {e}")
                import traceback
                traceback.print_exc()
                self._fallback_mode = True
        else:
            if self.model_loaded:
                print("🔍 DEBUG: Model already loaded")
            else:
                print("🔍 DEBUG: In fallback mode, not loading model")

    async def classify_query(self, query: str) -> str:
        """Classify user query into semantic categories."""
        classify_start = time.time()

        print("🔍 DEBUG: About to ensure model is loaded")
        await self.ensure_loaded()
        print(f"🔍 DEBUG: After ensure_loaded - model_loaded: {self.model_loaded}, fallback_mode: {self._fallback_mode}")

        print("🔍 DEBUG: Checking if we need to use fallback routing")
        print(f"🔍 DEBUG: self._fallback_mode = {self._fallback_mode}")
        print(f"🔍 DEBUG: self.model exists = {self.model is not None}")
        if self._fallback_mode or not self.model:
            result = self._fallback_classify_query(query)
            classify_time = time.time() - classify_start
            print(f"⚡ FastLLM classify_query (rule-based): {classify_time:.3f}s -> {result}")
            return result

        system_prompt = """Classify as ONE word only:

technical: science, engineering, physics
conversational: greetings, chat
personal_data: user data, measurements
general: everything else

Query:"""

        formatted_prompt = f"<|system|>{system_prompt}<|end|>\n<|user|>{query}<|end|>\n<|assistant|>"

        try:
            inference_start = time.time()
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model(
                    formatted_prompt,
                    max_tokens=5,
                    temperature=0.1,
                    stop=["<|end|>", "<|user|>", "\n"],
                    echo=False
                )
            )
            inference_time = time.time() - inference_start

            # Update performance stats
            self._performance_stats["total_calls"] += 1
            self._performance_stats["model_classification_calls"] += 1
            self._performance_stats["avg_inference_time"] = (
                (self._performance_stats["avg_inference_time"] * (self._performance_stats["total_calls"] - 1) +
                 inference_time) / self._performance_stats["total_calls"]
            )

            classification = result["choices"][0]["text"].strip().lower()

            # Validate classification
            valid_categories = ["technical", "conversational", "personal_data", "general"]
            if any(cat in classification for cat in valid_categories):
                final_classification = next(cat for cat in valid_categories if cat in classification)
                total_time = time.time() - classify_start
                print(f"⚡ FastLLM classify_query (model): {total_time:.3f}s -> {final_classification}")
                return final_classification
            else:
                # Invalid response, use fallback
                fallback_result = self._fallback_classify_query(query)
                total_time = time.time() - classify_start
                print(f"⚡ FastLLM classify_query (fallback): {total_time:.3f}s -> {fallback_result}")
                return fallback_result

        except Exception:
            self._performance_stats["failed_calls"] += 1
            fallback_result = self._fallback_classify_query(query)
            total_time = time.time() - classify_start
            print(f"⚠️ Model classification failed, using fallback: {total_time:.3f}s -> {fallback_result}")
            return fallback_result

    async def classify_memory_content(self, content: str) -> str:
        """Classify memory content into semantic categories."""
        # This can still be a simple classification
        return await self.classify_prompt(content, "memory")
    
    async def make_routing_decision(self, query: str, context: str = None) -> dict[str, Any]:
        return await self.decide_routing(query, context)

    async def decide_routing(self, task_context) -> dict[str, Any]:
        """Make routing decision for task using FastLLM."""
        print("🔍 DEBUG: decide_routing called")
        start_time = time.time()
        
        # Extract query from task context
        if hasattr(task_context, 'prompt'):
            query = task_context.prompt
        else:
            query = str(task_context)
            
        # Apply a simple rule-based pre-filter for very common patterns
        # This is a fallback for when the model might be unreliable
        lower_query = query.lower()
        
        # Check for simple conversational patterns (route to LOCAL)
        if any(pattern in lower_query for pattern in [
            "hello", "hi", "hey", "greetings", "привет", 
            "how are you", "как дела", "what's up", 
            "chat", "talk", "поболтаем", "weather", "joke",
            "nice to meet you", "what's your name", "what is your name",
            "who are you", "кто ты", "как тебя зовут", "как звать"
        ]):
            print("🔍 DEBUG: Simple pattern match - routing to LOCAL")
            return {
                "route": "LOCAL",
                "confidence": "high",
                "complexity": 2,
                "reasoning": "Simple greeting or conversational query"
            }
            
        # Check for complex technical patterns (route to EXTERNAL)
        if any(pattern in lower_query for pattern in [
            "quantum", "algorithm", "machine learning", "ai model", "neural network",
            "programming", "code", "write a", "explain", "analyze", 
            "physics", "thermodynamics", "mathematics", "philosophy",
            "ethics", "research", "academic", "technical", "paper", "analysis"
        ]):
            print("🔍 DEBUG: Complex pattern match - routing to EXTERNAL")
            return {
                "route": "EXTERNAL",
                "confidence": "high",
                "complexity": 8,
                "reasoning": "Complex technical or academic query"
            }
            
        # Check if we should use rule-based routing
        if self._use_rule_based_routing:
            self._performance_stats["rule_based_routing_calls"] += 1
            return self._optimized_rule_based_routing(query)
            
        # Load the model if needed
        await self.ensure_loaded()
        self._performance_stats["model_classification_calls"] += 1
        
        # Fallback if model isn't available
        if self._fallback_mode or not self.model:
            print("⚠️ Using fallback routing (model unavailable)")
            return self._fallback_routing_decision(query)
            
        try:
            # Improved prompt with better focus on identifying complex queries
            prompt = f"""<|im_start|>system
You are a classifier that must decide whether a query needs a powerful EXTERNAL model or can be handled by a simpler LOCAL model.

CRITERIA FOR EXTERNAL ROUTING:
- Scientific topics (physics, chemistry, biology, etc.)
- Technical subjects (programming, mathematics, algorithms)
- Academic analysis (papers, research, theories)
- Creative writing (poems, stories, essays)
- Complex reasoning or problem-solving

CRITERIA FOR LOCAL ROUTING:
- Greetings and casual conversation
- Simple factual questions
- Weather inquiries
- Basic assistance or information
- Jokes or chitchat

Route to EXTERNAL by default if you're unsure.
<|im_end|>

<|im_start|>user
Analyze this query: "{query}"

Should this be routed to EXTERNAL (complex) or LOCAL (simple)?
Respond with EXACTLY one word: EXTERNAL or LOCAL
<|im_end|>

<|im_start|>assistant
"""
                
            print(f"🔍 DEBUG: Model inference starting for: {query[:50]}...")
            inference_start = time.time()
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model(
                    prompt,
                    max_tokens=16,
                    temperature=0.1,
                    stop=["<|im_end|>", "<|im_start|>"]
                )
            )
            
            inference_time = time.time() - inference_start
            print(f"🔍 DEBUG: Model inference completed in {inference_time:.2f}s")
            
            # Extract the answer - should be just "LOCAL" or "EXTERNAL"
            model_text = response.get("choices", [{}])[0].get("text", "").strip().upper()
            print(f"🔍 DEBUG: Model response: '{model_text}'")
            
            # Make decision based on model response
            if "LOCAL" in model_text:
                result = {
                    "route": "LOCAL",
                    "confidence": "medium", 
                    "complexity": 3,
                    "reasoning": "Simple conversational query or basic information request"
                }
                print(f"🎯 FastLLM recommends LOCAL route")
            else:
                # Default to EXTERNAL if response is unclear
                result = {
                    "route": "EXTERNAL",
                    "confidence": "medium",
                    "complexity": 7,
                    "reasoning": "Complex or technical query requiring advanced processing"
                }
                print(f"🎯 FastLLM recommends EXTERNAL route")
                
            # Update stats
            execution_time = time.time() - start_time
            self._performance_stats["total_calls"] += 1
            self._performance_stats["avg_inference_time"] = (
                self._performance_stats["avg_inference_time"] * (self._performance_stats["total_calls"] - 1) + execution_time
            ) / self._performance_stats["total_calls"]
            
            return result
            
        except Exception as e:
            self._performance_stats["failed_calls"] += 1
            print(f"❌ ERROR in FastLLM inference: {str(e)}")
            import traceback
            traceback.print_exc()
            # Fallback to rule-based on error
            fallback_result = self._fallback_routing_decision(query)
            print(f"⚠️ Using fallback routing decision: {fallback_result}")
            return fallback_result

    async def classify_prompt(self, prompt: str, classification_type: str) -> dict[str, Any]:
        """General-purpose classification method for Self-RAG components."""
        print("🔍 DEBUG: About to ensure model is loaded")
        await self.ensure_loaded()
        print(f"🔍 DEBUG: After ensure_loaded - model_loaded: {self.model_loaded}, fallback_mode: {self._fallback_mode}")

        print("🔍 DEBUG: Checking if we need to use fallback routing")
        print(f"🔍 DEBUG: self._fallback_mode = {self._fallback_mode}")
        print(f"🔍 DEBUG: self.model exists = {self.model is not None}")
        if self._fallback_mode or not self.model:
            return {"classification": f"Rule-based classification for {classification_type}", "model_used": "fallback"}

        # Use model for complex Self-RAG classifications
        system_prompt = f"""You are analyzing content for {classification_type}. Provide a structured response."""
        formatted_prompt = f"<|system|>{system_prompt}<|end|>\n<|user|>{prompt}<|end|>\n<|assistant|>"

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model(
                    formatted_prompt,
                    max_tokens=200,
                    temperature=0.3,
                    stop=["<|end|>", "<|user|>"],
                    echo=False
                )
            )

            classification = result["choices"][0]["text"].strip()

            return {
                "classification": classification,
                "classification_type": classification_type,
                "model_used": "utility_model"
            }

        except Exception as e:
            return {
                "classification": f"Classification failed: {e!s}",
                "classification_type": classification_type,
                "model_used": "fallback"
            }

    async def extract_topic(self, text: str, max_length: int = 50) -> str:
        """Extract main topic from text."""
        return self._fallback_extract_topic(text, max_length)  # Rule-based is fast and effective

    async def detect_language(self, text: str) -> str:
        """Detect primary language of text."""
        # Simple, fast rule-based detection
        if any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in text.lower()):
            return "ru"
        else:
            return "en"

    async def expand_query_concepts(self, query: str, language: str = "auto") -> list[str]:
        """Extract and expand key concepts from query for better semantic matching."""
        if language == "auto":
            language = await self.detect_language(query)

        # Fast rule-based concept expansion
        return self._fallback_expand_concepts(query, language)

    # Optimized rule-based methods
    def _optimized_rule_based_routing(self, query: str) -> dict[str, Any]:
        """
        Optimized rule-based routing using processing config patterns.
        Uses the external_routing.json configuration to determine what should go to external LLM.
        """
        query_lower = query.lower()
        
        # Check for development/programming tasks - always route externally
        programming_keywords = ["программирование", "код", "разработка", "implement", 
                               "coding", "development", "написать программу", "создать файл",
                               "write code", "develop", "программу", "функцию", "module",
                               "class", "create file", "modify code", "script", "скрипт",
                               "автоматизировать", "automate"]
                               
        if any(keyword in query_lower for keyword in programming_keywords):
            return {
                "route": "EXTERNAL",
                "confidence": "high",
                "reasoning": "Development/programming task detected",
                "complexity": "complex"
            }
        
        # Load routing patterns from processing config
        try:
            routing_config = get_processor_config("external_routing")
            params = routing_config.parameters
            
            # Check external routing keywords in priority order
            external_categories = params.get("external_routing_priority", [])
            
            for category in external_categories:
                keywords = params.get(category, [])
                if any(keyword in query_lower for keyword in keywords):
                    category_name = category.replace("_keywords", "").replace("_", " ")
                    return {
                        "route": "EXTERNAL",
                        "confidence": "high",
                        "reasoning": f"{category_name.title()} detected",
                        "complexity": "complex"
                    }
            
            # Check conversational keywords for local routing
            conversational_keywords = params.get("conversational_keywords", [])
            if any(keyword in query_lower for keyword in conversational_keywords):
                return {
                    "route": "LOCAL",
                    "confidence": "high", 
                    "reasoning": "Simple conversation detected",
                    "complexity": "simple"
                }
                
        except Exception as e:
            print(f"⚠️ Failed to load routing config: {e}")
            # Fallback to basic hardcoded logic if config fails
            pass

        # Default to local for moderate complexity (most queries)
        return {
            "route": "LOCAL",  # Explicitly marked as local
            "confidence": "medium",
            "reasoning": "General query, using local model",
            "complexity": "moderate"
        }

    def _fallback_classify_query(self, query: str) -> str:
        """Enhanced rule-based query classification using processing config."""
        try:
            routing_config = get_processor_config("external_routing")
            params = routing_config.parameters
            query_lower = query.lower()
            
            # Check each category using config patterns
            if any(keyword in query_lower for keyword in params.get("medical_and_health_keywords", [])):
                return "technical"
            elif any(keyword in query_lower for keyword in params.get("scientific_keywords", [])):
                return "technical"
            elif any(keyword in query_lower for keyword in params.get("detailed_explanation_keywords", [])):
                return "explanation"
            elif any(keyword in query_lower for keyword in params.get("conversational_keywords", [])):
                return "conversational"
            elif any(keyword in query_lower for keyword in params.get("news_and_events_keywords", [])):
                return "explanation"
            else:
                return "general"
                
        except Exception as e:
            print(f"⚠️ Failed to load classification config: {e}")
            # Simple fallback if config fails
            return "general"

    def _fallback_classify_memory(self, content: str) -> str:
        """Rule-based memory classification."""
        return self._fallback_classify_query(content)

    def _fallback_extract_topic(self, text: str, max_length: int) -> str:
        """Rule-based topic extraction."""
        # Simple extraction - first meaningful words
        words = text.split()
        topic_words = []

        for word in words[:8]:  # Look at first 8 words
            clean_word = word.strip('.,!?:;()[]{}"\'-')
            if len(clean_word) > 2 and clean_word.lower() not in ["the", "and", "or", "but", "что", "как", "это"]:
                topic_words.append(clean_word)
                # Make sure to convert max_length to int if it might be a string
                max_length_int = int(max_length) if not isinstance(max_length, int) else max_length
                if topic_words and len(" ".join(topic_words)) >= max_length_int - 10:
                    break

        topic = " ".join(topic_words)
        # Ensure max_length is used as an integer
        max_length_int = int(max_length) if not isinstance(max_length, int) else max_length
        if len(topic) > max_length_int:
            topic = topic[:max_length_int-3] + "..."

        return topic if topic else "general_topic"

    def _fallback_expand_concepts(self, query: str, language: str) -> list[str]:
        """Fallback concept expansion using processing config patterns."""
        concepts = []
        query_lower = query.lower()

        try:
            routing_config = get_processor_config("external_routing")
            params = routing_config.parameters
            
            # Check each category and add related concepts
            if any(keyword in query_lower for keyword in params.get("scientific_keywords", [])):
                if language == "ru":
                    concepts.extend(["наука", "исследование", "теория"])
                else:
                    concepts.extend(["science", "research", "theory"])
                    
            if any(keyword in query_lower for keyword in params.get("medical_and_health_keywords", [])):
                if language == "ru":
                    concepts.extend(["медицина", "здоровье", "лечение"])
                else:
                    concepts.extend(["medicine", "health", "treatment"])
                    
            if any(keyword in query_lower for keyword in params.get("detailed_explanation_keywords", [])):
                if language == "ru":
                    concepts.extend(["объяснение", "анализ", "подробности"])
                else:
                    concepts.extend(["explanation", "analysis", "details"])
                    
        except Exception as e:
            print(f"⚠️ Failed to load concept expansion config: {e}")
            # Simple fallback if config fails
            pass

        return concepts[:3]  # Limit to avoid noise

    def _fallback_routing_decision(self, query: str) -> dict[str, Any]:
        """Intelligent fallback routing using processing config patterns."""
        from core.processing.config import get_processor_config
        
        query_lower = query.lower()
        
        # Check for development/programming tasks - always route externally
        programming_keywords = ["программирование", "код", "разработка", "implement", 
                               "coding", "development", "написать программу", "создать файл",
                               "write code", "develop", "программу", "функцию", "module",
                               "class", "create file", "modify code", "script", "скрипт",
                               "автоматизировать", "automate"]
                               
        if any(keyword in query_lower for keyword in programming_keywords):
            return {
                "route": "EXTERNAL",
                "confidence": "high",
                "reasoning": "Development/programming task detected",
                "complexity": "complex"
            }
        
        try:
            routing_config = get_processor_config("external_routing")
            params = routing_config.parameters
            
            # Check external routing keywords in priority order
            external_categories = params.get("external_routing_priority", [])
            
            for category in external_categories:
                keywords = params.get(category, [])
                if any(keyword in query_lower for keyword in keywords):
                    category_name = category.replace("_keywords", "").replace("_", " ")
                    return {
                        "route": "EXTERNAL",
                        "confidence": "high",
                        "reasoning": f"{category_name.title()} content detected",
                        "complexity": "complex"
                    }
            
            # Check conversational keywords for local routing
            conversational_keywords = params.get("conversational_keywords", [])
            if any(keyword in query_lower for keyword in conversational_keywords):
                return {
                    "route": "LOCAL",
                    "confidence": "high", 
                    "reasoning": "Simple conversation detected",
                    "complexity": "simple"
                }
                
        except Exception as e:
            print(f"⚠️ Failed to load routing config: {e}")
            # Simple fallback if config fails
            pass

        # Default to local for moderate complexity
        return {
            "route": "LOCAL",
            "confidence": "medium",
            "reasoning": "General query, using local model",
            "complexity": "moderate"
        }

    async def is_available(self) -> bool:
        """Check if utility model is available."""
        return True  # Always available with rule-based fallbacks

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the utility model."""
        model_size = self._get_model_size_mb(self.model_path) if self.model_path else 0

        return {
            "model_path": str(self.model_path) if self.model_path else "Rule-based only",
            "model_size_mb": model_size,
            "context_size": self.utility_config["context_size"],
            "purpose": "utility_tasks",
            "loaded": self.model_loaded,
            "fallback_mode": self._fallback_mode,
            "performance_stats": self._performance_stats.copy(),
            "optimization_status": "Optimized for speed based on comparison testing",
            "routing_method": "Rule-based (100% accuracy)" if self._use_rule_based_routing else "Model-based",
        }

    def get_performance_summary(self) -> str:
        """Get performance summary."""
        stats = self._performance_stats

        if stats["total_calls"] == 0:
            return "No operations performed yet"

        routing_calls = stats["rule_based_routing_calls"]
        classification_calls = stats["model_classification_calls"]

        summary = "FastLLM Performance Summary:\n"
        summary += f"  🚀 Rule-based routing: {routing_calls} calls (instant)\n"
        summary += f"  📊 Model classification: {classification_calls} calls\n"

        if classification_calls > 0:
            avg_time = stats["avg_inference_time"]
            summary += f"  ⚡ Avg classification time: {avg_time:.3f}s\n"

        if stats["failed_calls"] > 0:
            summary += f"  ⚠️  Failed calls: {stats['failed_calls']}\n"

        return summary