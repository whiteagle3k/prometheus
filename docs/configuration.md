# Configuration Guide

## Environment Configuration

### Core Settings
```env
# Local Model Configuration
LOCAL_MODEL_PATH=./models/phi-3-medium-4k-instruct-q4_k_m.gguf
LOCAL_MODEL_CONTEXT_SIZE=8192
LOCAL_MODEL_GPU_LAYERS=40

# Routing Configuration
META_COGNITIVE_ROUTING=true
SCIENTIFIC_UNCERTAINTY_THRESHOLD=0.7
ROUTING_CONTEXT_WINDOW=2

# Memory Management
MAX_MEMORY_ENTRIES=1000
MEMORY_SUMMARIZATION_THRESHOLD=500
REFLECTION_ENABLED=true
USE_HIERARCHICAL_MEMORY=true

# User Data Management
USER_PROFILE_STORAGE=storage/user_profiles
USER_DATA_EXTRACTION_ENABLED=true
USER_DATA_RETENTION_DAYS=365

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
    "version": "0.4.0"
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
    "name_extraction": {
      "patterns": [
        "меня зовут\\s+(\\w+)",
        "my name is\\s+(\\w+)"
      ]
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

The processing system uses modular JSON configurations for all text processing components.

### User Data Extraction Configuration
```json
{
  "enabled": true,
  "parameters": {
    "physical_patterns": [
      {
        "pattern": "(?:я\\s+)?(?:вешу|весу|мой\\s+вес)\\s+(\\d+(?:[.,]\\d+)?)\\s*(?:кг|килограмм)",
        "key": "weight",
        "unit": "kg",
        "confidence": 0.95
      },
      {
        "pattern": "(?:при\\s+)?(?:росте|высота|рост)\\s+(\\d+(?:[.,]\\d+)?)\\s*(?:см|сантиметр)",
        "key": "height",
        "unit": "cm",
        "confidence": 0.95
      },
      {
        "pattern": "(?:процент\\s+)?(?:жира|жир)\\s+(\\d+(?:[.,]\\d+)?)\\s*(?:%|процент)?",
        "key": "body_fat_percentage",
        "unit": "%",
        "confidence": 0.9
      }
    ],
    "goal_patterns": [
      {
        "pattern": "(?:хочу|цель|планирую)\\s+(.+?)(?:\\.|!|$)",
        "key": "fitness_goal",
        "confidence": 0.8
      }
    ],
    "preference_patterns": [
      {
        "pattern": "(?:я\\s+)?(?:люблю|нравится|предпочитаю)\\s+(.+?)(?:\\.|,|и|$)",
        "key": "likes",
        "confidence": 0.7
      },
      {
        "pattern": "(?:я\\s+)?(?:не\\s+люблю|не\\s+нравится)\\s+(.+?)(?:\\.|,|и|$)",
        "key": "dislikes",
        "confidence": 0.7
      }
    ],
    "data_query_patterns": [
      "(?:напомни|расскажи|покажи)\\s+(?:мне\\s+)?(?:мои\\s+)?(?:данные|информацию|профиль)",
      "(?:remind|tell|show)\\s+(?:me\\s+)?(?:my\\s+)?(?:data|information|profile)"
    ]
  }
}
```

### Entity Extractor Configuration
```json
{
  "enabled": true,
  "parameters": {
    "scientific_terms": [
      "водяной пар", "water vapor", "динозавры", "dinosaurs",
      "эволюция", "evolution", "химия", "chemistry"
    ],
    "compound_terms": [
      "водяной пар", "water vapor", "body fat", "процент жира"
    ],
    "exclude_words": [
      "это", "то", "такое", "когда", "где", "что",
      "the", "that", "this", "when", "where", "what"
    ],
    "max_entities": 5,
    "min_word_length": 3
  }
}
```

### Name Extractor Configuration
```json
{
  "enabled": true,
  "parameters": {
    "name_patterns": [
      "меня зовут\\s+(\\w+)",
      "мое имя\\s+(\\w+)", 
      "я\\s+(\\w+)",
      "my name is\\s+(\\w+)",
      "i'?m\\s+(\\w+)",
      "call me\\s+(\\w+)"
    ],
    "exclude_words": [
      "вверх", "вниз", "up", "down", "what", "who", "где", "кто"
    ],
    "min_name_length": 2
  }
}
```

### Reference Detector Configuration
```json
{
  "enabled": true,
  "parameters": {
    "pronouns": {
      "ru": ["он", "она", "оно", "они", "его", "её", "их"],
      "en": ["it", "that", "this", "them", "those"]
    },
    "continuation_phrases": {
      "ru": ["а что", "а если", "расскажи подробнее", "что дальше"],
      "en": ["tell me more", "what about", "explain further", "what's next"]
    },
    "implicit_patterns": [
      "\\bа\\s+если\\b",
      "\\bа\\s+что\\b",
      "^\\s*(а|но|и)\\s+"
    ],
    "confidence_threshold": 0.7
  }
}
```

## User Profile Management

### Profile Storage Configuration
User profiles are stored in JSON format in the configured directory:

```json
{
  "physical": {
    "weight": {
      "value": "80",
      "timestamp": "2025-06-02T12:00:00",
      "confidence": 0.95,
      "source": "Session context..."
    },
    "height": {
      "value": "190",
      "timestamp": "2025-06-02T12:00:00",
      "confidence": 0.95,
      "source": "Session context..."
    }
  },
  "personal": {
    "name": {
      "value": "Игорь",
      "timestamp": "2025-06-02T12:00:00",
      "confidence": 0.9,
      "source": "Name extraction..."
    }
  },
  "goals": {
    "fitness_goal": [
      {
        "value": "похудеть на 5кг",
        "timestamp": "2025-06-02T12:00:00",
        "confidence": 0.8,
        "source": "User stated goal..."
      }
    ]
  },
  "preferences": {
    "likes": [],
    "dislikes": []
  },
  "feedback": [],
  "last_updated": "2025-06-02T12:00:00"
}
```

### Profile Privacy Settings
```env
# User data privacy controls
USER_PROFILE_ENCRYPTION=false  # Enable for production
USER_PROFILE_EXPORT_ENABLED=true
USER_PROFILE_DELETE_ENABLED=true
USER_DATA_EXTERNAL_SHARING=false  # Never share with external LLMs
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
- **Model Storage**: ~2.3GB for Phi-3 Medium Q4_K_M

### Performance Tuning
```env
# Adjust based on available memory
LOCAL_MODEL_GPU_LAYERS=40  # All layers for M3 Max
LOCAL_MODEL_CONTEXT_SIZE=8192  # Increased for better context
LOCAL_MODEL_THREADS=8  # Adjust for CPU cores
LOCAL_MODEL_BATCH_SIZE=512  # Optimize for throughput
```

## Memory System Configuration

### Hierarchical Memory Settings
```env
# Memory tier configuration
HIERARCHICAL_MEMORY_ENABLED=true
RAW_MEMORY_LIMIT=200
SUMMARY_MEMORY_LIMIT=100
KEY_FACTS_LIMIT=50

# Automatic archiving
MEMORY_ARCHIVE_ENABLED=true
MEMORY_ARCHIVE_AGE_DAYS=30
MEMORY_COMPRESSION_RATIO=0.5
```

### Vector Database Settings
```env
# ChromaDB configuration
CHROMA_PERSIST_DIRECTORY=./storage/chroma
CHROMA_COLLECTION_NAME=aletheia_memory
CHROMA_ANONYMIZED_TELEMETRY=false
CHROMA_ALLOW_RESET=true
```

## External API Configuration

### Anthropic Claude (Recommended)
```env
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_MAX_TOKENS=1000
ANTHROPIC_TEMPERATURE=0.7
```

### OpenAI GPT-4 (Alternative)
```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.7
```

### Cost Management
```env
# External routing controls
EXTERNAL_THRESHOLD_TOKENS=1024
COST_OPTIMIZATION=true
MAX_COST_PER_QUERY=0.05
PREFER_LOCAL=true
```

## Advanced Configuration

### Custom Pattern Creation
1. Create new JSON config file in `aletheia/processing/configs/`
2. Define patterns with confidence scores
3. Register in processing pipeline
4. Test with validation tools

### Multi-Language Pattern Support
```json
{
  "physical_patterns": [
    {
      "pattern": "(?:I\\s+)?(?:weigh|weight\\s+is)\\s+(\\d+(?:[.,]\\d+)?)\\s*(?:kg|lbs)",
      "key": "weight",
      "unit": "extracted",
      "confidence": 0.95,
      "language": "en"
    },
    {
      "pattern": "(?:я\\s+)?(?:вешу|весу)\\s+(\\d+(?:[.,]\\d+)?)\\s*(?:кг|килограмм)",
      "key": "weight", 
      "unit": "kg",
      "confidence": 0.95,
      "language": "ru"
    }
  ]
}
```

### Custom Agent Creation
1. Copy `aletheia/identity/identity.json` to new file
2. Modify personality traits and language instructions
3. Update processing configurations as needed
4. Configure user data extraction patterns
5. Test with framework validation tools

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
from aletheia.processing.config import get_processor_config
config = get_processor_config('user_data_extractor')
print('User data config valid:', config is not None)
"

# Test user data extraction
poetry run python -c "
from aletheia.processing.extractors import UserDataExtractor
extractor = UserDataExtractor()
test_input = 'меня зовут Тест, я вешу 70кг'
data_points = extractor.extract(test_input)
print(f'Extracted {len(data_points)} data points')
"
```

## Configuration File Locations

```
aletheia/
├── identity/
│   └── identity.json              # Agent personality and behavior
├── processing/
│   └── configs/
│       ├── user_data_extractor.json    # Personal data patterns
│       ├── entity_extractor.json       # Topic extraction
│       ├── name_extractor.json         # Name detection
│       ├── reference_detector.json     # Context references  
│       ├── complexity_detector.json    # Task complexity
│       ├── contamination_filter.json   # Content filtering
│       ├── duplication_filter.json     # Duplicate detection
│       └── factual_validator.json      # Response validation
└── config.py                     # Core system configuration
```

## New in v0.4.0

### User Data Intelligence
- **Automatic extraction** from natural conversation
- **Instant queries** with zero-latency profile access
- **Privacy-first** local storage design
- **Configurable patterns** for different data types

### Enhanced Processing Pipeline
- **Modular extractors** with JSON configuration
- **Multi-language support** for pattern matching
- **Confidence scoring** for data quality assessment
- **Extensible architecture** for custom data types 