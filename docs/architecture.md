# Prometheus Framework Architecture

## Overview

Prometheus is an entity-based AI framework designed around clean architectural principles:
1. **Entity-driven design** - Autonomous entities with their own identities and behaviors
2. **Clean separation of concerns** - Core framework + entity implementations
3. **Dual-model intelligence** - Fast utility model + powerful reasoning model
4. **Generic core components** - Reusable LocalLLM, router, and memory systems
5. **English-first system prompts** - Consistent internal language with multilingual responses

## System Architecture

```
                    ┌─────────────────┐
                    │   Prometheus    │
                    │   Framework     │
                    │     (Core)      │
                    └─────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   ┌─────────┐         ┌─────────┐         ┌─────────┐
   │Aletheia │         │ Agent B │         │ Agent C │
   │ Entity  │         │ Entity  │         │ Entity  │
   └─────────┘         └─────────┘         └─────────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Identity     │    │ Identity     │    │ Identity     │
│ Config       │    │ Config       │    │ Config       │
└──────────────┘    └──────────────┘    └──────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│                Core Framework                            │
├─────────────┬─────────────┬─────────────┬───────────────┤
│ BaseEntity  │ LocalLLM    │ LLMRouter   │ Memory        │
│ (Generic)   │ (Generic)   │ (Generic)   │ System        │
└─────────────┴─────────────┴─────────────┴───────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌─────────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐
│Processing   │ │ Utility   │ │ External  │ │ Vector      │
│ Pipeline    │ │ LLM       │ │ LLM       │ │ Store       │
│             │ │(phi-mini) │ │ Clients   │ │ (ChromaDB)  │
└─────────────┘ └───────────┘ └───────────┘ └─────────────┘
```

## Entity-Based Architecture

### Core Framework Components (Generic)

#### 1. BaseEntity
- **Purpose**: Abstract base class for all AI entities
- **Responsibilities**: 
  - Identity loading and management
  - Core functionality (think, autonomous_loop, get_status)
  - Framework integration (router, memory, context)
- **Entity contracts**: Entities override `_load_identity()` and specify `IDENTITY_PATH`

#### 2. LocalLLM (Generic)
- **Purpose**: Generic local language model wrapper
- **Clean design**: No entity-specific knowledge
- **System prompts**: Always in English from identity config
- **Response format**: Simple `ANSWER`, `CONFIDENCE`, `REASONING`
- **No routing logic**: Pure text generation

#### 3. LLMRouter (Generic)
- **Purpose**: Intelligent routing between local and external LLMs
- **Responsibilities**: Route decisions, cost optimization, performance tracking
- **Meta-cognitive**: Uses local LLM's confidence to make routing decisions
- **Generic design**: Works with any entity's identity configuration

#### 4. Memory System (Generic)
- **Vector Store**: ChromaDB-based semantic memory
- **User Profiles**: Personal data extraction and storage
- **Context Manager**: Conversation history and running summaries
- **Processing Pipeline**: Configurable text processing modules

### Entity Implementation (Specific)

#### Aletheia Entity
```python
class AletheiaEntity(BaseEntity):
    IDENTITY_PATH = Path(__file__).parent / "identity"
    
    def _load_identity(self) -> Dict[str, Any]:
        # Load aletheia-specific configuration
        # Merge with fallbacks
        # Return complete identity config
```

#### Entity Identity Configuration
```json
{
  "name": "Aletheia",
  "llm_instructions": "You are Aletheia, a female autonomous technical agent...",
  "personality": {...},
  "module_paths": {
    "local_model_gguf": "models/Phi-3-medium-4k-instruct-Q4_K_M.gguf",
    "utility_model_gguf": "models/phi-3-mini-3.8b-q4_k.gguf"
  },
  "translations": {
    "ru": { ... }
  }
}
```

## Core Principles

### 1. Clean Separation of Concerns
- **Core framework**: Generic, reusable components
- **Entity implementations**: Specific personalities and behaviors
- **No coupling**: Core components don't know about specific entities
- **Dependency injection**: Identity config passed to core components

### 2. English-First System Design
- **System prompts**: Always in English for consistency
- **Internal communication**: Framework operates in English
- **User responses**: Generated in user's preferred language
- **Translation layer**: Handled at entity level through identity config

### 3. Generic Component Design
- **LocalLLM**: Works with any identity configuration
- **Router**: Entity-agnostic routing decisions
- **Memory**: Generic storage and retrieval
- **Processing**: Configurable patterns and filters

## Dual-Model Architecture

### Utility Model (phi-3-mini)
- **Purpose**: Fast classifications and utility tasks
- **Performance**: 60-140ms response times
- **Operations**: Query categorization, memory filtering, concept expansion
- **Independence**: Zero context pollution from main model

### Main Model (phi-3-medium)
- **Purpose**: Complex reasoning and response generation
- **Performance**: 1-3s for thoughtful responses
- **Operations**: Natural conversation, problem solving, self-assessment
- **Context**: Enhanced with utility model insights

### Routing Strategy
1. **Query Analysis**: Utility model categorizes the request
2. **Memory Retrieval**: Semantic filtering and relevance scoring
3. **Self-Assessment**: Main model evaluates its competence
4. **Routing Decision**: Router chooses local vs external processing
5. **Response Generation**: Clean, professional output

## Data Processing Architecture

### Processing Pipeline (Configuration-Driven)
```
core/processing/
├── configs/
│   ├── contamination_filter.json
│   ├── complexity_detector.json
│   ├── user_data_extractor.json
│   ├── reference_detector.json
│   └── ... (other pattern configs)
├── pipeline.py
├── extractors.py
├── detectors.py
├── filters.py
└── cleaners.py
```

### Clean Response Pipeline
```
Raw Response → Contamination Filter → Field Removal → Context Fallback → Clean Output
  Structured     Remove Markers       Clean Fields    Topic Preserve    User Ready
```

## File Structure

```
prometheus/
├── core/                      # Generic framework components
│   ├── __init__.py
│   ├── base_entity.py         # Abstract base class
│   ├── config.py              # Global configuration
│   ├── llm/
│   │   ├── local_llm.py       # Generic local LLM wrapper
│   │   ├── utility_llm.py     # Fast utility model
│   │   ├── router.py          # Intelligent routing
│   │   └── external_llm.py    # External API clients
│   ├── memory/
│   │   ├── vector_store.py    # ChromaDB wrapper
│   │   ├── controller.py      # Memory management
│   │   ├── user_profile_store.py
│   │   └── summariser.py
│   ├── context/
│   │   └── context_manager.py # Conversation context
│   └── processing/            # Text processing modules
│       ├── configs/           # JSON pattern configurations
│       ├── pipeline.py
│       ├── extractors.py
│       ├── detectors.py
│       ├── filters.py
│       └── cleaners.py
├── entities/                  # Entity implementations
│   ├── __init__.py           # Entity registry
│   └── aletheia/             # Aletheia entity
│       ├── __init__.py       # AletheiaEntity class
│       └── identity/
│           └── identity.json # Aletheia configuration
├── prometheus.py             # CLI interface
├── tests/                    # Test suite
├── docs/                     # Documentation
└── models/                   # Model storage
    ├── Phi-3-medium-4k-instruct-Q4_K_M.gguf
    └── phi-3-mini-3.8b-q4_k.gguf
```

## Performance Characteristics

### Response Times
- **User Data Queries**: 0ms (instant from profile storage)
- **Utility Operations**: 60-140ms (classifications, filtering)
- **Local Processing**: 1-3s (conversation, reasoning)
- **External Consultation**: 3-8s (for complex/scientific queries)

### Resource Usage
- **Memory**: ~8GB RAM for dual-model operation
- **Storage**: ~10GB for models and data
- **GPU**: Metal acceleration on Apple Silicon
- **Cost**: 85% local processing, 15% external API calls

### Routing Efficiency
- **Local Processing**: 85% of interactions
- **External Consultation**: 15% for accuracy-critical tasks
- **Context Pollution**: 0% (independent utility operations)
- **Speed Improvement**: 20x faster classifications

## Multi-language Support

### Architecture
- **System Level**: English-only for consistency
- **Entity Level**: Multilingual identity configurations
- **Response Level**: User's preferred language
- **Translation**: Handled through entity identity config

### Example (Russian Support)
```json
{
  "llm_instructions": "You are Aletheia, a female autonomous technical agent. When responding in Russian, always use feminine language forms: готова (not готов), рада (not рад)...",
  "translations": {
    "ru": {
      "greeting_templates": {
        "casual": "Привет! Как дела?",
        "professional": "Здравствуйте! Я {name}, готова помочь."
      }
    }
  }
}
```

## Hardware Requirements

### Minimum
- **RAM**: 16GB
- **Storage**: 20GB free space
- **CPU**: Apple Silicon M1/M2/M3 or equivalent
- **GPU**: Metal acceleration support

### Recommended
- **RAM**: 32GB+ for optimal dual-model performance
- **Storage**: 50GB+ for extended memory and models
- **Network**: Stable internet for external LLM access 