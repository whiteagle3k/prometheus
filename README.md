# Prometheus ✨
![CI](https://github.com/whiteagle3k/prometheus/actions/workflows/ci.yml/badge.svg)

Entity-based AI framework with clean architecture, dual-model intelligence, and generic core components.

## Why Prometheus?

- **Entity-based Design**: Clean separation between framework core and agent implementations
- **Generic Core Components**: Reusable LocalLLM, router, and memory systems
- **Dual-Model Architecture**: Fast utility model + powerful reasoning model → optimal performance
- **Cost-effective**: Local "brain" handles 85% of conversations → cheap and private
- **Smart routing**: External LLMs only when local model needs help  
- **Clean architecture**: No coupling between core framework and specific entities
- **English-first system**: Consistent internal language with multilingual responses
- **Robust parsing**: Clean responses without internal field contamination

## Meet Aletheia 👩

Aletheia is our first autonomous AI entity - a thoughtful research assistant with:
- **Entity-based**: Built using the generic Prometheus framework
- **Multilingual**: Fluent Russian and English with proper feminine grammar forms
- **Self-aware**: Knows when to ask external experts for help
- **Context-aware**: Remembers conversations and preserves topic continuity
- **Learning**: Improves through reflection and experience
- **Personal**: Remembers user data and provides personalized responses
- **Clean responses**: Professional output without technical contamination

## Entity-Based Architecture

```
        ┌─────────────────┐
        │   Prometheus    │
        │   Framework     │
        │     (Core)      │
        └─────────────────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│Aletheia │ │ Agent B │ │ Agent C │
│ Entity  │ │ Entity  │ │ Entity  │
└─────────┘ └─────────┘ └─────────┘
    │
    ▼
┌────────────────────────────────────┐
│         Core Framework             │
├──────────┬──────────┬──────────────┤
│BaseEntity│ LocalLLM │ LLMRouter    │
│(Generic) │(Generic) │ (Generic)    │
└──────────┴──────────┴──────────────┘
    │           │           │
    ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────────┐
│Processing│ │ Memory  │ │ External    │
│Pipeline │ │ System  │ │ LLM Clients │
└─────────┘ └─────────┘ └─────────────┘
```

## Core Features

### 🏗️ Clean Architecture
- **Entity-based Design**: Autonomous entities with their own identities
- **Generic Core**: Reusable components work with any entity configuration
- **Separation of Concerns**: Core framework + entity implementations
- **No Coupling**: Framework components don't know about specific entities
- **Dependency Injection**: Identity config passed to core components

### 🧠 Intelligence & Memory
- **Dual-Model System**: Utility model (phi-3-mini) for fast classification + main model for reasoning
- **Generic LocalLLM**: Works with any entity's identity configuration
- **English-first System**: Consistent internal language, multilingual responses
- **Meta-cognitive Routing**: Self-assessment for smart LLM selection  
- **Vector Memory**: RAG-powered conversation history with semantic filtering
- **User Profiles**: Automatic extraction and storage of personal data

### 💬 Conversation & Context
- **Clean Response Format**: Simple `ANSWER`, `CONFIDENCE`, `REASONING` structure
- **Topic Preservation**: Maintains conversation continuity and context flow
- **Multilingual Context**: Seamless language switching in responses
- **Personalized Responses**: Context-aware using stored user data
- **Professional Output**: No technical field contamination in user responses

## Quick Start (macOS)

```bash
# Clone and setup
git clone https://github.com/whiteagle3k/prometheus.git
cd prometheus
./scripts/install_mac.sh
./scripts/download_models.sh  # Downloads both required models

# Start Aletheia entity
poetry run python prometheus.py aletheia

# Alternative: Direct Python execution
python prometheus.py aletheia
```

Once running, you can interact with Aletheia in natural language:
```
🤖 Aletheia: Привет! Я Алетейя, готова помочь. Как дела?
🧑 You: расскажи про квантовую механику
🤖 Aletheia: [Intelligent routing to external expert, then personalized response]
```

## Documentation

For detailed information, see our comprehensive documentation:

### 📚 Core Documentation
- **[Architecture Guide](docs/architecture.md)** - Framework design, entity system, and component relationships
- **[Memory System](docs/memory.md)** - Vector storage, user profiles, context management, and three-tier memory
- **[Configuration Reference](docs/configuration.md)** - Identity setup, model configuration, and customization options
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues, debugging, and performance optimization

### 🏗️ Development Guides
- **Entity Development** - Creating new autonomous agents (see `docs/architecture.md`)
- **Core Extension** - Adding framework components and capabilities
- **Memory Integration** - Implementing custom memory and learning systems
- **LLM Integration** - Adding new local or external model providers

### 📖 Quick Reference
- **CLI Commands** - Interactive commands and debugging utilities
- **Configuration Examples** - Sample entity configurations and setups
- **API Reference** - Core component interfaces and usage patterns

## Configuration

### Entity Configuration
Each entity has its own identity configuration:
```json
{
  "name": "Aletheia",
  "llm_instructions": "You are Aletheia, a female autonomous technical agent. When responding in Russian, always use feminine language forms: готова (not готов), рада (not рад)...",
  "personality": {
    "summary": "Female autonomous research agent"
  },
  "module_paths": {
    "local_model_gguf": "models/Phi-3-medium-4k-instruct-Q4_K_M.gguf",
    "utility_model_gguf": "models/phi-3-mini-3.8b-q4_k.gguf",
    "memory_dir": "storage/chroma"
  },
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

### Hardware Requirements
- **Minimum**: 16GB RAM, Apple Silicon M1/M2/M3
- **Recommended**: 32GB+ RAM for optimal dual-model performance
- **Storage**: ~10GB (both models + data)

## Usage Examples

### Entity-based Interaction
```
🧑 You: что такое Сфера Дайсона?

🔧 Utility model: Classifying query for memory filtering...
🔧 Query categorized as: technical
🔧 LocalLLM: Using English system instructions
🔧 LocalLLM: Generating Russian response with feminine forms

🤖 Aletheia: Сфера Дайсона — это гипотетическое масштабное сооружение...
💭 Thoughts: 2.1s | Route: local | Classifications: 60ms
```

### Clean Generic Response Format
```
🧑 You: как тебя зовут?
🤖 Aletheia: Здравствуйте! Меня зовут Алетейя, я готова помочь.
✅ Clean response: No technical contamination
💭 LocalLLM: Generic format, entity-specific content
```

### Generic System Design
```
🧑 You: status
📊 Framework Status: {
  "entity": "AletheiaEntity",
  "identity_loaded": true,
  "core_components": {
    "local_llm": "generic, no entity coupling",
    "router": "entity-agnostic routing",
    "memory": "reusable vector store"
  },
  "architecture": "clean separation of concerns"
}
```

## CLI Commands

- `quit` - Exit gracefully
- `status` - Show entity and framework diagnostics
- `reset` - Clear memory and conversation history  
- `context` - Display recent conversation
- `plan: <task>` - Force planning mode for complex tasks

## File Structure

```
prometheus/
├── core/                      # Generic framework components
│   ├── base_entity.py         # Abstract base class
│   ├── llm/
│   │   ├── local_llm.py       # Generic local LLM wrapper
│   │   ├── utility_llm.py     # Fast utility model
│   │   ├── router.py          # Intelligent routing
│   │   └── external_llm.py    # External API clients
│   ├── memory/                # Memory systems
│   ├── context/               # Context management
│   └── processing/            # Text processing modules
├── entities/                  # Entity implementations
│   ├── __init__.py           # Entity registry
│   └── aletheia/             # Aletheia entity
│       ├── __init__.py       # AletheiaEntity class
│       └── identity/
│           └── identity.json # Aletheia configuration
├── prometheus.py             # CLI interface
├── tests/                    # Test suite
└── models/                   # Model storage
```

## Latest Achievements ✨

### Clean Entity-Based Architecture
- **Generic Core**: Framework components work with any entity
- **No Coupling**: Core doesn't know about specific entities
- **Clean Separation**: Framework vs entity implementation
- **Dependency Injection**: Identity config passed to components

### Improved LocalLLM Design
- **Generic Implementation**: Works with any identity configuration
- **English-first System**: Consistent internal language
- **Simple Response Format**: `ANSWER`, `CONFIDENCE`, `REASONING`
- **No Routing Logic**: Pure text generation component

### Enhanced Parsing & Output
- **Clean Responses**: Eliminated all field contamination
- **Professional Output**: No technical markers in user-facing responses
- **Robust Extraction**: Multiple parsing strategies with contextual fallbacks
- **Topic Preservation**: Maintains conversation continuity

### Better Framework Design
- **Reusable Components**: Generic LocalLLM, router, memory
- **Entity Registry**: Easy addition of new agent types
- **Clean Configuration**: Identity-driven setup per entity
- **Maintainable Code**: Proper separation of concerns

## Development

### Adding New Entities
```python
class MyAgentEntity(BaseEntity):
    IDENTITY_PATH = Path(__file__).parent / "identity"
    
    def _load_identity(self) -> Dict[str, Any]:
        # Load your entity's specific configuration
        # Return complete identity config
```

For detailed guides, see:
- **[Architecture Guide](docs/architecture.md)** - Entity development and framework design
- **[Configuration Reference](docs/configuration.md)** - Identity setup and customization
- **[Memory System](docs/memory.md)** - Custom memory and learning systems
- **[Troubleshooting](docs/troubleshooting.md)** - Common development issues

### Testing
```bash
poetry run pytest tests/
```

### Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and the clean architecture principles.

**📖 Complete Documentation**: All detailed guides are in the [docs/](docs/) folder:
- [Architecture](docs/architecture.md) | [Configuration](docs/configuration.md) | [Memory](docs/memory.md) | [Troubleshooting](docs/troubleshooting.md)
