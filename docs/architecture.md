# Prometheus Framework Architecture

## Overview

Prometheus is designed around four core principles:
1. **Identity-driven configuration** - Agent personalities defined in JSON
2. **Intelligent hybrid routing** - Local-first with smart external consultation
3. **Persistent conversational memory** - RAG-powered context and learning
4. **User data intelligence** - Automatic extraction and personalized responses

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
             ┌──────────┐ ┌────────┐ ┌──────────┐
             │Config-   │ │ User   │ │ Local    │
             │Driven    │ │Profile │ │ LLM      │
             │Patterns  │ │Store   │ │(Phi-3M)  │
             └──────────┘ └────────┘ └──────────┘
                             │            │
                             ▼            ▼
                     ┌────────────┐ ┌──────────┐
                     │Vector Store│ │External  │
                     │(ChromaDB)  │ │LLM       │
                     └────────────┘ └──────────┘
                             │
                             ▼
                     ┌──────────────────┐
                     │   Reflection     │
                     │    Engine        │
                     └──────────────────┘
```

## Core Components

### 1. Identity Management System
- **JSON-Based Configuration**: Complete agent identity in `aletheia/identity/identity.json`
- **English-Primary Design**: Core personality in English for optimal model performance
- **Translation Layer**: Seamless multilingual interactions
- **Template System**: Easy creation of new agent personalities

### 2. Intelligent Hybrid Routing
- **Meta-Cognitive Assessment**: Local LLM decides when external help is needed
- **Self-Aware Routing**: Uses internal confidence scoring
- **Cost Optimization**: 85% local processing, 15% external consultation
- **Scientific Accuracy**: Prevents misinformation through smart routing

### 3. Conversational Memory System
- **Vector-Based Retrieval**: RAG-powered memory with semantic search
- **Hierarchical Storage**: Automatic tiering (raw → summary → key facts)
- **User Profile Management**: Dedicated storage for personal data
- **Context Continuity**: Maintains topic threads and reference resolution
- **Automatic Compression**: Intelligent summarization to manage memory
- **Learning Integration**: Stores successful interaction patterns

### 4. User Data Intelligence System
- **Automatic Extraction**: Pattern-based detection of personal information
- **Real-time Storage**: Instant saving to user profiles
- **Zero-latency Queries**: Direct profile access without LLM calls
- **Personalized Context**: User data integration into conversations
- **Privacy-first Design**: Local storage with encryption support

### 5. Modular Processing Pipeline
- **Config-Driven Architecture**: All patterns defined in JSON configurations
- **Modular Processors**: Filters, extractors, detectors, validators
- **Extensible Design**: Easy addition of new data types and patterns
- **Multilingual Support**: Consistent behavior across languages
- **Performance Optimized**: Fast local processing with intelligent routing

## Agent Orchestrator Philosophy

### The "Smart Conductor with Memory" Approach

**Traditional AI**: Tries to know everything
- Risk of confident misinformation
- High computational costs
- Limited adaptability
- No personal context

**Prometheus Approach**: Knows when to ask for help AND remembers users
- Meta-cognitive assessment of competence
- Intelligent orchestration of resources
- Prevention of misinformation through humility
- Cost-effective resource utilization
- Personalized responses using stored user data
- Instant access to user information

### Routing Strategy

1. **User Data Check**: First check if it's a data query (0.00s response)
2. **Self-Assessment**: Local LLM evaluates its competence
3. **Profile Integration**: Include user data in context when relevant
4. **Confidence Scoring**: Determines routing based on uncertainty
5. **Scientific Detection**: Auto-routes factual/scientific questions
6. **Context Awareness**: Considers conversation history and user profile
7. **Default Local**: Simple conversations stay local

## Data Processing Architecture

### User Data Extraction Pipeline

```
User Input → Pattern Matching → Data Extraction → Profile Update → Response
     │              │               │               │             │
     ▼              ▼               ▼               ▼             ▼
┌─────────┐  ┌────────────┐  ┌─────────────┐  ┌──────────┐  ┌─────────┐
│Natural  │  │Config-based│  │Structured   │  │JSON      │  │Enhanced │
│Language │  │Regex       │  │Data Points  │  │Profile   │  │Context  │
│Text     │  │Patterns    │  │w/Confidence │  │Storage   │  │Response │
└─────────┘  └────────────┘  └─────────────┘  └──────────┘  └─────────┘
```

### Configuration Structure

```
aletheia/processing/configs/
├── user_data_extractor.json    # Personal data patterns
├── entity_extractor.json       # Topic/entity extraction  
├── name_extractor.json         # User name detection
├── reference_detector.json     # Context references
├── complexity_detector.json    # Task complexity assessment
└── factual_validator.json      # Response validation
```

## File Structure

```
prometheus/
├── aletheia/                    # Main agent implementation
│   ├── identity/               # Identity management system
│   │   ├── identity.json       # Agent personality configuration
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
│   │   ├── local_llm.py       # Local model wrapper
│   │   └── external_llm.py    # External API clients
│   └── agent/                 # Agent behavior
│       ├── orchestrator.py    # Main orchestrator
│       ├── context_manager.py # Conversation context
│       ├── planner.py         # Task planning
│       └── reflexion.py       # Self-reflection
├── tests/                     # Comprehensive test suite
├── scripts/                   # Setup and utility scripts
├── docs/                      # Documentation
└── models/                    # Local model storage
```

## Performance Characteristics

### Typical Usage Patterns
- **User Data Queries**: 0.00s instant response from profile storage
- **Local Processing**: 85% of interactions (greetings, simple questions)
- **External Consultation**: 15% for scientific/factual accuracy
- **Memory Efficiency**: Automatic compression keeps database under 100MB
- **Response Times**: 0.5-2s local, 2-5s external consultation

### Hardware Requirements
- **Minimum**: 16GB RAM, Apple Silicon M1/M2/M3
- **Recommended**: 32GB+ RAM for optimal performance
- **Storage**: ~5GB (model + dependencies + data)

## Data Privacy & Security

### User Data Protection
- **Local Storage**: All user data stored locally in JSON profiles
- **No External Sharing**: User information never sent to external LLMs
- **Encryption Ready**: Storage designed for easy encryption integration
- **Granular Control**: Users can delete or modify their data anytime

### Memory Management
- **Hierarchical Tiering**: Automatic data archiving and compression
- **Selective Retention**: Important user data preserved, temporary data cleaned
- **Privacy Controls**: Easy profile deletion and data export

## Future Vision: Knowledge Orchestra with Personal Memory

The framework envisions AI agents as intelligent coordinators with persistent memory:
- **Personal AI Assistants**: Deep understanding of individual users
- **Domain Specialists**: LoRA extensions for specialized knowledge
- **Service Integrators**: Coordination with external tools and APIs
- **Learning Systems**: Continuous improvement through interaction patterns
- **Collaborative Networks**: Multi-agent coordination with shared context
- **Privacy-First Design**: User data sovereignty and control 