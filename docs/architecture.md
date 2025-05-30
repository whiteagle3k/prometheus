# Prometheus Framework Architecture

## Overview

Prometheus is designed around three core principles:
1. **Identity-driven configuration** - Agent personalities defined in JSON
2. **Intelligent hybrid routing** - Local-first with smart external consultation
3. **Persistent conversational memory** - RAG-powered context and learning

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
                     ┌─────────┴─────────┐
                     ▼                   ▼
             ┌──────────────┐    ┌──────────────┐
             │ Conversation │    │   LLM Router │
             │   Context    │    │   (Smart)    │
             └──────────────┘    └──────────────┘
                               │
                     ┌─────────┴─────────┐
                     ▼                   ▼
             ┌──────────────┐    ┌──────────────┐
             │  Local LLM   │    │ External LLM │
             │ (Phi-3 Mini) │    │(Claude/GPT-4)│
             └──────────────┘    └──────────────┘
                               │
                               ▼
                     ┌──────────────────┐
                     │  Vector Memory   │
                     │   (ChromaDB)     │
                     └──────────────────┘
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
- **Context Continuity**: Maintains topic threads and reference resolution
- **Automatic Compression**: Intelligent summarization to manage memory
- **Learning Integration**: Stores successful interaction patterns

### 4. Processing Pipeline
- **Generic Architecture**: No hardcoded patterns - all JSON-configurable
- **Modular Processors**: Filters, extractors, detectors, validators
- **Multilingual Support**: Consistent behavior across languages
- **Performance Optimized**: Fast local processing with intelligent routing

## Agent Orchestrator Philosophy

### The "Smart Conductor" Approach

**Traditional AI**: Tries to know everything
- Risk of confident misinformation
- High computational costs
- Limited adaptability

**Prometheus Approach**: Knows when to ask for help
- Meta-cognitive assessment of competence
- Intelligent orchestration of resources
- Prevention of misinformation through humility
- Cost-effective resource utilization

### Routing Strategy

1. **Self-Assessment**: Local LLM evaluates its competence
2. **Confidence Scoring**: Determines routing based on uncertainty
3. **Scientific Detection**: Auto-routes factual/scientific questions
4. **Context Awareness**: Considers conversation history
5. **Default Local**: Simple conversations stay local

## File Structure

```
prometheus/
├── aletheia/                    # Main agent implementation
│   ├── identity/               # Identity management system
│   │   ├── identity.json       # Agent personality configuration
│   │   ├── loader.py          # Configuration loading
│   │   └── validator.py       # Schema validation
│   ├── processing/            # Generic text processing system
│   │   ├── configs/           # JSON configuration files
│   │   ├── pipeline.py        # Processing pipeline
│   │   └── *.py              # Processors (filters, extractors, etc.)
│   ├── llm/                   # Language model management
│   │   ├── router.py          # Intelligent routing logic
│   │   ├── local_llm.py       # Local model wrapper
│   │   └── external_llm.py    # External API clients
│   ├── memory/                # Memory and persistence
│   │   ├── vector_store.py    # ChromaDB wrapper
│   │   └── summariser.py      # Memory compression
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
- **Local Processing**: 85% of interactions (greetings, simple questions)
- **External Consultation**: 15% for scientific/factual accuracy
- **Memory Efficiency**: Automatic compression keeps database under 100MB
- **Response Times**: 0.5-2s local, 2-5s external consultation

### Hardware Requirements
- **Minimum**: 16GB RAM, Apple Silicon M1/M2/M3
- **Recommended**: 32GB+ RAM for optimal performance
- **Storage**: ~5GB (model + dependencies + data)

## Future Vision: Knowledge Orchestra

The framework envisions AI agents as intelligent coordinators rather than encyclopedias:
- **Domain Specialists**: LoRA extensions for deep knowledge
- **Service Integrators**: Coordination with external tools
- **Learning Systems**: Continuous improvement through self-assessment
- **Collaborative Networks**: Multi-agent coordination capabilities 