# Configuration Guide

## Environment Configuration

### Core Settings
```env
# Local Model Configuration
LOCAL_MODEL_PATH=./models/phi-3-mini-3.8b-q4_k.gguf
LOCAL_MODEL_CONTEXT_SIZE=4096
LOCAL_MODEL_GPU_LAYERS=32

# Routing Configuration
META_COGNITIVE_ROUTING=true
SCIENTIFIC_UNCERTAINTY_THRESHOLD=0.7
ROUTING_CONTEXT_WINDOW=2

# Memory Management
MAX_MEMORY_ENTRIES=1000
MEMORY_SUMMARIZATION_THRESHOLD=500
REFLECTION_ENABLED=true

# External API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Logging
LOG_LEVEL=INFO
```

## Identity Configuration

The identity system uses JSON-based configuration for agent personalities.

### Basic Identity Structure
```json
{
  "meta": {
    "version": "0.3.0"
  },
  "name": "Aletheia",
  "primary_language": "en",
  "identity": {
    "summary": "Female autonomous research agent",
    "personality": [
      "Presents as a thoughtful female AI",
      "Technically precise and concise",
      "Uses appropriate feminine language forms"
    ]
  },
  "translations": {
    "ru": {
      "identity": {
        "summary": "Женский автономный исследователь-агент",
        "personality": ["Позиционирует себя как женский ИИ"]
      },
      "llm_instructions": "Ты — Алетейя, женский автономный агент..."
    }
  }
}
```

### Conversation Management
```json
{
  "conversation_management": {
    "context_window_size": 3,
    "reference_detection": {
      "enabled": true,
      "pronouns": ["it", "that", "this", "это", "то", "такое"],
      "continuation_phrases": ["tell me more", "расскажи подробнее"]
    },
    "context_questions": ["как меня зовут", "what's my name"]
  }
}
```

### Routing Configuration
```json
{
  "routing_configuration": {
    "planning_indicators": ["step by step", "пошагово"],
    "simple_conversation": ["привет", "hello", "как дела"]
  }
}
```

### Validation Patterns
```json
{
  "validation_patterns": {
    "water_vapor_confusion": {
      "question_terms": ["водяной пар", "water vapor"],
      "error_terms": ["водород", "hydrogen"]
    },
    "contradiction_pairs": [
      [["газ", "gas"], ["твердый", "solid"]]
    ]
  }
}
```

## Processing System Configuration

The processing system uses JSON configurations for all text processing components.

### Example: Entity Extractor Configuration
```json
{
  "scientific_terms": [
    "водяной пар", "water vapor", "динозавры", "dinosaurs",
    "эволюция", "evolution", "химия", "chemistry"
  ],
  "compound_terms": {
    "водяной пар": ["водяной", "пар"],
    "water vapor": ["water", "vapor"]
  },
  "exclude_words": [
    "это", "то", "такое", "когда", "где", "что"
  ]
}
```

### Example: Reference Detector Configuration
```json
{
  "pronouns": {
    "ru": ["он", "она", "оно", "они", "его", "её", "их"],
    "en": ["it", "that", "this", "them", "those"]
  },
  "continuation_phrases": {
    "ru": ["а что", "а если", "расскажи подробнее"],
    "en": ["tell me more", "what about", "explain further"]
  },
  "implicit_patterns": [
    "\\bа\\s+если\\b",
    "\\bа\\s+что\\b",
    "^\\s*(а|но|и)\\s+"
  ]
}
```

## Hardware Optimization

### Apple Silicon (M1/M2/M3)
```bash
# Enable Metal acceleration
CMAKE_ARGS="-DLLAMA_METAL=on" poetry install

# Verify Metal support
poetry run python -c "
from aletheia.llm.local_llm import LocalLLM
import asyncio
llm = LocalLLM()
print(asyncio.run(llm.get_model_info()))
"
```

### Memory Configuration
- **16GB RAM**: Basic operation with reduced context
- **32GB+ RAM**: Optimal performance with full context
- **Model Storage**: ~2.3GB for Phi-3 Mini Q4_K

### Performance Tuning
```env
# Adjust based on available memory
LOCAL_MODEL_GPU_LAYERS=32  # All layers for M3 Max
LOCAL_MODEL_CONTEXT_SIZE=4096  # Reduce if memory limited
LOCAL_MODEL_THREADS=8  # Adjust for CPU cores
```

## External API Configuration

### Anthropic Claude (Recommended)
```env
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-3-sonnet-20240229
ANTHROPIC_MAX_TOKENS=1024
```

### OpenAI GPT-4 (Alternative)
```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_MAX_TOKENS=1024
```

### Cost Management
- **External routing threshold**: Adjust confidence scoring
- **Token limits**: Set max_tokens per request
- **Request frequency**: Configure rate limiting

## Advanced Configuration

### Custom Agent Creation
1. Copy `aletheia/identity/identity.json` to new file
2. Modify personality traits and language instructions
3. Update processing configurations as needed
4. Test with framework validation tools

### Multi-Language Support
- Add translation entries in identity configuration
- Configure language-specific processing patterns
- Ensure proper grammatical forms for target language

### Memory Management
```env
# Automatic cleanup settings
MAX_MEMORY_ENTRIES=1000
MEMORY_CLEANUP_THRESHOLD=0.8
MEMORY_COMPRESSION_RATIO=0.5

# Vector database settings
CHROMA_PERSIST_DIRECTORY=./storage/chroma
CHROMA_COLLECTION_NAME=aletheia_memory
```

## Configuration Validation

The framework includes built-in validation for all configuration files:

```bash
# Validate identity configuration
poetry run python -c "
from aletheia.identity.validator import validate_identity
from aletheia.identity.loader import load_identity_config
config = load_identity_config()
print('Identity valid:', validate_identity(config))
"

# Validate processing configurations
poetry run python -c "
from aletheia.processing.config import validate_config
print('Processing configs valid:', validate_config())
"
``` 