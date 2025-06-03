# Prometheus Framework Architecture

## Overview

Prometheus is designed around four core principles:
1. **Identity-driven configuration** - Agent personalities defined in JSON
2. **Dual-model intelligence** - Fast utility model + powerful reasoning model
3. **Persistent conversational memory** - RAG-powered context with semantic filtering
4. **Clean professional output** - Robust parsing without technical contamination

## System Architecture

```
                    ┌─────────────────┐
                    │   Prometheus    │
                    │   Framework     │
                    └─────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   ┌─────────┐         ┌─────────┐         ┌─────────┐
   │Aletheia │         │ Agent B │         │ Agent C │
   │ (Active)│         │(Future) │         │(Future) │
   └─────────┘         └─────────┘         └─────────┘
        │
        ▼
┌──────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input     │───▶│   Orchestrator   │───▶│   Response      │
└──────────────────┘    └──────────────────┘    └─────────────────┘
                               │
                               ▼
                     ┌──────────────────┐
                     │ Identity System  │
                     │ (JSON Config)    │
                     └──────────────────┘
                               │
                     ┌─────────┼─────────┐
                     ▼         ▼         ▼
             ┌──────────┐ ┌────────┐ ┌──────────┐
             │Processing│ │ Memory │ │LLM Router│
             │ Pipeline │ │ System │ │ (Smart)  │
             └──────────┘ └────────┘ └──────────┘
                   │         │            │
                   ▼         ▼            ▼
             ┌──────────┐ ┌────────┐ ┌──────────────┐
             │Config-   │ │ User   │ │ Utility LLM  │
             │Driven    │ │Profile │ │(phi-3-mini)  │
             │Patterns  │ │Store   │ │Classifications│
             └──────────┘ └────────┘ └──────────────┘
                             │            │
                             ▼            ▼
                     ┌────────────┐ ┌──────────┐
                     │Vector Store│ │ Local    │
                     │(ChromaDB)  │ │ LLM      │
                     └────────────┘ │(Phi-3M)  │
                             │      └──────────┘
                             ▼            │
                     ┌──────────────────┐ ▼
                     │   Reflection     │ ┌──────────┐
                     │    Engine        │ │External  │
                     └──────────────────┘ │LLM       │
                                          └──────────┘
```

## Core Components

### 1. Dual-Model Architecture ✨
- **Utility Model (phi-3-mini)**: Fast classification and utility tasks (60-140ms)
- **Main Model (phi-3-medium)**: Complex reasoning and response generation
- **Zero Context Pollution**: Utility model operates independently
- **Performance Boost**: 20x faster classifications, optimal resource usage
- **Configuration**: Both models managed through `identity.json`

### 2. Identity Management System
- **JSON-Based Configuration**: Complete agent identity in `aletheia/identity/identity.json`
- **Model Path Management**: Unified configuration for both models
- **English-Primary Design**: Core personality in English for optimal model performance
- **Translation Layer**: Seamless multilingual interactions
- **Template System**: Easy creation of new agent personalities

### 3. Enhanced Parsing & Output System ✨
- **Clean Response Output**: Eliminated field contamination (CONFIDENCE, REASONING, etc.)
- **Professional Responses**: No technical markers in user-facing text
- **Robust Extraction**: Multiple parsing strategies with contextual fallbacks
- **Topic Preservation**: Maintains conversation continuity and context flow
- **Contextual Fallbacks**: Intelligent error handling without topic loss

### 4. Intelligent Hybrid Routing
- **Meta-Cognitive Assessment**: Local LLM decides when external help is needed
- **Self-Assessment Validation**: Utility model assists in routing decisions
- **Cost Optimization**: 85% local processing, 15% external consultation
- **Scientific Accuracy**: Prevents misinformation through smart routing
- **Enhanced Debug Output**: Comprehensive visibility into routing decisions

### 5. Advanced Memory System
- **Semantic Filtering**: Utility model provides fast query/memory categorization
- **Vector-Based Retrieval**: RAG-powered memory with intelligent relevance scoring
- **Category Matching**: Technical queries get technical memories, conversational get conversational
- **Hierarchical Storage**: Automatic tiering (raw → summary → key facts)
- **Context Continuity**: Maintains topic threads and reference resolution
- **Learning Integration**: Stores successful interaction patterns with source attribution

### 6. User Data Intelligence System
- **Automatic Extraction**: Pattern-based detection of personal information
- **Real-time Storage**: Instant saving to user profiles
- **Zero-latency Queries**: Direct profile access without LLM calls
- **Personalized Context**: User data integration into conversations
- **Privacy-first Design**: Local storage with encryption support

### 7. Comprehensive Debugging System ✨
- **Utility Model Visibility**: Debug output for all utility model operations
- **Performance Monitoring**: Speed tracking for classifications and memory operations
- **Route Tracking**: Clear visibility into local vs external routing decisions
- **Memory Analytics**: Detailed memory filtering and categorization insights
- **Error Diagnostics**: Enhanced error handling with contextual information

## Agent Orchestrator Philosophy

### The "Dual-Brain Smart Conductor" Approach

**Traditional AI**: Single model tries to do everything
- Context pollution from utility tasks
- Slow operations for simple classifications
- Risk of confident misinformation
- Limited adaptability

**Prometheus Dual-Model Approach**: Specialized models for specialized tasks
- **Utility Brain**: Fast phi-3-mini for classifications (60-140ms)
- **Reasoning Brain**: Powerful phi-3-medium for complex thoughts
- **Smart Orchestration**: Knows when to ask external experts
- **Memory Intelligence**: Semantic filtering and categorization
- **Clean Output**: Professional responses without technical contamination
- **Cost-Effective**: Optimal resource usage with intelligent routing

### Routing Strategy

1. **User Data Check**: First check if it's a data query (0.00s response)
2. **Query Classification**: Utility model categorizes query type (60ms)
3. **Memory Filtering**: Semantic categorization and relevance scoring (140ms)
4. **Self-Assessment**: Local LLM evaluates its competence
5. **Profile Integration**: Include user data in context when relevant
6. **Confidence Scoring**: Determines routing based on uncertainty
7. **Scientific Detection**: Auto-routes factual/scientific questions
8. **Context Awareness**: Considers conversation history and user profile
9. **Clean Response**: Robust parsing removes technical contamination

## Dual-Model Performance Architecture

### Utility Model Operations (phi-3-mini)
```
Query → Utility Model → Classification/Filtering → Main Model Context
 60ms      140ms           Fast Results              Clean Input
```

**Utility Tasks:**
- Query categorization (conversational, technical, explanation)
- Memory content classification
- Semantic relevance scoring
- Topic extraction
- Query concept expansion

### Main Model Operations (phi-3-medium)
```
Enhanced Context → Main Model → Structured Response → Clean Output
  Rich Input        1-3s         Internal Fields      User Response
```

**Reasoning Tasks:**
- Natural language conversation
- Complex question answering
- Context understanding
- Self-assessment for routing
- Response generation

## Data Processing Architecture

### Enhanced Memory Pipeline

```
Query → Utility Classification → Semantic Filtering → Relevance Scoring → Context
 60ms        Technical/Conv.        Category Match         Boost/Penalty    Enhanced
```

### Clean Response Pipeline

```
Raw Response → Contamination Filter → Field Removal → Context Fallback → Clean Output
Structured      Remove Markers        Clean Fields     Topic Preserve    User Ready
```

### Configuration Structure

```
aletheia/
├── identity/
│   └── identity.json           # Dual-model configuration
├── processing/configs/
│   ├── user_data_extractor.json    # Personal data patterns
│   ├── entity_extractor.json       # Topic/entity extraction  
│   ├── name_extractor.json         # User name detection
│   ├── reference_detector.json     # Context references
│   ├── complexity_detector.json    # Task complexity assessment
│   └── factual_validator.json      # Response validation
└── llm/
    ├── utility_llm.py          # Fast classification model
    ├── local_llm.py            # Main reasoning model
    └── router.py               # Intelligent routing
```

## File Structure

```
prometheus/
├── aletheia/                    # Main agent implementation
│   ├── identity/               # Identity management system
│   │   ├── identity.json       # Agent personality + model configuration
│   │   ├── loader.py          # Configuration loading
│   │   └── validator.py       # Schema validation
│   ├── processing/            # Modular text processing system
│   │   ├── configs/           # JSON pattern configurations
│   │   ├── extractors.py      # Data extraction engines
│   │   ├── pipeline.py        # Processing pipeline
│   │   └── *.py              # Processors (filters, detectors, etc.)
│   ├── memory/                # Memory and persistence systems
│   │   ├── vector_store.py    # ChromaDB wrapper
│   │   ├── hierarchical_store.py # Advanced memory management
│   │   ├── user_profile_store.py # User data storage
│   │   └── summariser.py      # Memory compression
│   ├── llm/                   # Language model management
│   │   ├── router.py          # Intelligent routing logic
│   │   ├── local_llm.py       # Main model wrapper (phi-3-medium)
│   │   ├── utility_llm.py     # Fast utility model (phi-3-mini)
│   │   └── external_llm.py    # External API clients
│   └── agent/                 # Agent behavior
│       ├── orchestrator.py    # Main orchestrator
│       ├── context_manager.py # Conversation context
│       ├── planner.py         # Task planning
│       └── reflexion.py       # Self-reflection
├── tests/                     # Comprehensive test suite
├── scripts/                   # Setup and utility scripts
├── docs/                      # Documentation
└── models/                    # Dual-model storage
    ├── Phi-3-medium-4k-instruct-Q4_K_M.gguf    # Main reasoning model
    └── phi-3-mini-3.8b-q4_k.gguf               # Utility classification model
```

## Performance Characteristics

### Dual-Model Performance
- **Utility Operations**: 60-140ms (classifications, filtering)
- **Main Model Operations**: 1-3s (reasoning, conversation)
- **Context Pollution**: 0% (independent utility operations)
- **Speed Improvement**: 20x faster for utility tasks
- **Memory Efficiency**: Enhanced semantic filtering reduces irrelevant memories

### Typical Usage Patterns
- **User Data Queries**: 0.00s instant response from profile storage
- **Local Processing**: 85% of interactions (greetings, simple questions)
- **External Consultation**: 15% for scientific/factual accuracy
- **Memory Efficiency**: Automatic compression keeps database under 100MB
- **Response Quality**: Clean professional output without contamination

### Hardware Requirements
- **Minimum**: 16GB RAM, Apple Silicon M1/M2/M3
- **Recommended**: 32GB+ RAM for optimal dual-model performance
- **Storage**: ~10GB (both models + data)
- **GPU**: Metal acceleration for optimal performance 