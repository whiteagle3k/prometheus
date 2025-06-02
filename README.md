# Prometheus ✨
![CI](https://github.com/whiteagle3k/prometheus/actions/workflows/ci.yml/badge.svg)

Identity-driven AI framework with hybrid LLM routing, conversational memory, and intelligent user data management.

## Why Prometheus?

- **Cost-effective**: Local "brain" handles 85% of conversations → cheap and private
- **Smart routing**: External LLMs only when local model needs help  
- **Identity-driven**: Agent personality configured in JSON → easy to extend
- **Conversational memory**: Persistent context with vector storage and compression
- **User data intelligence**: Automatic extraction and personalized responses
- **Modular architecture**: Config-driven processing with clean separation of concerns

## Meet Aletheia 👩

Aletheia is our first female AI agent - a thoughtful research assistant with:
- **Multilingual**: Fluent Russian and English with proper grammar
- **Self-aware**: Knows when to ask external experts for help
- **Context-aware**: Remembers conversations and understands references
- **Learning**: Improves through reflection and experience
- **Personal**: Remembers user data and provides personalized responses
- **Instant recall**: Zero-latency access to user information

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
            ┌──────────┐ ┌────────┐ ┌──────────┐
            │ Vector   │ │ User   │ │Processing│
            │ Memory   │ │Profile │ │ Pipeline │
            └──────────┘ └────────┘ └──────────┘
                                          │
                              ┌───────────┴───────────┐
                              ▼                       ▼
                      ┌───────────────┐      ┌──────────────┐
                      │   Local LLM   │      │ External LLM │
                      │ (Phi-3 Medium)│      │(Claude/GPT-4)│
                      └───────────────┘      └──────────────┘
```

## Core Features

### 🧠 Intelligence & Memory
- **Identity Management**: JSON-based personality configuration
- **Meta-cognitive Routing**: Self-assessment for smart LLM selection  
- **Vector Memory**: RAG-powered conversation history and learning
- **User Profiles**: Automatic extraction and storage of personal data
- **Instant Data Queries**: Zero-latency access to user information

### 💬 Conversation & Context
- **Reference Resolution**: Understands "it", "that", "tell me more"
- **Multilingual Context**: Seamless Russian/English conversation flow
- **Personalized Responses**: Context-aware using stored user data
- **Conversation Continuity**: Maintains context across sessions

### 🏗️ Architecture & Processing
- **Modular Design**: Clean separation of concerns with configurable components
- **Processing Pipeline**: Config-driven text analysis with JSON patterns
- **Reflection Engine**: Self-improvement through experience analysis
- **Cost Optimization**: ~$0.01-0.03 per external consultation

## Quick Start (macOS)

```bash
git clone https://github.com/whiteagle3k/prometheus.git
cd prometheus
./scripts/install_mac.sh
poetry run aletheia
```

## Configuration

### Basic Setup
```bash
cp .env.example .env
# Add your API keys (optional but recommended)
nano .env
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

### Processing Configuration
Text processing patterns in `aletheia/processing/configs/`:
```json
{
  "enabled": true,
  "parameters": {
    "physical_patterns": [
      {
        "pattern": "(?:я\\s+)?(?:вешу|весу)\\s+(\\d+)\\s*кг",
        "key": "weight",
        "confidence": 0.95
      }
    ]
  }
}
```

### Hardware Requirements
- **Minimum**: 16GB RAM, Apple Silicon M1/M2/M3
- **Recommended**: 32GB+ RAM
- **Storage**: ~5GB (model + data)

## Usage Examples

### Personal Data Learning
```
🧑 You: Привет! Меня зовут Игорь. Сейчас я вешу 80кг при росте 190см.
🤖 Aletheia: Привет, Игорь! Рада познакомиться! 
📊 Extracted 3 user data points
💭 Thoughts: 1.2s | Route: local | Data stored
```

### Instant Data Recall
```
🧑 You: напомни мне мои данные
🤖 Aletheia: Profile for Игорь:

Physical Data:
• Weight: 80kg
• Height: 190cm
• Body Fat Percentage: 19%
💭 Thoughts: 0.00s | Route: user_profile | Instant response
```

### Personalized Context
```
🧑 You: Как мне лучше тренироваться для похудения?
🤖 Aletheia: Игорь, учитывая ваш вес 80кг и рост 190см, рекомендую...
💭 Thoughts: 2.1s | Route: local | User profile integrated
```

### Smart Routing in Action
```
🧑 You: Объясни биохимические процессы жиросжигания
🤖 Aletheia: [Self-assessment] → Complex scientific question → [External expert]

При кардио нагрузках жиры расщепляются через липолиз...
💭 Thoughts: 3.2s | Route: external | $0.015 cost
```

## CLI Commands

- `quit` - Exit gracefully
- `status` - Show diagnostics and routing statistics
- `reset` - Clear memory and conversation history  
- `context` - Display recent conversation
- `plan: <task>` - Force planning mode for complex tasks

## Roadmap

### Phase 1: Foundation ✅
- [x] Aletheia personality and identity system
- [x] Meta-cognitive routing with self-assessment
- [x] Vector memory with conversation context
- [x] Multilingual support (Russian/English)
- [x] Modular processing pipeline (config-driven patterns)
- [x] User data extraction and profile management
- [x] Instant user data queries with zero latency

### Phase 2: Enhancement 🔄
- [ ] Advanced context relationship graphs
- [ ] Multi-agent template system
- [ ] Enhanced memory compression
- [ ] Domain-specific knowledge routing
- [ ] Advanced user preference learning

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
