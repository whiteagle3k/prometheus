# Troubleshooting Guide

## Installation Issues

### Model Download Problems
```bash
# Manually download Aletheia's model
./scripts/download_models.sh

# Verify model file exists and is correct size (~2.3GB)
ls -la models/phi-3-mini-3.8b-q4_k.gguf

# Check model integrity
poetry run python -c "
from aletheia.llm.local_llm import LocalLLM
llm = LocalLLM()
print('Model loaded successfully')
"
```

### Metal Acceleration Issues (macOS)
```bash
# Reinstall llama-cpp-python with Metal support
CMAKE_ARGS="-DLLAMA_METAL=on" poetry run pip install llama-cpp-python --force-reinstall --no-cache-dir

# Verify Metal acceleration is working
poetry run python -c "
from aletheia.llm.local_llm import LocalLLM
import asyncio
llm = LocalLLM()
info = asyncio.run(llm.get_model_info())
print('Metal supported:', 'metal' in str(info).lower())
"

# Check system Metal support
system_profiler SPDisplaysDataType | grep Metal
```

### Poetry/Python Environment Issues
```bash
# Reset poetry environment
poetry env remove python
poetry install

# Verify Python version (3.11+ required)
poetry run python --version

# Check for conflicting packages
poetry run pip list | grep llama
```

## Runtime Issues

### Memory and Conversation Problems
```bash
# Reset Aletheia's memory and conversation history
poetry run python -c "
from aletheia.agent.orchestrator import AletheiaAgent
import asyncio
agent = AletheiaAgent()
asyncio.run(agent.reset_memory())
print('Memory reset complete')
"

# Check Aletheia's current status
poetry run python -m aletheia.agent.orchestrator
# Then type: status
```

### Context and Reference Issues
If Aletheia loses context or doesn't understand references:

1. **Check conversation history**:
   ```bash
   # In Aletheia CLI, type: context
   ```

2. **Verify entity extraction**:
   ```python
   from aletheia.processing.extractors import EntityExtractor
   extractor = EntityExtractor()
   result = extractor.process("your problematic input")
   print("Entities:", result.data if result.success else "None")
   ```

3. **Test reference detection**:
   ```python
   from aletheia.processing.detectors import ReferenceDetector
   detector = ReferenceDetector()
   result = detector.process("your reference question")
   print("Has references:", result.data.get("has_references", False))
   ```

### External API Issues
```bash
# Test Anthropic API connectivity
poetry run python -c "
import os
from aletheia.llm.external_llm import ExternalLLMManager
manager = ExternalLLMManager()
print('Available providers:', manager.list_available_providers())
print('Anthropic key set:', bool(os.getenv('ANTHROPIC_API_KEY')))
"

# Test OpenAI API connectivity
poetry run python -c "
import os
print('OpenAI key set:', bool(os.getenv('OPENAI_API_KEY')))
"
```

### Performance Issues

#### Slow Response Times
1. **Check GPU acceleration**:
   ```bash
   # Verify Metal is being used
   poetry run python -c "
   from aletheia.llm.local_llm import LocalLLM
   llm = LocalLLM()
   # Look for 'Metal' or 'GPU' in output
   "
   ```

2. **Reduce context size** (if memory limited):
   ```env
   LOCAL_MODEL_CONTEXT_SIZE=2048  # Reduce from 4096
   LOCAL_MODEL_GPU_LAYERS=16      # Reduce if needed
   ```

3. **Monitor memory usage**:
   ```bash
   # Check system memory while running
   top -o MEM
   ```

#### High Memory Usage
```bash
# Reduce memory footprint
export LOCAL_MODEL_GPU_LAYERS=16  # Use fewer GPU layers
export MAX_MEMORY_ENTRIES=500     # Reduce memory entries

# Clear accumulated memory
poetry run python -c "
from aletheia.agent.orchestrator import AletheiaAgent
import asyncio
agent = AletheiaAgent()
asyncio.run(agent.reset_memory())
"
```

## Language and Grammar Issues

### Russian Grammar Problems
If Aletheia uses masculine forms instead of feminine:

1. **Check identity configuration**:
   ```bash
   # Verify feminine instructions in identity.json
   grep -A 5 "llm_instructions" aletheia/identity/identity.json
   ```

2. **Test language detection**:
   ```python
   text = "я готов помочь"  # Should be "готова" for female
   # Check if identity correctly specifies feminine forms
   ```

3. **Restart Aletheia** - Sometimes model state needs refresh

### Multilingual Context Issues
If context is lost when switching languages:

1. **Check language detection**:
   ```python
   from aletheia.agent.context_manager import ContextManager
   context = ContextManager()
   context.update_from_input("твой русский текст")
   print("Detected language:", context.last_user_language)
   ```

2. **Verify translation coverage**:
   ```bash
   # Check if all necessary phrases are translated
   grep -r "translations" aletheia/identity/identity.json
   ```

## Error Messages

### Common Error Solutions

#### `ModuleNotFoundError: No module named 'llama_cpp'`
```bash
CMAKE_ARGS="-DLLAMA_METAL=on" poetry install
```

#### `FileNotFoundError: [Errno 2] No such file or directory: 'models/...'`
```bash
./scripts/download_models.sh
```

#### `ImportError: No module named 'chromadb'`
```bash
poetry install --extras all
```

#### `ValueError: Failed to load model`
```bash
# Check model file integrity
ls -la models/phi-3-mini-3.8b-q4_k.gguf
# Re-download if corrupted
rm models/phi-3-mini-3.8b-q4_k.gguf
./scripts/download_models.sh
```

#### Context building errors
```python
# Test context building manually
from aletheia.agent.orchestrator import AletheiaAgent
agent = AletheiaAgent()
context = agent._build_context_summary()
print("Context:", context)
```

## Debugging Tools

### Enable Debug Logging
```env
LOG_LEVEL=DEBUG
```

### Test Individual Components
```bash
# Test local LLM only
poetry run python -c "
from aletheia.llm.local_llm import LocalLLM
import asyncio
llm = LocalLLM()
result = asyncio.run(llm.generate('Hello, how are you?'))
print(result)
"

# Test processing pipeline
poetry run python -c "
from aletheia.processing.pipeline import create_context_analysis_pipeline
pipeline = create_context_analysis_pipeline()
result = pipeline.process('test input')
print(result)
"

# Test memory system
poetry run python -c "
from aletheia.memory.vector_store import VectorStore
import asyncio
store = VectorStore()
print('Memory count:', asyncio.run(store.get_memory_count()))
"
```

### Performance Profiling
```bash
# Profile memory usage
poetry run python -m memory_profiler -m aletheia.agent.orchestrator

# Profile execution time
poetry run python -m cProfile -m aletheia.agent.orchestrator
```

## Getting Help

### Collecting Debug Information
When reporting issues, include:

1. **System information**:
   ```bash
   uname -a
   poetry --version
   poetry run python --version
   ```

2. **Aletheia status**:
   ```bash
   poetry run python -m aletheia.agent.orchestrator
   # Type: status
   ```

3. **Error logs**:
   ```bash
   # Run with debug logging
   LOG_LEVEL=DEBUG poetry run python -m aletheia.agent.orchestrator
   ```

4. **Configuration**:
   ```bash
   # Check configuration (remove sensitive keys)
   cat .env | grep -v API_KEY
   ```

### Community Support
- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For usage questions and ideas
- **Documentation**: Check `docs/` for detailed guides

### Known Limitations
- **Apple Silicon only**: Currently optimized for M1/M2/M3 Macs
- **Memory requirements**: 16GB+ RAM recommended
- **Model size**: Large model files (~2.3GB) required
- **Context windows**: Limited by local model capabilities
- **External API costs**: Usage-based pricing for external consultations 