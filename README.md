# Prometheus ✨
![CI](https://github.com/whiteagle3k/prometheus/actions/workflows/ci.yml/badge.svg)

Entity-based AI framework with clean architecture, **Fast LLM routing intelligence**, and robust cross-LLM context coordination.

## Why Prometheus?

- **Entity-based Design**: Clean separation between framework core and agent implementations
- **Fast LLM Routing Oracle**: Unbiased routing decisions with context isolation
- **Cross-LLM Context Coordination**: Seamless context flow between utility, local, and external models
- **Triple-Model Architecture**: Fast routing model + local reasoning + external consultation → optimal intelligence
- **Cost-effective**: Local "brain" handles 85% of conversations → cheap and private
- **Context Isolation**: Zero contamination between routing decisions
- **Clean architecture**: No coupling between core framework and specific entities
- **English-first system**: Consistent internal language with multilingual responses
- **Robust parsing**: Clean responses without internal field contamination

## Meet Aletheia 👩

Aletheia is our first autonomous AI entity - a thoughtful research assistant with:
- **Entity-based**: Built using the generic Prometheus framework
- **Smart Routing**: Fast LLM oracle makes unbiased LOCAL vs EXTERNAL decisions
- **Context-aware**: Perfect memory of conversations with zero context leakage
- **Multilingual**: Fluent Russian and English with proper feminine grammar forms
- **Self-aware**: Knows when to ask external experts for help
- **Learning**: Improves through reflection and experience
- **Personal**: Remembers user data and provides personalized responses
- **Clean responses**: Professional output without technical contamination

## Enhanced Architecture with Fast LLM Routing

```
    User Query
        │
        ▼
┌──────────────────┐    ┌─────────────────────┐
│   Fast LLM       │───▶│   LLM Router        │
│   (phi-3-mini)   │    │   (Decision Maker)  │
│   • Independent  │    │                     │
│   • Context-Free │    │   LOCAL ←→ EXTERNAL │
│   • Unbiased    │    │                     │
└──────────────────┘    └─────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │   Local LLM  │ │ External LLM │ │   Memory     │
            │  (Phi-3-M)   │ │  (OpenAI)    │ │   System     │
            │              │ │              │ │              │
            │ Context ✓    │ │ Context ✓    │ │ Context ✓    │
            └──────────────┘ └──────────────┘ └──────────────┘
                                  │
                                  ▼
                            Clean Response
                         (No Contamination)
```

## Core Features

### 🎯 Fast LLM Routing Intelligence
- **Unbiased Routing Oracle**: Dedicated Fast LLM (phi-3-mini) makes routing decisions
- **Context Isolation**: Each routing decision is independent with zero contamination
- **Smart Decision Making**: LOCAL for conversations, EXTERNAL for scientific topics
- **Performance Optimized**: 12 GPU layers, 2048 context, fast classification
- **Fallback Robustness**: Rule-based routing when Fast LLM unavailable

### 🔄 Cross-LLM Context Coordination
- **Seamless Context Flow**: Clean context passing between all LLM components
- **Zero Context Leakage**: Routing decisions don't contaminate each other
- **Memory Integration**: Context preserved across conversations and sessions
- **User Profile Continuity**: Personal data flows correctly through all components
- **Clean Context Preparation**: Focused context extraction for external consultations

### 🏗️ Clean Architecture
- **Entity-based Design**: Autonomous entities with their own identities
- **Generic Core**: Reusable components work with any entity configuration
- **Separation of Concerns**: Core framework + entity implementations
- **No Coupling**: Framework components don't know about specific entities
- **Dependency Injection**: Identity config passed to core components

### 🧠 Intelligence & Memory
- **Triple-Model System**: Routing (phi-3-mini) + Local (Phi-3-M) + External (OpenAI)
- **Generic LocalLLM**: Works with any entity's identity configuration
- **English-first System**: Consistent internal language, multilingual responses
- **Meta-cognitive Routing**: Independent assessment for smart LLM selection  
- **Vector Memory**: RAG-powered conversation history with semantic filtering
- **User Profiles**: Automatic extraction and storage of personal data

### 💬 Conversation & Context
- **Perfect Context Flow**: Zero contamination between routing and content generation
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
./scripts/download_models.sh  # Downloads all required models

# Start Aletheia entity
poetry run python prometheus.py aletheia

# Alternative: Direct Python execution
python prometheus.py aletheia
```

Once running, you can interact with Aletheia in natural language:
```
🤖 Aletheia: Привет! Я Алетейя, готова помочь. Как дела?
🧑 You: расскажи про квантовую механику
🔧 Fast LLM routing: EXTERNAL (scientific topic)
🌐 Router: External LLM selected
🤖 Aletheia: [Expert consultation, then personalized response with feminine forms]
```

## Documentation

For detailed information, see our comprehensive documentation:

### 📚 Core Documentation
- **[Architecture Guide](docs/architecture.md)** - Fast LLM routing, context coordination, entity system
- **[Memory System](docs/memory.md)** - Vector storage, user profiles, context management
- **[Configuration Reference](docs/configuration.md)** - Identity setup, utility model config, performance tuning
- **[Troubleshooting](docs/troubleshooting.md)** - Context contamination, routing issues, debugging

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
Each entity has its own identity configuration with dual-model support:
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
    "performance_config": {
      "gpu_layers": 40,
      "context_size": 8192
    },
    "utility_performance_config": {
      "gpu_layers": 12,
      "context_size": 2048
    }
  },
  "routing_threshold": 1024,
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
- **Recommended**: 32GB+ RAM for optimal triple-model performance
- **Storage**: ~12GB (all models + data)

## Usage Examples

### Fast LLM Routing in Action
```
🧑 You: что такое Сфера Дайсона?

🔧 Fast LLM: Making routing decision...
🔧 Fast LLM routing: EXTERNAL (confidence: high, complexity: scientific)
🔧 Reasoning: Scientific principle explanation
🌐 Router: External LLM selected
📡 Consulting external: openai
📋 Consultation received: 697 chars analysis, 5 memory points

🤖 Aletheia: Сфера Дайсона — это гипотетическое масштабное сооружение...
💭 Total: 17.0s | LLM: 14.7s | Route: External
```

### Context Preservation Across Interactions
```
🧑 You: Меня зовут Игорь
🤖 Aletheia: Приятно познакомиться, Игорь!

🧑 You: помнишь как меня зовут?
🔧 Fast LLM routing: LOCAL (confidence: high, complexity: simple)
🤖 Aletheia: Конечно, Игорь, я помню. Я рада помогать тебе.
✅ Context preserved: Zero contamination, perfect memory
```

### Clean Cross-LLM Context Flow
```
🧑 You: объясни принцип работы теплового двигателя
🔧 Fast LLM routing: EXTERNAL (scientific complexity)
📡 External consultation with user context
🤖 Aletheia: [Technical explanation in Russian with feminine forms]
✅ Clean response: No field contamination, proper context flow
```

### Debug Transparency
```
🔧 Utility model: Classifying query for memory filtering...
🔧 Query categorized as: technical
📂 Found 2 memories, filtering for relevance...
🔧 Fast LLM: Making routing decision...
🔧 Fast LLM routing: LOCAL (confidence: high, complexity: simple)
🎯 Router: Local LLM selected
🔧 LocalLLM: Using English system instructions
🔧 LocalLLM: Generating Russian response
💭 Total: 13.3s | LLM: 10.5s | No context contamination
✅ Clean response: No technical contamination
```

## CLI Commands

- `quit` - Exit gracefully
- `status` - Show entity and framework diagnostics
- `test` - Run comprehensive framework tests

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
