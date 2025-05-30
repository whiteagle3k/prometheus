# Prometheus ✨
![CI](https://github.com/whiteagle3k/prometheus/actions/workflows/ci.yml/badge.svg)

Identity-driven AI framework with hybrid LLM routing and conversational memory.

## Why Prometheus?

- **Cost-effective**: Local "brain" handles 85% of conversations → cheap and private
- **Smart routing**: External LLMs only when local model needs help  
- **Identity-driven**: Agent personality configured in JSON → easy to extend
- **Conversational memory**: Persistent context with vector storage and compression

## Meet Aletheia 👩

Aletheia is our first female AI agent - a thoughtful research assistant with:
- **Multilingual**: Fluent Russian and English with proper grammar
- **Self-aware**: Knows when to ask external experts for help
- **Context-aware**: Remembers conversations and understands references
- **Learning**: Improves through reflection and experience

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │───▶│   Orchestrator   │───▶│   Response      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
            ┌───────────┐ ┌─────────┐ ┌──────────┐
            │ Identity  │ │ Context │ │   LLM    │
            │   JSON    │ │ Memory  │ │ Router   │
            └───────────┘ └─────────┘ └──────────┘
                                          │
                              ┌───────────┴───────────┐
                              ▼                       ▼
                      ┌───────────────┐      ┌──────────────┐
                      │   Local LLM   │      │ External LLM │
                      │ (Phi-3 Mini)  │      │(Claude/GPT-4)│
                      └───────────────┘      └──────────────┘
```

## Core Features

- **Identity Management**: JSON-based personality configuration
- **Meta-cognitive Routing**: Self-assessment for smart LLM selection  
- **Vector Memory**: RAG-powered conversation history and learning
- **Reference Resolution**: Understands "it", "that", "tell me more"
- **Reflection Engine**: Self-improvement through experience analysis
- **Processing Pipeline**: Configurable text analysis (no hardcoded patterns)
- **Multilingual Context**: Seamless Russian/English conversation flow
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

### Hardware Requirements
- **Minimum**: 16GB RAM, Apple Silicon M1/M2/M3
- **Recommended**: 32GB+ RAM
- **Storage**: ~5GB (model + data)

## Usage Examples

### First Meeting
```
🧑 You: Привет! Меня зовут Игорь.
🤖 Aletheia: Привет, Игорь! Я Алетейя, женский автономный исследователь-агент. 
Рада познакомиться! Готова помочь с анализом и исследованиями.
💭 Thoughts: 1.2s | Route: local
```

### Smart Routing in Action
```
🧑 You: Что такое водяной пар?
🤖 Aletheia: [Self-assessment] → Scientific question → [Consulting external expert]

Водяной пар — это газообразное состояние воды, образующееся при испарении 
или кипении. Он невидим глазу, но играет ключевую роль в атмосферных процессах.
💭 Thoughts: 2.1s | Route: external | Scientific accuracy prioritized
```

### Context Continuity
```
🧑 You: А как он образуется?
🤖 Aletheia: [Context: водяной пар] → Continuing scientific topic...

Водяной пар образуется тремя способами:
1. Испарение с поверхности воды
2. Кипение при 100°C 
3. Сублимация льда напрямую в пар
💭 Thoughts: 1.8s | Route: external | Context maintained
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
- [x] Generic processing pipeline (no hardcoded patterns)

### Phase 2: Enhancement 🔄
- [ ] Advanced context relationship graphs
- [ ] Multi-agent template system
- [ ] Enhanced memory compression
- [ ] Domain-specific knowledge routing

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
│   ├── processing/            # Configurable text processing
│   ├── llm/                   # Hybrid routing system
│   ├── memory/                # Vector storage and RAG
│   └── agent/                 # Orchestrator and context management
├── docs/                      # Detailed documentation
├── tests/                     # Comprehensive test suite
└── scripts/                   # Setup and utilities
```

## Documentation

- **[Architecture](docs/architecture.md)** - Detailed system design and philosophy
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
