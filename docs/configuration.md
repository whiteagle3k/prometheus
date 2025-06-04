# Configuration Reference

## Overview

Prometheus uses entity-based configuration where each autonomous agent has its own identity file containing personality, model settings, and behavioral parameters. The framework supports **dual-model configuration** with separate settings for the main reasoning model and the Fast LLM routing oracle.

## Identity Configuration Structure

### Basic Structure
```json
{
  "meta": {
    "snapshot_id": "unique-id",
    "created_at": "timestamp",
    "version": "0.4.0"
  },
  "name": "EntityName",
  "primary_language": "en",
  "supported_languages": ["en", "ru"],
  "identity": { ... },
  "module_paths": { ... },
  "external_llms": { ... },
  "routing_configuration": { ... }
}
```

## Core Configuration Sections

### Entity Identity
```json
{
  "identity": {
    "summary": "Brief description of the entity's role and purpose",
    "personality": [
      "Key personality trait 1",
      "Key personality trait 2",
      "Uses appropriate language forms when needed"
    ]
  },
  "core_values": [
    "Honesty and transparency",
    "Evidence-based reasoning"
  ],
  "goals": [
    "Primary objective",
    "Secondary objective"
  ],
  "llm_instructions": "System prompt template for the entity. IMPORTANT: When responding in Russian, always use feminine language forms: готова (not готов), рада (not рад)..."
}
```

### Model Configuration
The framework supports **dual-model architecture** with separate configuration for reasoning and routing:

```json
{
  "module_paths": {
    "local_llm_binary": "models/llama.cpp/build/bin/llama",
    "local_model_gguf": "models/Phi-3-medium-4k-instruct-Q4_K_M.gguf",
    "utility_model_gguf": "models/phi-3-mini-3.8b-q4_k.gguf",
    "memory_dir": "storage/chroma",
    
    "performance_config": {
      "gpu_layers": 40,
      "context_size": 8192,
      "batch_size": 512,
      "threads": 8
    },
    
    "utility_performance_config": {
      "gpu_layers": 12,
      "context_size": 2048,
      "batch_size": 256,
      "threads": 4
    }
  },
  "routing_threshold": 1024
}
```

#### Performance Configuration Options

**Main Model (Local LLM)**:
- `gpu_layers`: Number of layers to run on GPU (0-40 for Phi-3-medium)
- `context_size`: Maximum context window (recommended: 8192)
- `batch_size`: Processing batch size (recommended: 512)
- `threads`: CPU threads when not using GPU (recommended: 8)

**Utility Model (Fast LLM)**:
- `gpu_layers`: GPU layers for routing model (recommended: 12)
- `context_size`: Context for routing decisions (recommended: 2048)
- `batch_size`: Batch size for fast processing (recommended: 256)
- `threads`: CPU threads for utility tasks (recommended: 4)

**Routing Configuration**:
- `routing_threshold`: Token limit before forcing external LLM (recommended: 1024)

### External LLM Configuration
```json
{
  "external_llms": {
    "primary_provider": "openai",
    "fallback_provider": "anthropic",
    "providers": {
      "openai": {
        "enabled": true,
        "model": "gpt-4.1-mini",
        "max_tokens_default": 1000,
        "temperature_default": 0.7,
        "cost_per_1k_input": 0.0015,
        "cost_per_1k_output": 0.006,
        "context_size": 128000,
        "use_for": ["technical_analysis", "detailed_explanations", "factual_questions"]
      },
      "anthropic": {
        "enabled": false,
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens_default": 1000,
        "temperature_default": 0.7,
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
        "context_size": 200000,
        "use_for": ["creative_tasks", "complex_reasoning", "analysis"]
      }
    },
    "routing_preferences": {
      "prefer_local": true,
      "external_threshold_tokens": 1024,
      "cost_optimization": true,
      "max_cost_per_query": 0.05
    }
  }
}
```

### Routing Configuration
Configure how the Fast LLM routing oracle makes decisions:

```json
{
  "routing_configuration": {
    "planning_indicators": [
      "step by step", "пошагово", "explain how to", "объясни как"
    ],
    "simple_conversation": [
      "привет", "hello", "как дела", "how are you"
    ],
    "dismissive_phrases": [
      "нет", "no", "хорошо", "спасибо"
    ]
  },
  "operational_guidelines": {
    "routing_policy": {
      "description": "90% local, external only for high complexity",
      "thresholds": {
        "max_tokens_local": 1024,
        "requires_deep_reasoning": true,
        "factual_question_min_words": 5
      }
    }
  }
}
```

## Hardware-Specific Configuration

### Apple Silicon (M1/M2/M3)
Optimized configuration for Metal acceleration:

```json
{
  "performance_config": {
    "gpu_layers": 40,
    "context_size": 8192,
    "batch_size": 512,
    "threads": 8
  },
  "utility_performance_config": {
    "gpu_layers": 12,
    "context_size": 2048,
    "batch_size": 256,
    "threads": 4
  }
}
```

### NVIDIA GPU Systems
Configuration for CUDA acceleration:

```json
{
  "performance_config": {
    "gpu_layers": 35,
    "context_size": 8192,
    "batch_size": 1024,
    "threads": 12
  },
  "utility_performance_config": {
    "gpu_layers": 10,
    "context_size": 2048,
    "batch_size": 512,
    "threads": 6
  }
}
```

### CPU-Only Systems
Configuration for systems without GPU acceleration:

```json
{
  "performance_config": {
    "gpu_layers": 0,
    "context_size": 4096,
    "batch_size": 256,
    "threads": 16
  },
  "utility_performance_config": {
    "gpu_layers": 0,
    "context_size": 1024,
    "batch_size": 128,
    "threads": 8
  }
}
```

## Memory Configuration

### Vector Storage Settings
```json
{
  "memory_dir": "storage/chroma",
  "memory_management": {
    "storage": "ChromaDB (vector)",
    "summarisation": "TL;DR every 500 records by local LLM",
    "retention": "raw records > 30 days deleted after compression"
  }
}
```

### Conversation Management
```json
{
  "conversation_management": {
    "context_window_size": 3,
    "context_summary_max_length": 300,
    "reference_detection": {
      "enabled": true,
      "pronouns": ["it", "that", "это", "то"],
      "continuation_phrases": [
        "tell me more", "расскажи подробнее",
        "explain further", "детально"
      ]
    }
  }
}
```

## Language Configuration

### Multilingual Support
```json
{
  "primary_language": "en",
  "supported_languages": ["en", "ru"],
  "translations": {
    "ru": {
      "identity": {
        "summary": "Женский автономный исследователь-агент",
        "personality": [
          "Позиционирует себя как женский ИИ",
          "Использует соответствующие женские формы языка"
        ]
      },
      "greeting_templates": {
        "introduction": "Привет! Я {name}, {summary}. Чем могу помочь?",
        "casual": "Привет! Как дела?",
        "professional": "Здравствуйте! Я {name}, готова помочь."
      }
    }
  }
}
```

## Environment Variables

### Required Environment Variables
```bash
# OpenAI API access (if using external LLMs)
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic API access (optional)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Custom model paths
PROMETHEUS_MODEL_DIR=/path/to/models
PROMETHEUS_STORAGE_DIR=/path/to/storage
```

### Development Environment
```bash
# For development and testing
PROMETHEUS_DEBUG=true
PROMETHEUS_LOG_LEVEL=debug
PROMETHEUS_CACHE_DISABLED=true
```

## Performance Tuning

### Memory Usage Optimization
- **16GB RAM**: Use 12 GPU layers for utility model, 25 for main model
- **32GB RAM**: Use 12 GPU layers for utility model, 40 for main model  
- **64GB+ RAM**: Use 12 GPU layers for utility model, full model on GPU

### Speed vs Quality Trade-offs
- **Speed Priority**: Lower context size, fewer GPU layers, smaller batch
- **Quality Priority**: Higher context size, more GPU layers, larger batch
- **Balanced**: Default recommended settings

### Context Management
- **Routing Context**: Keep under 300 characters for fast decisions
- **Generation Context**: Full conversation history for quality responses
- **Memory Context**: Semantic filtering for relevance

## Configuration Examples

### Minimal Configuration
Basic setup for development:
```json
{
  "name": "TestAgent",
  "llm_instructions": "You are a helpful AI assistant.",
  "module_paths": {
    "local_model_gguf": "models/Phi-3-medium-4k-instruct-Q4_K_M.gguf",
    "utility_model_gguf": "models/phi-3-mini-3.8b-q4_k.gguf",
    "utility_performance_config": {
      "gpu_layers": 12,
      "context_size": 2048
    }
  }
}
```

### Production Configuration  
Full setup for production deployment:
```json
{
  "name": "ProductionAgent",
  "llm_instructions": "Detailed system instructions...",
  "module_paths": {
    "local_model_gguf": "models/Phi-3-medium-4k-instruct-Q4_K_M.gguf",
    "utility_model_gguf": "models/phi-3-mini-3.8b-q4_k.gguf",
    "performance_config": {
      "gpu_layers": 40,
      "context_size": 8192,
      "batch_size": 512,
      "threads": 8
    },
    "utility_performance_config": {
      "gpu_layers": 12,
      "context_size": 2048,
      "batch_size": 256,
      "threads": 4
    }
  },
  "external_llms": {
    "primary_provider": "openai",
    "providers": {
      "openai": {
        "enabled": true,
        "model": "gpt-4.1-mini"
      }
    }
  },
  "routing_threshold": 1024
}
```

## Validation and Testing

### Configuration Validation
The framework automatically validates configuration on startup:
- Required fields presence
- Model file existence  
- Hardware compatibility
- External API availability

### Testing Configuration
```bash
# Test entity configuration
poetry run python prometheus.py your_entity --validate

# Test routing configuration
poetry run python test_comprehensive.py

# Test external LLM connectivity
poetry run python -c "from core.llm.providers import ExternalLLMManager; print(ExternalLLMManager().test_connectivity())"
```

## Troubleshooting Configuration

### Common Issues
1. **Model not found**: Check file paths in `module_paths`
2. **Out of memory**: Reduce `gpu_layers` or `context_size`
3. **Slow routing**: Check `utility_performance_config` settings
4. **Context contamination**: Verify Fast LLM context isolation settings

### Debug Configuration
```json
{
  "debug": {
    "enable_detailed_logging": true,
    "show_routing_decisions": true,
    "show_context_flow": true,
    "performance_monitoring": true
  }
}
```

See [Troubleshooting Guide](troubleshooting.md) for detailed debugging information. 