# Troubleshooting Guide

## Overview

This guide covers common issues with the Prometheus framework, particularly focusing on **context contamination**, **Fast LLM routing problems**, and **cross-LLM coordination issues** that can arise in the advanced architecture.

## 🚀 Performance Optimization (v0.5.0)

### Problem: Slow Performance Despite Optimizations

**Symptoms**:
- Classification taking >1s instead of ~0.3s expected
- Routing decisions taking several seconds instead of instant
- System not using SmolLM2 model

**Solutions**:

1. **Verify SmolLM2 Installation**: Check if optimized model is downloaded:
```bash
ls -la models/SmolLM2-135M-Instruct-Q4_K_S.gguf
# Should show: ~97MB file
```

2. **Download SmolLM2 if Missing**:
```bash
./scripts/download_models.sh
# Or manually:
cd models/
wget https://huggingface.co/Triangle104/SmolLM2-135M-Instruct-Q4_K_S-GGUF/resolve/main/smollm2-135m-instruct-q4_k_s.gguf
mv smollm2-135m-instruct-q4_k_s.gguf SmolLM2-135M-Instruct-Q4_K_S.gguf
```

3. **Check Identity Configuration**: Verify entity uses SmolLM2:
```json
{
  "module_paths": {
    "utility_model_gguf": "models/SmolLM2-135M-Instruct-Q4_K_S.gguf",
    "utility_model_candidates": [
      "SmolLM2-135M-Instruct-Q4_K_S.gguf",
      "SmolLM2-360M-Instruct-Q4_K_M.gguf",
      "TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf"
    ]
  }
}
```

4. **Monitor Performance**: Check if optimizations are working:
```bash
poetry run python prometheus.py aletheia
🧑 You: status

# Should show:
📊 FastLLM Performance Summary:
  🚀 Rule-based routing: X calls (instant)
  📊 Model classification: X calls
  ⚡ Avg classification time: ~0.29s  # Target performance
```

### Problem: System Not Using Rule-Based Routing

**Symptoms**:
- Routing decisions still taking >1s
- No "rule-based routing" messages in logs
- Routing performance not improved

**Solutions**:

1. **Check FastLLM Configuration**: Verify rule-based routing enabled:
```python
# In FastLLM initialization
self._use_rule_based_routing = True  # Should be True by default
```

2. **Debug Routing Path**: Add debug logging:
```python
# In make_routing_decision method
if self._use_rule_based_routing:
    print("✅ Using optimized rule-based routing")
    result = self._optimized_rule_based_routing(query)
else:
    print("⚠️ Falling back to model-based routing")
```

3. **Force Rule-Based Mode**: If needed, explicitly enable:
```python
# In entity configuration or FastLLM init
fast_llm._use_rule_based_routing = True
```

### Problem: Large Model Being Used Instead of SmolLM2

**Symptoms**:
- Classification times >1s consistently
- High memory usage during utility operations
- System reports "large utility model" in logs

**Solutions**:

1. **Check Model Discovery**: Look for model loading messages:
```
🎯 Using configured utility model: SmolLM2-135M-Instruct-Q4_K_S.gguf (97.1MB)
# vs
🐌 Using large utility model: phi-3-mini-3.8b-q4_k.gguf (2.3GB) - expect slower performance
```

2. **Verify Model Priority**: Check utility model candidates order:
```json
{
  "utility_model_candidates": [
    "SmolLM2-135M-Instruct-Q4_K_S.gguf",  // First = highest priority
    "phi-3-mini-3.8b-q4_k.gguf"           // Fallback only
  ]
}
```

3. **Force Small Model**: Explicitly set utility model:
```json
{
  "module_paths": {
    "utility_model_gguf": "models/SmolLM2-135M-Instruct-Q4_K_S.gguf"
  }
}
```

### Problem: Poor Classification or Routing Accuracy

**Symptoms**:
- Simple queries routed to EXTERNAL incorrectly
- Conversational queries classified as "technical"
- System accuracy below expected performance

**Solutions**:

1. **Check Rule-Based Logic**: Verify keyword detection:
```python
# Test rule-based routing manually
test_queries = [
    "привет как дела",  # Should be LOCAL
    "объясни квантовую механику",  # Should be EXTERNAL  
    "как тебя зовут"  # Should be LOCAL
]

for query in test_queries:
    result = fast_llm._optimized_rule_based_routing(query)
    print(f"{query} -> {result['route']}")
```

2. **Update Keywords**: Enhance detection patterns:
```python
# In _optimized_rule_based_routing method
external_keywords = [
    # Add more scientific terms
    'physical', 'химический', 'biological', 'математический'
]

local_keywords = [
    # Add more conversational terms  
    'кто', 'what', 'когда', 'where'
]
```

3. **Test Classification Accuracy**: Verify model performance:
```python
# Test classification with SmolLM2
test_queries = [
    ("как дела", "conversational"),
    ("физика квантов", "technical"),
    ("меня зовут Игорь", "personal_data")
]

for query, expected in test_queries:
    result = await fast_llm.classify_query(query)
    print(f"'{query}' -> {result} (expected: {expected})")
```

## Legacy Context Contamination Issues

### Problem: Incorrect Routing Decisions Based on Previous Queries

**Note**: This issue is largely resolved in v0.5.0 with rule-based routing, but may still occur if model-based routing is used.

**Symptoms**:
- Fast LLM makes routing decisions that seem influenced by previous queries
- Simple query routed to EXTERNAL because of previous scientific topic
- Routing confidence doesn't match current query

**Updated Solutions for v0.5.0**:

1. **Use Rule-Based Routing** (Recommended):
```python
# Enable rule-based routing to eliminate context contamination
self._use_rule_based_routing = True
```

2. **If Using Model-Based Routing**: Ensure context isolation:
```python
# Stronger context separation in prompts
system_prompt = """You are a routing oracle. Judge this query INDEPENDENTLY.

CRITICAL: Completely ignore any previous queries or decisions.

Current query to route:"""
```

## Context Contamination Issues

### Problem: Incorrect Routing Decisions Based on Previous Queries

**Symptoms**:
- Fast LLM makes routing decisions that seem influenced by previous queries
- Example: Simple query routed to EXTERNAL because of previous scientific topic
- Routing confidence and reasoning doesn't match current query

**Example Problem**:
```
🧑 You: расскажи про Сферу Дайсона
🔧 Fast LLM routing: EXTERNAL (scientific topic) ✓

🧑 You: как тебя зовут?
🔧 Fast LLM routing: EXTERNAL (confidence: high, complexity: scientific)
🔧 Reasoning: Scientific principle explanation  ❌ WRONG!
```

**Root Cause**: Fast LLM context contamination where previous query context affects new routing decisions.

**Solutions**:

1. **Verify Context Reset**: Check if `_reset_model_context()` is working:
```python
# In FastLLM, verify reset methods are being called
async def make_routing_decision(self, query: str) -> dict:
    # This should be called first
    await self._reset_model_context()
    
    # Then make decision
    routing_result = await self.model(prompt, ...)
```

2. **Enable Debug Logging**: Add debugging to see reset attempts:
```python
async def _reset_model_context(self) -> None:
    print("🔄 Attempting Fast LLM context reset...")
    try:
        if hasattr(self.model, 'reset'):
            self.model.reset()
            print("✅ Model reset successful")
        # ... other reset methods
    except Exception as e:
        print(f"⚠️ Reset failed: {e}")
```

3. **Enhanced Prompt Isolation**: Use stronger context separation:
```python
system_prompt = """You are a routing oracle. 

CRITICAL: Judge this query INDEPENDENTLY. Completely ignore any previous queries, contexts, or decisions.

Only consider the current query below:"""
```

4. **Fallback to Rule-based Routing**: If Fast LLM continues to have issues:
```python
# Check routing consistency
def _validate_routing_decision(self, query: str, decision: dict) -> bool:
    # Simple validation
    if "привет" in query.lower() and decision['route'] == 'EXTERNAL':
        return False  # Obviously wrong
    return True
```

### Problem: Memory Context Bleeding Between Conversations

**Symptoms**:
- User information from previous sessions appears in new conversations
- Context window contains irrelevant historical data
- Memory retrieval returns wrong user profiles

**Solutions**:

1. **Check Memory Isolation**: Verify proper session management:
```python
# In memory system
async def get_relevant_memories(self, query: str, user_id: str = None):
    # Should filter by user_id
    if user_id:
        filter_criteria = {"user_id": user_id}
    else:
        filter_criteria = {}
```

2. **Clean Context Preparation**: Ensure context cleaning:
```python
def _prepare_clean_context(self, conversation_context: str) -> str:
    """Extract only relevant recent context."""
    if not conversation_context:
        return ""
    
    # Limit to recent exchanges only
    lines = conversation_context.strip().split('\n')
    recent_lines = lines[-4:]  # Only last 4 lines
    
    return '\n'.join(recent_lines)
```

## Fast LLM Routing Issues

### Problem: Slow Routing Decisions

**Symptoms**:
- Routing takes 5+ seconds
- High memory usage during routing
- System becomes unresponsive

**Solutions**:

1. **Check GPU Allocation**: Verify utility model configuration:
```json
{
  "utility_performance_config": {
    "gpu_layers": 12,     // Not too high
    "context_size": 2048, // Appropriate size
    "batch_size": 256,    // Reasonable batch
    "threads": 4          // Balanced
  }
}
```

2. **Monitor Resource Usage**: Add performance monitoring:
```python
import time
start_time = time.time()
routing_result = await self.utility_llm.make_routing_decision(query)
duration = time.time() - start_time

if duration > 2.0:
    print(f"⚠️ Slow routing: {duration:.1f}s")
```

3. **Reduce Context Size**: Limit routing context:
```python
# Keep routing context minimal
if len(routing_context) > 300:
    routing_context = routing_context[-300:]  # Last 300 chars only
```

### Problem: Fast LLM Model Not Loading

**Symptoms**:
- `Fast LLM routing failed` errors
- Falls back to rule-based routing constantly
- Model path errors in logs

**Solutions**:

1. **Verify Model Path**: Check utility model exists:
```python
utility_model_path = identity_config["module_paths"]["utility_model_gguf"]
if not Path(utility_model_path).exists():
    print(f"❌ Utility model not found: {utility_model_path}")
```

2. **Check Download**: Ensure both models downloaded:
```bash
ls -la models/
# Should show both:
# Phi-3-medium-4k-instruct-Q4_K_M.gguf  (main model)
# phi-3-mini-3.8b-q4_k.gguf            (utility model)
```

3. **Download Missing Model**:
```bash
cd models/
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf
mv Phi-3-mini-4k-instruct-q4.gguf phi-3-mini-3.8b-q4_k.gguf
```

### Problem: Inconsistent Routing Decisions

**Symptoms**:
- Same query gets different routing decisions
- LOCAL/EXTERNAL decisions seem random
- Low confidence in routing decisions

**Solutions**:

1. **Stabilize Temperature**: Use lower temperature for routing:
```python
result = self.model(
    formatted_prompt,
    max_tokens=80,
    temperature=0.1,  # Lower for consistency
    stop=["<|end|>"]
)
```

2. **Improve Prompt Structure**: Use clearer instructions:
```python
system_prompt = f"""You are a routing oracle. Decide if query needs LOCAL or EXTERNAL LLM.

RULES:
- LOCAL: Simple greetings, basic questions, conversations
- EXTERNAL: Scientific topics, complex explanations, technical details

Respond ONLY in JSON:
{{"route": "LOCAL", "confidence": "high", "reasoning": "simple greeting"}}

Query: {query}"""
```

3. **Add Validation**: Check decision consistency:
```python
def _validate_routing_decision(self, query: str, decision: dict) -> bool:
    route = decision.get('route', 'LOCAL')
    
    # Basic sanity checks
    if any(word in query.lower() for word in ['привет', 'hello', 'hi']):
        return route == 'LOCAL'
    
    if any(word in query.lower() for word in ['квантов', 'физик', 'quantum', 'physics']):
        return route == 'EXTERNAL'
    
    return True
```

## Cross-LLM Coordination Problems

### Problem: External LLM Context Not Preserved

**Symptoms**:
- External LLM doesn't receive conversation context
- User name not passed to external consultation
- Response lacks personalization

**Solutions**:

1. **Check Context Preparation**: Verify external prompt building:
```python
def _prepare_external_prompt(self, task: TaskContext) -> str:
    consultation_prompt = f"I am {self.identity_config['name']}..."
    
    # Add conversation context
    if task.conversation_context:
        consultation_prompt += f"\n\nCONVERSATION CONTEXT:\n{task.conversation_context}"
    
    consultation_prompt += f"\n\nQuestion: {task.prompt}"
    return consultation_prompt
```

2. **Verify Context Assembly**: Check task context creation:
```python
task_context = TaskContext(
    prompt=user_input,
    conversation_context=self.get_conversation_context(),  # This should exist
    user_name=self.get_current_user_name(),               # This should exist
    session_context={"user_profile": user_profile}        # This should exist
)
```

### Problem: Response Quality Degradation

**Symptoms**:
- Local responses become generic
- External responses lose entity personality
- Context not maintained across turns

**Solutions**:

1. **Verify Identity Injection**: Check if identity config is passed:
```python
# In BaseEntity initialization
router = LLMRouter(identity_config=self.identity_config)  # Must pass config
local_llm = LocalLLM(identity_config=self.identity_config)  # Must pass config
```

2. **Check System Prompt Generation**: Verify prompts use identity:
```python
def _get_system_prompt(self, language: str) -> str:
    if language == "ru":
        return self.identity_config["system_prompts"]["ru"]
    else:
        return self.identity_config["system_prompts"]["en"]
```

3. **Monitor Response Pipeline**: Add debugging to response generation:
```python
print(f"🔧 Using identity: {self.identity_config['name']}")
print(f"🔧 Language detected: {language}")
print(f"🔧 System prompt: {system_prompt[:100]}...")
```

## Memory System Issues

### Problem: Memory Not Retrieving Relevant Context

**Symptoms**:
- "No relevant memories found" despite previous conversations
- User profile data not retrieved
- Context seems lost between sessions

**Solutions**:

1. **Check Memory Storage**: Verify memories are being saved:
```python
# After conversation, check if memory was stored
stored_memories = await self.memory_manager.search_memories("test query", limit=5)
print(f"📂 Found {len(stored_memories)} memories")
```

2. **Test Memory Retrieval**: Debug memory search:
```python
# Test semantic search
query = "как меня зовут"
memories = await self.memory_manager.search_memories(query)
for memory in memories:
    print(f"Memory: {memory['content'][:50]}... (score: {memory.get('score', 0):.3f})")
```

3. **Verify User Profile Storage**: Check profile directory:
```bash
ls -la storage/user_profiles/
# Should contain JSON files with user data
```

### Problem: Memory Storage Errors

**Symptoms**:
- "ChromaDB connection failed" errors
- Memory directory not created
- Persistence errors

**Solutions**:

1. **Check Directory Permissions**:
```bash
mkdir -p storage/chroma
chmod 755 storage/chroma
```

2. **Test ChromaDB Directly**:
```python
import chromadb
client = chromadb.PersistentClient(path="storage/chroma")
collection = client.get_or_create_collection("test")
print("ChromaDB working correctly")
```

3. **Reset Memory Storage**:
```bash
# If corrupted, reset memory
rm -rf storage/chroma
mkdir -p storage/chroma
```

## Performance Issues

### Problem: High Memory Usage

**Symptoms**:
- System uses 20GB+ RAM
- Models loading slowly
- Out of memory errors

**Solutions**:

1. **Reduce GPU Layers**: Lower memory usage:
```json
{
  "performance_config": {
    "gpu_layers": 25,     // Reduce from 40
    "context_size": 4096  // Reduce from 8192
  },
  "utility_performance_config": {
    "gpu_layers": 8,      // Reduce from 12
    "context_size": 1024  // Reduce from 2048
  }
}
```

2. **Enable Model Unloading**: Free memory when not in use:
```python
# After long idle periods
await self.local_llm.unload()
```

### Problem: Slow Response Times

**Symptoms**:
- Responses take 30+ seconds
- High CPU usage
- System becomes unresponsive

**Solutions**:

1. **Optimize Hardware Settings**: Match your system capabilities:
```bash
# Check system resources
system_profiler SPHardwareDataType | grep "Total Number of Cores"
sysctl hw.memsize
```

2. **Profile Performance**: Add timing to identify bottlenecks:
```python
import time

start_time = time.time()
routing_time = time.time()
routing_result = await self.router.route_task(task)
routing_duration = time.time() - routing_time

generation_time = time.time()
response = await self.generate_response(task)
generation_duration = time.time() - generation_time

total_duration = time.time() - start_time

print(f"⏱️  Routing: {routing_duration:.1f}s, Generation: {generation_duration:.1f}s, Total: {total_duration:.1f}s")
```

## Debug Output and Monitoring

### Enable Comprehensive Debugging

1. **Framework Debug Mode**:
```bash
export PROMETHEUS_DEBUG=true
export PROMETHEUS_LOG_LEVEL=debug
```

2. **Component-Specific Debugging**:
```python
# In router.py
print(f"🔧 Fast LLM routing: {route} (confidence: {confidence})")
print(f"🔧 Reasoning: {reasoning}")

# In local_llm.py  
print(f"🔧 LocalLLM: Using {language} system instructions")
print(f"🔧 LocalLLM: Generating {user_language} response")

# In memory system
print(f"📂 Found {len(memories)} memories, filtering for relevance...")
```

3. **Performance Monitoring**:
```python
# Add to all major operations
execution_time = asyncio.get_event_loop().time() - start_time
print(f"💭 Total: {execution_time:.1f}s | Route: {route_used}")
```

### Monitor Context Flow

Add context flow debugging:
```python
def debug_context_flow(self, stage: str, context: str):
    context_preview = context[:100] + "..." if len(context) > 100 else context
    print(f"🔄 Context at {stage}: {context_preview}")

# Use throughout the pipeline
self.debug_context_flow("fast_llm_input", routing_context)
self.debug_context_flow("local_llm_input", generation_context)
self.debug_context_flow("external_llm_input", consultation_context)
```

## Getting Help

### Collect Debug Information

When reporting issues, include:

1. **System Information**:
```bash
uname -a
python --version
poetry --version
```

2. **Model Information**:
```bash
ls -la models/
du -h models/
```

3. **Configuration**:
```bash
# Sanitized identity config (remove API keys)
cat identity/identity.json | jq 'del(.external_llms.providers[].api_key)'
```

4. **Debug Output**: Include full debug output showing the problem

5. **Performance Metrics**: Include timing information from debug output

### Contact and Resources

- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check docs/ folder for detailed information
- **Configuration Examples**: See sample configurations in the repository

Remember: Most issues are related to configuration, context handling, or resource limitations. The debug output is your best tool for identifying the root cause. 