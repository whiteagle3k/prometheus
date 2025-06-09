# Prometheus AI Framework

## Project Overview

Prometheus is a universal multi-entity AI framework designed to create, manage, and deploy specialized autonomous AI entities. The framework features ultra-fast routing, advanced memory management, and robust cross-LLM context coordination.

The project implements a self-evolving AI team featuring multiple autonomous agents:

1. **Aletheia** - Primary user-facing agent that handles initial queries
2. **Supervisor (Petrovich)** - Manages development tasks and coordinates between other agents
3. **Developer (Vasya)** - Implements code changes and technical solutions
4. **QA (Marina)** - Tests and verifies implementations

## Core Architecture

Prometheus uses a modular architecture with these key components:

### Entity System
- **BaseEntity** - Abstract base class for all AI entities
- **Entity Registration** - Dynamic discovery and loading of entities from `entities/{name}/` directories
- **Universal Registry** - Thread-safe entity management and lifecycle coordination

### Routing System
- **Fast Classification** - SmolLM2-135M model provides rapid query classification (~0.3s)
- **Rule-based Routing** - Near-instant decision making based on query characteristics
- **Route Targets** - LOCAL (Phi-3-medium) and EXTERNAL (OpenAI) models

### Memory System
- **Vector Store** - ChromaDB-based vector storage for semantic retrieval
- **Context Management** - User profiles, conversation history, and entity-specific memory
- **Memory Critique** - Self-assessment and optimization of stored knowledge

### External Tools (MCP)
- **Model Context Protocol** - Standardized interface for external tools
- **DirectMCPClient** - Custom client implementation bypassing SDK limitations
- **Tool Servers** - Filesystem, Git, Terminal, and Web operation capabilities

## Current State and Recent Changes

### Routing Enhancement (v0.7.1)
We recently addressed an issue where Aletheia wasn't properly delegating development tasks to the Supervisor agent. The key fixes included:

1. **Rule-based Routing Activation**: Set `self._use_rule_based_routing = True` in FastLLM
2. **Routing Policy Configuration**: Added `prefer_external: true` and `use_for_coding: true` in Aletheia's operational guidelines
3. **Enhanced Programming Task Detection**: Added keywords like "обертка", "wrapper", "timestamp" to improve detection

The workflow is now functioning correctly:
User → Aletheia → Supervisor → Developer/QA → results back to Aletheia

### Test System
The project includes multiple test suites:
- **API Tests**: Verify API endpoints and entity switching
- **Smoke Tests**: Basic functionality verification
- **Context Isolation Tests**: Ensure proper separation between different contexts
- **Singleton Tests**: Test entity registry functionality (temporarily skipped due to mocking issues)

## Key Files and Components

### Core Framework
- `core/base_entity.py` - Base entity definition with common functionality
- `core/llm/router.py` - LLM routing system for model selection
- `core/llm/fast_llm.py` - Utility model for classification and rapid operations
- `core/runtime/registry.py` - Entity registry for discovery and management

### Entities
- `entities/aletheia/__init__.py` - Aletheia entity implementation
- `entities/aletheia/identity/identity.json` - Aletheia configuration

### Tests
- `tests/test_api.py` - API endpoint tests
- `tests/test_smoke.py` - Basic functionality tests
- `tests/test_context_isolation.py` - Context management tests

## Development Workflow

When continuing development on this project, consider these aspects:

1. **Entity-Based Design**: All autonomous agents are implemented as separate entities
2. **Routing Configuration**: The routing system determines which model processes each query
3. **Test-Driven Development**: Ensure all changes are covered by appropriate tests
4. **Mock Testing**: When testing entity interactions, proper mocking is essential

## Current Challenges and TODOs

1. **Testing Framework**: The singleton tests need proper mocking to handle entity discovery
2. **Entity Interactions**: Further refinement of inter-entity communication may be needed
3. **Performance Optimization**: Continuous monitoring and improvement of routing performance
4. **Documentation**: Maintain updated docs as new features are implemented

## Getting Started for Development

1. Clone the repository and install dependencies using Poetry
2. Run tests to verify your environment: `poetry run pytest tests/`
3. Start the framework with `poetry run python prometheus.py api --entity aletheia`
4. Modify entity behaviors in their respective directories
5. Add new routing rules in `core/llm/router.py` as needed
6. Update identity configurations to adjust entity behaviors

## Configuration Guide

Entities are configured using identity files. The key parameters for Aletheia include:

```json
{
  "name": {
    "en": "Aletheia",
    "ru": "Алетейя"
  },
  "operational_guidelines": {
    "routing_policy": {
      "prefer_external": true,
      "use_for_coding": true
    }
  }
}
```

The `prefer_external` and `use_for_coding` parameters are particularly important for proper task delegation to external LLMs and the Supervisor agent.
