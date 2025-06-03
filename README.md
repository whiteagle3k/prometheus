# Prometheus ✨
![CI](https://github.com/whiteagle3k/prometheus/actions/workflows/ci.yml/badge.svg)

Identity-driven AI framework with dual-model architecture, intelligent routing, conversational memory, and comprehensive debugging capabilities.

## Why Prometheus?

- **Dual-Model Architecture**: Fast utility model + powerful reasoning model → optimal performance
- **Cost-effective**: Local "brain" handles 85% of conversations → cheap and private
- **Smart routing**: External LLMs only when local model needs help  
- **Identity-driven**: Agent personality configured in JSON → easy to extend
- **Conversational memory**: Persistent context with vector storage and semantic filtering
- **Enhanced debugging**: Comprehensive visibility into model usage and decision-making
- **Robust parsing**: Clean responses without internal field contamination

## Meet Aletheia 👩

Aletheia is our first female AI agent - a thoughtful research assistant with:
- **Multilingual**: Fluent Russian and English with proper grammar
- **Self-aware**: Knows when to ask external experts for help
- **Context-aware**: Remembers conversations and preserves topic continuity
- **Learning**: Improves through reflection and experience
- **Personal**: Remembers user data and provides personalized responses
- **Instant recall**: Zero-latency access to user information
- **Clean responses**: Professional output without technical contamination

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │───▶│   Orchestrator   │───▶│   Response      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
            ┌───────────┐ ┌─────────┐ ┌──────────┐
            │ Identity  │ │ Memory  │ │   LLM    │
            │   JSON    │ │ System  │ │ Router   │
            └───────────┘ └─────────┘ └──────────┘
                              │           │
                    ┌─────────┼─────┐     │
                    ▼         ▼     ▼     ▼
            ┌──────────┐ ┌────────┐ ┌──────────────┐
            │ Vector   │ │ User   │ │ Utility LLM  │
            │ Memory   │ │Profile │ │(Classification)│
            └──────────┘ └────────┘ └──────────────┘
                                          │
                              ┌───────────┴───────────┐
                              ▼                       ▼
                      ┌───────────────┐      ┌──────────────┐
                      │   Local LLM   │      │ External LLM │
                      │(Phi-3 Medium) │      │(Claude/GPT-4)│
                      └───────────────┘      └──────────────┘
```

## Core Features

### 🧠 Intelligence & Memory
- **Dual-Model System**: Utility model (phi-3-mini) for fast classification + main model for reasoning
- **Identity Management**: JSON-based personality configuration
- **Meta-cognitive Routing**: Self-assessment for smart LLM selection  
- **Vector Memory**: RAG-powered conversation history with semantic filtering
- **User Profiles**: Automatic extraction and storage of personal data
- **Instant Data Queries**: Zero-latency access to user information

### 💬 Conversation & Context
- **Reference Resolution**: Understands "it", "that", "tell me more"
- **Topic Preservation**: Maintains conversation continuity and context flow
- **Multilingual Context**: Seamless Russian/English conversation flow
- **Personalized Responses**: Context-aware using stored user data
- **Clean Output**: Professional responses without technical field contamination

### 🏗️ Architecture & Processing
- **Modular Design**: Clean separation of concerns with configurable components
- **Dual-Model Performance**: 20x faster classifications with zero context pollution
- **Enhanced Debugging**: Comprehensive utility model usage visibility
- **Processing Pipeline**: Config-driven text analysis with JSON patterns
- **Reflection Engine**: Self-improvement through experience analysis
- **Cost Optimization**: ~$0.01-0.03 per external consultation

## Quick Start (macOS)

```bash
git clone https://github.com/whiteagle3k/prometheus.git
cd prometheus
./scripts/install_mac.sh
./scripts/download_models.sh  # Downloads both required models
poetry run aletheia
```

## Configuration

### Model Configuration
Both models are configured in `aletheia/identity/identity.json`:
```json
{
  "module_paths": {
    "local_model_gguf": "models/Phi-3-medium-4k-instruct-Q4_K_M.gguf",
    "utility_model_gguf": "models/phi-3-mini-3.8b-q4_k.gguf",
    "memory_dir": "storage/chroma"
  }
}
```

### Identity Configuration
Agent personality is defined in `aletheia/identity/identity.json`:
```json
{
  "name": "Aletheia",
  "identity": {
    "summary": "Female autonomous research agent",
    "personality": ["Thoughtful", "Precise", "Helpful"]
  },
  "translations": {
    "ru": {
      "llm_instructions": "Ты — Алетейя, женский ИИ-агент..."
    }
  }
}
```

### Hardware Requirements
- **Minimum**: 16GB RAM, Apple Silicon M1/M2/M3
- **Recommended**: 32GB+ RAM for optimal dual-model performance
- **Storage**: ~10GB (both models + data)

## Usage Examples

### Dual-Model Architecture in Action
```
🧑 You: что такое Сфера Дайсона?

🔧 Utility model: Classifying query for memory filtering...
🔧 Query categorized as: technical
🔧 Utility model: Categorizing 8 memories...
🔧 → technical, conversational, technical
🔧 Utility model: Filtering complete. 5/8 memories passed filtering

🤖 Aletheia: Сфера Дайсона — это гипотетическое масштабное сооружение...
💭 Thoughts: 2.1s | Route: local | Classifications: 60ms
```

### Clean Response Output
```
🧑 You: как тебя зовут?
🤖 Aletheia: Здравствуй! Меня зовут Алетейя. Я рада встрече с вами.
✅ Clean response: No contamination detected
💭 Thoughts: 1.8s | Route: local | Parsing: Fixed
```

### Context Preservation
```
🧑 You: А сейчас возможно её построить?
🤖 Aletheia: Да, в теории, можно построить Сферу Дайсона, но это потребует огромных технологических достижений...
📝 Context preserved: "её" correctly referenced Dyson Sphere from previous question
💭 Thoughts: 2.4s | Route: local | Topic continuity: Working
```

### Performance Monitoring
```
🧑 You: status
📊 Agent Status: {
  "memory_stats": {"total_memories": 45, "utility_classifications": 120},
  "router_health": {"local_model": true, "utility_model": true},
  "dual_model_performance": {
    "utility_speed": "60-140ms", 
    "classification_accuracy": "95%",
    "context_pollution": "0%"
  }
}
```

## CLI Commands

- `quit` - Exit gracefully
- `status` - Show diagnostics and dual-model performance stats
- `reset` - Clear memory and conversation history  
- `context` - Display recent conversation
- `plan: <task>` - Force planning mode for complex tasks

## Latest Achievements ✨

### Dual-Model Architecture
- **Utility Model**: Fast phi-3-mini for classification (60-140ms)
- **Main Model**: Powerful phi-3-medium for reasoning
- **Performance**: 20x faster utility tasks, zero context pollution
- **Configuration**: Both models managed through identity.json

### Enhanced Parsing & Output
- **Clean Responses**: Eliminated all field contamination (CONFIDENCE, REASONING, etc.)
- **Professional Output**: No technical markers in user-facing responses
- **Robust Extraction**: Multiple parsing strategies with contextual fallbacks

### Improved Context & Memory
- **Topic Preservation**: Maintains conversation continuity across questions
- **Semantic Filtering**: Intelligent memory categorization and relevance scoring
- **Enhanced Debug**: Comprehensive visibility into utility model operations

### Better Routing Intelligence
- **Self-Assessment**: Local model evaluates its own confidence
- **Validation Rules**: Fallback routing for inconsistent assessments
- **Scientific Topics**: Proper routing for technical/scientific questions

## Roadmap

### Phase 1: Foundation ✅
- [x] Aletheia personality and identity system
- [x] Meta-cognitive routing with self-assessment
- [x] Vector memory with conversation context
- [x] Multilingual support (Russian/English)
- [x] Modular processing pipeline (config-driven patterns)
- [x] User data extraction and profile management
- [x] Instant user data queries with zero latency
- [x] **Dual-model architecture with utility LLM**
- [x] **Enhanced parsing and clean response output**
- [x] **Topic preservation and context continuity**
- [x] **Comprehensive debugging and monitoring**

### Phase 2: Enhancement 🔄
- [ ] Advanced context relationship graphs
- [ ] Multi-agent template system
- [ ] Enhanced memory compression
- [ ] Domain-specific knowledge routing
- [ ] Advanced user preference learning
- [ ] Model performance optimization

### Phase 3: Ecosystem 🚀
- [ ] Plugin architecture for specialized agents
- [ ] Multi-agent collaboration protocols
- [ ] Cross-platform deployment (Windows/Linux)
- [ ] Community agent marketplace

## File Structure

```
prometheus/
├── aletheia/                   # Main agent implementation
│   ├── identity/              # JSON-based personality system
│   ├── processing/            # Modular text processing
│   │   ├── configs/           # Pattern configurations (JSON)
│   │   └── extractors.py      # Data extraction engines
│   ├── memory/                # Storage and retrieval systems
│   │   ├── vector_store.py    # Vector memory storage
│   │   ├── hierarchical_store.py # Advanced memory management
│   │   └── user_profile_store.py # Personal data storage
│   ├── llm/                   # Hybrid routing system
│   └── agent/                 # Orchestrator and context management
├── docs/                      # Detailed documentation
├── tests/                     # Comprehensive test suite
└── scripts/                   # Setup and utilities
```

## New in v0.4.0

### 🎯 **User Data Intelligence**
- **Automatic extraction** of personal information from natural conversation
- **Instant data queries** with zero-latency profile access
- **Personalized responses** using stored user context

### 🏗️ **Modular Architecture** 
- **Config-driven processing** with JSON pattern definitions
- **Clean separation** of concerns (memory, processing, routing)
- **Extensible extractors** for different data types

### 💾 **Enhanced Memory System**
- **User profile storage** in dedicated memory subsystem
- **Hierarchical memory** with automatic tiering
- **Profile-aware context** integration

## Documentation

- **[Architecture](docs/architecture.md)** - Detailed system design and philosophy
- **[Memory System](docs/memory.md)** - Three-tier memory architecture and safety features
- **[Configuration](docs/configuration.md)** - Complete setup and customization guide  
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

## Contributing

```bash
# Development setup
git clone https://github.com/yourusername/prometheus.git
cd prometheus
./scripts/install_mac.sh

# Run tests
poetry run pytest tests/ -v

# Code quality
poetry run ruff check aletheia/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Ready to meet Aletheia?** 🚀

```bash
poetry run aletheia
```

*Prometheus - Identity-driven AI agents with smart routing and conversational memory.*
