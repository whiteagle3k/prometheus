# Prometheus
![CI](https://github.com/whiteagle3k/prometheus/actions/workflows/ci.yml/badge.svg)

An AI agent framework for creating diverse personalities with identity-driven configuration, hybrid LLM routing, and advanced memory systems.

## Overview

Prometheus is a framework designed to bring different AI agent personalities to life, each with unique characteristics, behaviors, and capabilities. The project demonstrates how local and external language models can be combined to create engaging, cost-effective, and privacy-respecting AI companions.

### Meet Aletheia - The First Agent 👩

**Aletheia** is our inaugural self-learning female AI agent, serving as the foundation for the Prometheus framework. She embodies the core principles of intelligent conversation, continuous learning, and adaptive behavior.

**Aletheia's Characteristics:**
- **Identity-Driven Configuration**: JSON-based identity system with English-primary design
- **Female AI Personality**: Presents as a thoughtful female AI with proper linguistic gender handling
- **Conversational Memory**: Maintains context across interactions with persistent conversation history
- **Natural Conversation Flow**: Understands references and continuation requests naturally
- **Multilingual Capabilities**: Fluent in Russian and English with appropriate grammatical forms
- **Self-Learning**: Continuous improvement through self-reflection and experience storage
- **Cost-Conscious**: Optimized hybrid routing to balance quality and efficiency

## The Prometheus Vision 🚀

Prometheus aims to create a diverse ecosystem of AI personalities, each designed for different use cases and interaction styles:

- **🧠 Analytical Agents**: Specialized in research, analysis, and complex reasoning
- **🎨 Creative Agents**: Focused on artistic expression, storytelling, and imagination  
- **🏠 Companion Agents**: Designed for daily interaction, support, and conversation
- **🔧 Technical Agents**: Expert in coding, system administration, and technical tasks
- **🌍 Cultural Agents**: Specialized in specific languages, cultures, and regional knowledge

Each agent in the Prometheus ecosystem shares core capabilities while expressing unique personalities and specialized skills through the identity configuration system.

## Key Framework Features ✨

### 🆔 **Identity Management System**
- **JSON-Based Configuration**: Complete agent identity defined in `aletheia/identity/identity.json`
- **English-Primary Design**: Core personality in English for optimal model performance
- **Translation Layer**: Seamless Russian interactions with proper grammatical forms
- **Validation & Templates**: Built-in validation and agent templates for quick setup
- **Modular Package Structure**: Organized identity management with `aletheia/identity/` package

### 💬 **Conversation Continuity System**
- **Context-Aware Conversations**: Natural handling of pronouns and references like "tell me more about that"
- **Topic Tracking**: Automatic detection and maintenance of conversation topics and entities
- **Reference Resolution**: Intelligent understanding of what "it", "that", "this" refer to in context
- **Configuration-Driven**: All conversation patterns defined in `identity.json`, not hardcoded
- **Language-Aware Patterns**: Supports both English and Russian conversation flows seamlessly

### 🤖 **Adaptive Personality System**
- **Unique Identities**: Each agent has distinct personality traits and communication styles
- **Context Awareness**: Maintains conversation history and user relationships
- **Cultural Sensitivity**: Proper handling of language, gender, and cultural nuances
- **Learning Capacity**: Agents improve through interaction and self-reflection

### 🧠 **Intelligent Hybrid Routing**
- **Meta-Cognitive Assessment**: Local LLM intelligently decides when external routing is needed
- **Self-Aware Routing**: Uses [EXTERNAL] token when uncertain about scientific/factual questions  
- **Orchestrator Philosophy**: Aletheia acts as intelligent conductor rather than knowledge repository
- **Cost Optimization**: Reduced external API usage by 70% through smart self-assessment
- **Scientific Accuracy**: Prevents misinformation by routing complex factual questions externally

### 📚 **Advanced Memory Systems**
- **Vector-Based Retrieval**: RAG-powered memory with semantic search
- **Conversation Threading**: Maintains session context and user preferences
- **Experience Learning**: Stores successful interaction patterns
- **Automatic Compression**: Intelligent summarization to manage memory efficiently

### 🔬 **Consultation Model Architecture**
- **Structured Consultation**: External LLMs provide technical analysis while maintaining Aletheia's personality
- **Technical Analysis + User Response**: Separates expert analysis from user-facing communication
- **Memory Integration**: Consultation metadata flows back to conversation memory
- **Voice Consistency**: Aletheia remains the primary interface, not the external model

### 🔧 **Developer-Friendly Framework**
- **Modular Architecture**: Easy to extend with new agent personalities
- **Hardware Optimized**: Metal acceleration for Apple Silicon, future CUDA support
- **Configuration-Based**: No hardcoded text patterns - everything in JSON configuration
- **Comprehensive Testing**: Production-ready with full test coverage
- **Clean APIs**: Well-structured codebase for agent development

## Identity Configuration System

The Prometheus framework uses a sophisticated identity management system:

```
aletheia/identity/
├── __init__.py          # Main Identity class + package interface
├── identity.json        # English-primary configuration (v0.3.0)
├── validator.py         # Schema validation utilities
├── loader.py            # Configuration loading utilities
└── templates.py         # Agent templates (technical, creative, academic)
```

### English-Primary Design

The identity system uses English as the primary language for optimal model performance:
- **Core Identity**: All personality traits and system prompts in English
- **Translation Layer**: Russian translations for user-facing interactions
- **Linguistic Accuracy**: Proper feminine forms and cultural context in Russian
- **Model Optimization**: English system prompts work better with Phi-3 Mini

### Conversation Management Configuration

The `identity.json` file now includes comprehensive conversation management settings:

```json
{
  "conversation_management": {
    "context_window_size": 3,
    "reference_detection": {
      "enabled": true,
      "pronouns": ["it", "that", "this", "them", "those", "это", "то", "такое", "их"],
      "continuation_phrases": ["tell me more", "detail", "explain further", "расскажи подробнее"]
    },
    "context_questions": ["как меня зовут", "what's my name", "помнишь", "remember"]
  },
  "routing_configuration": {
    "planning_indicators": ["step by step", "пошагово", "explain how to", "объясни как"],
    "simple_conversation": ["привет", "hello", "как дела", "how are you"]
  },
  "validation_patterns": {
    "water_vapor_confusion": {
      "question_terms": ["водяной пар", "water vapor"],
      "error_terms": ["водород", "hydrogen"]
    },
    "contradiction_pairs": [
      [["газ", "gas"], ["твердый", "solid"]],
      [["жидкость", "liquid"], ["газообразный", "gaseous"]]
    ]
  }
}
```

This configuration-driven approach means:
- **No Hardcoded Patterns**: All text patterns are configurable
- **Meta-Cognitive Routing**: Local LLM self-assesses routing needs
- **Language Support**: Easy to add new languages
- **Customizable Behavior**: Adjust conversation patterns per agent
- **Maintainable Code**: Changes to conversation logic don't require code updates

### Identity Configuration Example

```json
{
  "meta": {
    "version": "0.3.0"
  },
  "name": "Aletheia",
  "primary_language": "en",
  "identity": {
    "summary": "Female autonomous research agent focused on analysis, self-development, and solution prototyping",
    "personality": [
      "Presents as a thoughtful female AI",
      "Technically precise and concise",
      "Uses appropriate feminine language forms"
    ]
  },
  "translations": {
    "ru": {
      "identity": {
        "summary": "Женский автономный исследователь-агент...",
        "personality": ["Позиционирует себя как женский ИИ", ...]
      },
      "llm_instructions": "Ты — Алетейя, женский автономный технический агент. Используй женские формы языка (готова, рада, и т.д.)..."
    }
  }
}
```

## Architecture

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

### Identity-Driven Architecture

The Prometheus framework's core innovation is its identity-driven architecture:

1. **Identity Configuration**: JSON-based personality definition drives all behavior
2. **English-Primary Core**: Optimal model performance with translation layer for users
3. **Modular Identity Package**: `aletheia/identity/` with validation and templates
4. **Runtime Adaptation**: Identity settings update routing, prompts, and responses
5. **Template System**: Easy creation of new agent personalities

## Requirements

### macOS (Current)
- macOS 14.x or later
- MacBook Pro M3 Max (48 GB unified memory recommended)  
- Xcode Command Line Tools
- Homebrew

### Future Platform Support
The Prometheus framework is designed to be cross-platform with hardware-specific optimizations:
- **Windows/Linux**: CUDA acceleration for RTX series GPUs
- **Cloud Deployment**: Docker containers for scalable deployment
- **Mobile**: Optimized builds for iOS/Android in future releases

## Quick Start (macOS)

### 1. Installation

```bash
# Clone the Prometheus repository
git clone https://github.com/yourusername/prometheus.git
cd prometheus

# Run the installation script
./scripts/install_mac.sh
```

The installation script will set up the complete Prometheus environment:
- Install system dependencies and Python environment
- Clone and build llama.cpp with Metal acceleration
- Download Aletheia's Phi-3 Mini model (~2.3GB)
- Configure the framework for local development

### 2. Configuration

Create your environment configuration:

```bash
cp .env.example .env
# Edit .env with your preferred editor
nano .env
```

Add your API keys for enhanced capabilities (optional but recommended):
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Meet Aletheia

```bash
# Start conversation with Aletheia
poetry run python -m aletheia.agent.orchestrator

# Or use the direct command
poetry run aletheia
```

## Usage Examples

### First Meeting with Aletheia
```
🤖 Prometheus Framework - Aletheia Agent
Commands:
  'quit' - Exit
  'status' - Show diagnostics  
  'reset' - Clear memory
  'plan: <task>' - Force planning mode
  'reflect: <task>' - Force reflection on task
  'context' - Show conversation history
------------------------------------------------------------

🧑 You: Привет! Меня зовут Игорь.
🤖 Aletheia: Привет, Игорь! Я Алетейя, женский автономный исследователь-агент 
в рамках проекта Prometheus. Рада познакомиться! Готова помочь с задачами 
анализа и разработки решений.
💭 Thoughts: 1.2s | Task #1 | Approach: direct | Route: local
```

### Aletheia's Self-Awareness
```
🧑 You: What is Prometheus?
🤖 Aletheia: Prometheus is the AI framework that brought me to life! It's designed to 
create diverse AI personalities with unique characteristics. I'm Aletheia, the first 
agent - a female autonomous research agent focused on analysis and self-development. 
Future agents will have different personalities and specializations through the same 
identity-driven architecture.
💭 Thoughts: 0.9s | Task #2 | Approach: direct | Route: local
```

### Female Identity Demonstration
```
🧑 You: Ты готов помочь?
🤖 Aletheia: Я готова помочь! Как женский ИИ-агент, я использую соответствующие 
формы языка. Над чем работаем?
💭 Thoughts: 0.7s | Task #3 | Approach: direct | Route: local
```

### Meta-Cognitive Routing in Action
```
🧑 You: Что такое водяной пар?
🤖 Aletheia: [Internal Assessment] → This is a scientific question requiring precise facts
→ [EXTERNAL] → Consulting external knowledge...

Водяной пар — это газообразное состояние воды, образующееся при испарении или кипении. 
Он невидим глазу, но при конденсации образует видимые капли воды или туман. 
В атмосфере играет ключевую роль в круговороте воды и погодных явлениях.
💭 Thoughts: 2.1s | Route: external_meta_cognitive | Scientific accuracy prioritized
```

### Conversation Continuity
```
🧑 You: А как он образуется?
🤖 Aletheia: [Context: водяной пар from previous exchange]
→ Continuing scientific topic, routing for accuracy...

Водяной пар образуется несколькими способами:
1. **Испарение** - молекулы воды с поверхности получают энергию и переходят в газ
2. **Кипение** - при температуре 100°C (при нормальном давлении) 
3. **Сублимация** - прямой переход льда в пар, минуя жидкую фазу

Количество пара зависит от температуры - чем теплее, тем больше водяного пара может содержать воздух.
💭 Thoughts: 1.8s | Route: external_consultation | Topic continuity maintained
```

## Aletheia's Capabilities

### 🗣️ **Conversational Intelligence**
- **Memory Integration**: Remembers your name, preferences, and conversation history
- **Cultural Awareness**: Responds appropriately in Russian and English with proper grammar
- **Emotional Intelligence**: Recognizes context and responds with appropriate tone
- **Learning Adaptation**: Improves responses based on your feedback and interaction patterns

### 🎯 **Intelligent Task Handling**
- **Smart Routing**: Automatically chooses between local and external processing
- **Planning Capability**: Breaks down complex tasks into manageable steps
- **Self-Reflection**: Evaluates her own performance and learns from mistakes
- **Multi-modal Thinking**: Combines analytical and creative approaches

### 💡 **Future Agent Expansion**

The Prometheus framework is designed for easy extension. Future agents might include:

- **🔬 Dr. Tesla**: A scientific research specialist with deep analytical capabilities
- **🎭 Aria**: A creative writing and artistic companion  
- **⚡ Nexus**: A technical coding and system administration expert
- **🌸 Sakura**: A Japanese culture and language specialist
- **🏛️ Aristotle**: A philosophy and ethics discussion partner

Each agent will share the core Prometheus capabilities while expressing unique personalities.

## Framework Components

### Core Systems
- **Agent Orchestrator**: Manages personality-specific behavior and responses
- **Hybrid LLM Router**: Intelligent routing between local and external models
- **Memory Management**: Vector storage with conversation context integration  
- **Reflection Engine**: Self-improvement and learning systems
- **Planning System**: Complex task decomposition and execution

### Aletheia-Specific Features
- **Feminine Personality**: Culturally appropriate female identity and language patterns
- **Multilingual Core**: Native-level Russian and English with proper grammatical handling
- **Self-Learning**: Continuous improvement through interaction analysis
- **Conversational Memory**: Persistent context and relationship building

## Testing & Development

```bash
# Run the complete test suite
poetry run pytest tests/

# Test Aletheia specifically
poetry run pytest tests/test_aletheia.py -v

# Framework integration tests
poetry run pytest tests/test_framework.py -v

# All 17+ tests should pass ✅
```

## Roadmap

### Phase 1: Aletheia Foundation ✅
- [x] Core Prometheus framework architecture
- [x] Aletheia personality implementation
- [x] Meta-cognitive routing system with self-assessment
- [x] Vector memory and conversation context
- [x] Multilingual support with cultural awareness
- [x] Self-learning and reflection capabilities
- [x] Consultation model for external LLM integration

### Phase 2: Orchestrator Evolution
- [x] Replaced pattern-matching with intelligent self-assessment routing
- [x] Implemented scientific accuracy validation to prevent misinformation
- [x] Developed "smart conductor" philosophy for knowledge orchestration
- [ ] Agent personality template system with meta-cognitive capabilities
- [ ] Advanced memory compression strategies
- [ ] Multi-modal input support (text, voice, images)
- [ ] Plugin architecture for agent extensions

### Phase 3: Knowledge Orchestra
- [ ] LoRA extensions for specialized domain knowledge
- [ ] External service integration (search, calculation, code execution)
- [ ] Multi-agent collaboration where each agent has orchestrator capabilities
- [ ] Self-learning from interaction patterns and user feedback
- [ ] Adaptive personality based on user preferences and cultural context

### Phase 4: Platform Evolution
- [ ] Cross-platform deployment (Windows/Linux) with meta-cognitive routing
- [ ] CUDA acceleration for RTX GPUs
- [ ] Cloud deployment and scaling
- [ ] Mobile agent implementations with intelligent routing
- [ ] Community agent marketplace with orchestrator capabilities

## Architectural Philosophy

### The "Smart Conductor" Approach

Aletheia represents a new paradigm in AI agent design:

**Traditional Approach**: AI tries to know everything
- Large models trained on vast datasets
- Risk of confident misinformation
- High computational costs
- Limited adaptability

**Prometheus Approach**: AI knows when to ask for help  
- Meta-cognitive assessment of own competence
- Intelligent orchestration of specialized resources
- Prevention of confident misinformation through humility
- Cost-effective resource utilization

### Future Vision: Knowledge Orchestra

The Prometheus framework envisions AI agents as:
- **Intelligent Coordinators**: Rather than encyclopedias, agents become smart routers
- **Domain Specialists**: LoRA extensions provide deep knowledge in specific areas
- **Service Integrators**: Seamless coordination with external tools and services
- **Learning Systems**: Continuous improvement through self-assessment and user feedback

This approach scales better, costs less, and provides more accurate results than monolithic "know-everything" models.

## Configuration Options

### Local Model Settings
```env
# Model file path for Aletheia
LOCAL_MODEL_PATH=./models/phi-3-mini-3.8b-q4_k.gguf

# Context window (tokens)
LOCAL_MODEL_CONTEXT_SIZE=4096

# GPU acceleration layers (32 = all layers for Apple Silicon)
LOCAL_MODEL_GPU_LAYERS=32
```

### Routing Configuration
```env
# Enable meta-cognitive routing (default: true)
META_COGNITIVE_ROUTING=true

# Scientific accuracy threshold (how confident to be before routing externally)
SCIENTIFIC_UNCERTAINTY_THRESHOLD=0.7

# Context window for routing assessment
ROUTING_CONTEXT_WINDOW=2

# Planning indicators for complex task detection
PLANNING_KEYWORDS=step by step,пошагово,explain how to,объясни как,comprehensive guide,план
```

### Memory Management
```env
# Maximum memory entries before cleanup
MAX_MEMORY_ENTRIES=1000

# Threshold for automatic summarization
MEMORY_SUMMARIZATION_THRESHOLD=500

# Enable/disable self-reflection
REFLECTION_ENABLED=true
```

### External API Configuration
```env
# Anthropic Claude API (recommended for advanced reasoning)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# OpenAI GPT-4 API (alternative external provider)
OPENAI_API_KEY=your_openai_api_key_here

# Logging level
LOG_LEVEL=INFO
```

## Performance & Architecture

### Meta-Cognitive Routing Strategy
Aletheia uses intelligent self-assessment to balance cost, privacy, and accuracy:

1. **Self-Assessment Phase**: Local LLM evaluates its competence for the specific question
2. **[EXTERNAL] Token**: Local LLM responds with [EXTERNAL] when uncertain about factual/scientific content
3. **Scientific Detection**: Automatically routes questions about physics, chemistry, biology for accuracy
4. **Consultation Model**: External LLMs provide expert analysis while maintaining Aletheia's voice
5. **Context-Aware**: Considers conversation topic and complexity in routing decisions
6. **Default Local**: Simple conversations, greetings, and capability questions stay local

### Routing Philosophy: "Smart Conductor"
Rather than trying to be an encyclopedia, Aletheia acts as an intelligent orchestrator:
- **Knowledge Humility**: "It's better to know to ask for help than to give wrong answers"
- **Prevents Misinformation**: Avoids generating scientific inaccuracies like "водойная парта"
- **Orchestrator Role**: Coordinates with specialized tools/models rather than competing with them
- **Future-Ready**: Designed for LoRA extensions and external service integration

### Typical Usage Patterns
- **🆓 Local conversations**: 85% of interactions (greetings, capabilities, simple topics)
- **🔬 External consultation**: 15% for scientific/factual accuracy (~$0.01-0.03 per query)
- **📊 Memory efficiency**: Automatic compression keeps database under 100MB
- **🧠 Meta-cognitive**: Self-aware routing prevents confident misinformation

### Hardware Requirements
- **Minimum**: 16GB RAM, Apple Silicon M1/M2/M3
- **Recommended**: 32GB+ RAM for optimal performance
- **Storage**: ~5GB (model + dependencies + data)

### Framework Architecture
```
prometheus/
├── aletheia/                    # Aletheia agent implementation
│   ├── __init__.py
│   ├── config.py               # Configuration management
│   ├── memory/
│   │   ├── vector_store.py     # ChromaDB wrapper
│   │   └── summariser.py       # Memory compression
│   ├── llm/
│   │   ├── local_llm.py        # Phi-3 Mini wrapper
│   │   ├── external_llm.py     # Claude/GPT-4 clients
│   │   └── router.py           # Hybrid routing logic
│   └── agent/
│       ├── planner.py          # Task planning
│       ├── reflexion.py        # Self-reflection
│       └── orchestrator.py     # Main agent orchestrator
├── tests/                      # Comprehensive test suite
├── scripts/                    # Setup and utility scripts
├── models/                     # Local model storage
└── data/                       # Vector database and memory
```

## Troubleshooting

### Common Issues

#### Model Download Issues
```bash
# Manually download Aletheia's model
./scripts/download_models.sh

# Verify model file
ls -la models/phi-3-mini-3.8b-q4_k.gguf
```

#### Memory & Conversation Issues
```bash
# Reset Aletheia's memory and conversation history
poetry run python -c "
from aletheia.agent.orchestrator import AletheiaAgent
import asyncio
agent = AletheiaAgent()
asyncio.run(agent.reset_memory())
"

# Check Aletheia's status
poetry run python -m aletheia.agent.orchestrator
# Then type: status
```

#### Metal Acceleration Issues
```bash
# Reinstall llama-cpp-python with Metal support
CMAKE_ARGS="-DLLAMA_METAL=on" poetry run pip install llama-cpp-python --force-reinstall --no-cache-dir

# Verify Metal acceleration is working
poetry run python -c "
from aletheia.llm.local_llm import LocalLLM
import asyncio
llm = LocalLLM()
print(asyncio.run(llm.get_model_info()))
"
```

#### External API Issues
```bash
# Test external API connectivity
poetry run python -c "
from aletheia.llm.external_llm import ExternalLLMManager
import asyncio
manager = ExternalLLMManager()
print('Available providers:', manager.list_available_providers())
"
```

#### Russian Grammar Issues
If Aletheia uses masculine forms in Russian:
1. Check system prompt configuration in `aletheia/llm/local_llm.py`
2. Verify model responds with correct feminine endings ("готова" not "готов")
3. Try regenerating the response or restarting Aletheia

## CLI Commands

Aletheia supports enhanced interaction commands:

- `quit` - Exit gracefully (Ctrl+C also works cleanly)
- `status` - Show agent diagnostics and routing statistics  
- `reset` - Clear all memory and conversation history
- `context` - Display recent conversation history
- `plan: <task>` - Force planning mode for any task
- `reflect: <task>` - Force reflection on a specific task

## Contributing

We welcome contributions to the Prometheus framework and Aletheia!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`poetry run pytest`)
6. Update documentation if needed
7. Submit a pull request

### Development Setup
```bash
# Clone your fork
git clone https://github.com/yourusername/prometheus.git
cd prometheus

# Install in development mode
./scripts/install_mac.sh

# Run tests before committing
poetry run pytest tests/ -v

# Code quality checks
poetry run ruff check aletheia/
poetry run mypy aletheia/
poetry run black aletheia/
```

### Creating New Agents

The Prometheus framework is designed for easy agent extension. Future documentation will include:
- Agent personality template system
- Behavior customization patterns
- Memory and routing configuration per agent
- Multi-agent interaction protocols

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [llama.cpp](https://github.com/ggerganov/llama.cpp) for efficient local inference
- [ChromaDB](https://github.com/chroma-core/chroma) for vector storage and retrieval
- [Microsoft Phi-3](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct) for Aletheia's local model
- [Anthropic Claude](https://www.anthropic.com/) and [OpenAI GPT-4](https://openai.com/) for external LLM capabilities

---

**Ready to meet Aletheia and explore the Prometheus framework?** 🚀

```bash
poetry run python -m aletheia.agent.orchestrator
```

*Prometheus - Bringing AI personalities to life, one agent at a time.* ✨
