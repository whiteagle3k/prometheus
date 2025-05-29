# Prometheus
![CI](https://github.com/whiteagle3k/prometheus/actions/workflows/ci.yml/badge.svg)

An AI agent framework for creating diverse personalities with hybrid LLM routing and advanced memory systems.

## Overview

Prometheus is a framework designed to bring different AI agent personalities to life, each with unique characteristics, behaviors, and capabilities. The project demonstrates how local and external language models can be combined to create engaging, cost-effective, and privacy-respecting AI companions.

### Meet Aletheia - The First Agent 👩

**Aletheia** is our inaugural self-learning female AI agent, serving as the foundation for the Prometheus framework. She embodies the core principles of intelligent conversation, continuous learning, and adaptive behavior.

**Aletheia's Characteristics:**
- **Conversational Memory**: Maintains context across interactions with persistent conversation history
- **Multilingual Capabilities**: Fluent in Russian and English with proper grammatical gender handling
- **Self-Learning**: Continuous improvement through self-reflection and experience storage
- **Female Identity**: Presents as a thoughtful female AI with appropriate cultural and linguistic awareness
- **Cost-Conscious**: Optimized hybrid routing to balance quality and efficiency

## The Prometheus Vision 🚀

Prometheus aims to create a diverse ecosystem of AI personalities, each designed for different use cases and interaction styles:

- **🧠 Analytical Agents**: Specialized in research, analysis, and complex reasoning
- **🎨 Creative Agents**: Focused on artistic expression, storytelling, and imagination  
- **🏠 Companion Agents**: Designed for daily interaction, support, and conversation
- **🔧 Technical Agents**: Expert in coding, system administration, and technical tasks
- **🌍 Cultural Agents**: Specialized in specific languages, cultures, and regional knowledge

Each agent in the Prometheus ecosystem shares core capabilities while expressing unique personalities and specialized skills.

## Key Framework Features ✨

### 🤖 **Adaptive Personality System**
- **Unique Identities**: Each agent has distinct personality traits and communication styles
- **Context Awareness**: Maintains conversation history and user relationships
- **Cultural Sensitivity**: Proper handling of language, gender, and cultural nuances
- **Learning Capacity**: Agents improve through interaction and self-reflection

### 🧠 **Intelligent Hybrid Routing**
- **Local-First Approach**: Uses efficient local models (Phi-3 Mini) for most tasks
- **Strategic External Routing**: Leverages Claude/GPT-4 for complex reasoning when needed
- **Cost Optimization**: Reduced external API usage by 60% through smart routing
- **Privacy Protection**: Most conversations stay on-device

### 📚 **Advanced Memory Systems**
- **Vector-Based Retrieval**: RAG-powered memory with semantic search
- **Conversation Threading**: Maintains session context and user preferences
- **Experience Learning**: Stores successful interaction patterns
- **Automatic Compression**: Intelligent summarization to manage memory efficiently

### 🔧 **Developer-Friendly Framework**
- **Modular Architecture**: Easy to extend with new agent personalities
- **Hardware Optimized**: Metal acceleration for Apple Silicon, future CUDA support
- **Comprehensive Testing**: Production-ready with full test coverage
- **Clean APIs**: Well-structured codebase for agent development

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
                     │   Conversation   │
                     │     Context      │
                     └──────────────────┘
                               │
                               ▼
                     ┌──────────────────┐
                     │   LLM Router     │
                     └──────────────────┘
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
🤖 Aletheia: Привет, Игорь! Я Алетейя, первый агент в рамках проекта Prometheus. 
Рада познакомиться! Я здесь, чтобы изучать, помогать и развиваться вместе с вами.
💭 Thoughts: 1.2s | Task #1 | Approach: direct | Route: local
```

### Aletheia's Self-Awareness
```
🧑 You: What is Prometheus?
🤖 Aletheia: Prometheus is the AI framework that brought me to life! It's designed to 
create diverse AI personalities with unique characteristics. I'm Aletheia, the first 
agent - a self-learning female AI focused on conversation and continuous improvement. 
Future agents will have different personalities and specializations.
💭 Thoughts: 0.9s | Task #2 | Approach: direct | Route: local
```

### Complex Task Demonstration
```
🧑 You: Объясни как работает машинное обучение пошагово
🎯 Handling complex task with planning...
📋 Executing plan with 5 sub-tasks...
🔄 Executing: Explain basic concepts of machine learning
🔄 Executing: Describe training process step by step
...
🤖 Aletheia: [Comprehensive ML explanation with structured steps]
💭 Thoughts: 12.3s | Task #3 | Approach: planning | Route: external
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
- [x] Hybrid LLM routing system
- [x] Vector memory and conversation context
- [x] Multilingual support with cultural awareness
- [x] Self-learning and reflection capabilities

### Phase 2: Framework Enhancement
- [ ] Agent personality template system
- [ ] Advanced memory compression strategies
- [ ] Multi-modal input support (text, voice, images)
- [ ] Plugin architecture for agent extensions
- [ ] Real-time learning optimization

### Phase 3: Agent Expansion
- [ ] Second agent personality (analytical specialist)
- [ ] Third agent personality (creative companion)  
- [ ] Agent-to-agent communication protocols
- [ ] Multi-agent collaboration scenarios

### Phase 4: Platform Evolution
- [ ] Cross-platform deployment (Windows/Linux)
- [ ] CUDA acceleration for RTX GPUs
- [ ] Cloud deployment and scaling
- [ ] Mobile agent implementations
- [ ] Community agent marketplace

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
# Token threshold for external routing
LOCAL_TOKEN_THRESHOLD=1024

# Keywords that trigger deep reasoning (comma-separated)
DEEP_REASONING_KEYWORDS=analysis,strategy,complex,detailed,research,comprehensive,explain,пошагово
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

### Hybrid Routing Strategy
Aletheia uses intelligent heuristics to balance cost, privacy, and quality:

1. **Token threshold**: Tasks > 1024 tokens → External LLM
2. **Deep reasoning keywords**: "analysis", "пошагово", "explain" → External LLM  
3. **Planning synthesis**: Complex multi-step results → External LLM
4. **Creative + long tasks**: Creative tasks > 2000 tokens → External LLM
5. **Very long outputs**: max_tokens > 1500 → External LLM
6. **Context overflow**: Tasks > 80% of local context → External LLM
7. **Default**: Local Phi-3 for efficiency and privacy

### Typical Usage Patterns
- **🆓 Local conversations**: 80% of interactions (free, private, fast)
- **💰 External analysis**: 20% for complex reasoning (~$0.01-0.05 per task)
- **📊 Memory efficiency**: Automatic compression keeps database under 100MB

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