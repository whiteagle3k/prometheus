# Memory System Architecture

## Overview

Prometheus implements a sophisticated **three-tier context system** ("cloud of contexts") that enables Aletheia to maintain distinct memory spaces for different types of information while providing unified, intelligent retrieval.

## Three-Tier Architecture

### 🧠 **Core-Self Context** (Priority 1)
- **Purpose**: Aletheia's autobiographical memory and self-development
- **Contents**: 
  - Self-reflection loops and learning experiences
  - Skill acquisition and improvement records
  - Internal goals and system evolution
  - Meta-cognitive insights about own performance
- **Threshold**: 0.75 (highest quality filter)
- **Max Chunks**: 500 (focused on key learnings)
- **Value**: High - contains expensive LLM-acquired knowledge
- **Reset Policy**: Protected by default, requires explicit override

### 👤 **User Context** (Priority 2)  
- **Purpose**: Per-user conversation history and preferences
- **Contents**:
  - Conversation threads and dialogue history
  - User preferences and personal data
  - User feedback and corrections
  - Relationship context and interaction patterns
- **Threshold**: 0.70 (conversational relevance)
- **Max Chunks**: 1000 (extensive user modeling)
- **Value**: Medium - user-specific but replaceable
- **Reset Policy**: Safe to reset for privacy/cleanup

### 🌍 **Environment Context** (Priority 3)
- **Purpose**: External sensor and API data integration
- **Contents**:
  - Sensor readings and environmental data
  - API webhooks and external events
  - System notifications and alerts
  - Third-party service integration data
- **Threshold**: 0.65 (broad environmental awareness)
- **Max Chunks**: 300 (recent environmental state)
- **Value**: Low - transient data that can be regenerated
- **Reset Policy**: Safe to reset for cleanup

## Memory Safety and Reset System

### Reset Commands

#### `reset` - Safe Reset (Default)
```bash
# Clears USER and ENV tiers, preserves CORE_SELF
reset
```
- ✅ Clears user conversations and preferences
- ✅ Clears environmental/sensor data
- ✅ Preserves Aletheia's learned knowledge
- ✅ Safe for production use

#### `reset_all` - Complete Reset (Development Only)
```bash
# Clears ALL tiers including CORE_SELF
reset_all
```
- ⚠️  Deletes ALL memory including valuable learned knowledge
- ⚠️  Only available in development mode
- ⚠️  Disabled by default in production

### Configuration Modes

#### Development Mode (Default)
```env
DEVELOPMENT_MODE=true
ALLOW_COMPLETE_MEMORY_RESET=true
```
- Both `reset` and `reset_all` available
- Suitable for testing and development
- Complete memory reset allowed

#### Production Mode (Recommended)
```env
DEVELOPMENT_MODE=false
ALLOW_COMPLETE_MEMORY_RESET=false
```
- Only `reset` available (safe tier reset)
- `reset_all` command disabled
- Protects valuable learned knowledge

### Safety Features

#### Configuration Guards
- Environment variable controls for reset permissions
- Development vs production mode separation
- CLI command availability based on mode

#### User Warnings
```
🚨 FULL MEMORY RESET - This will delete Aletheia's learned knowledge!
🚨 This should only be used during development!
```

#### Graceful Degradation
- If tier-specific reset not available, clear warning provided
- Fallback to full reset only with explicit user awareness

### Implementation Status

#### Current (Hierarchical Memory)
- **Full Reset**: ✅ Implemented
- **Tier-Specific Reset**: ⚠️ Planned (falls back to full reset with warning)

#### Future (Three-Tier Controller)
- **Full Reset**: ✅ Implemented
- **Tier-Specific Reset**: 🚧 In Development
- **CORE_SELF Protection**: 🚧 In Development

## Intelligent Retrieval System

### Tiered Search Strategy

```python
async def retrieve(query: str, k: int = 6) -> RetrievalResult:
    """
    1. Search Core-Self (threshold 0.75) 
    2. If <k results, search User (threshold 0.70)
    3. If still <k, search Environment (threshold 0.65)
    4. Return merged list maintaining tier priority
    """
```

### Retrieval Priority Logic

1. **Core-Self First**: Aletheia's own experiences and learnings take highest priority
2. **User Context Second**: Relevant conversation history and user preferences  
3. **Environment Last**: Supplementary environmental context if needed
4. **Quality Thresholds**: Higher tiers require higher similarity scores
5. **Adaptive Results**: Stops searching when sufficient relevant memories found

## Automatic Classification System

### Write-Back Logic

The MemoryController automatically classifies new experiences:

```python
# Core-Self indicators
"i learned", "my skill", "self-reflection", "internal goal"

# Environment indicators  
"sensor", "api", "external", "webhook", "event"

# Default: User tier (conversation content)
```

### Memory Types by Tier

**Core-Self Types:**
- `SELF_REFLECTION` - Insights about own performance
- `SKILL_ACQUISITION` - Learning new capabilities
- `INTERNAL_GOAL` - Setting and tracking self-improvement
- `SYSTEM_LEARNING` - Understanding system behavior

**User Types:**
- `CONVERSATION` - Dialogue exchanges
- `USER_PREFERENCE` - Stated likes/dislikes
- `USER_DATA` - Personal information
- `USER_FEEDBACK` - Corrections and guidance

**Environment Types:**
- `SENSOR_DATA` - Physical sensor readings
- `API_EVENT` - External service notifications
- `EXTERNAL_UPDATE` - Third-party data changes
- `SYSTEM_EVENT` - Infrastructure notifications

## Overflow Management

### Per-Tier Summarization

When a tier exceeds its `max_chunks` limit:

1. **Identify Oldest**: Find least recently accessed memories
2. **Generate Summary**: Use local LLM to create TL;DR condensation
3. **Replace Batch**: Store summary chunk with `is_summary=True`
4. **Preserve Key**: Maintain essential information in compressed form

### Summarization Ratios

- **Core-Self**: 10% retention (highly selective)
- **User**: 20% retention (preserve relationship context)
- **Environment**: 15% retention (keep recent state)

## Usage Examples

### Basic Memory Operations

```python
from aletheia.memory.controller import MemoryController
from aletheia.memory.models import MemoryChunk
from aletheia.memory.enums import MemoryTier, MemoryType

# Initialize controller
memory = MemoryController()

# Store self-reflection (auto-classified to Core-Self)
await memory.store(MemoryChunk(
    id="learn-001",
    text="I learned to better detect user frustration through conversation patterns",
    embedding=[],  # Generated automatically
    tier=MemoryTier.CORE_SELF,  # Can be auto-classified
    memory_type=MemoryType.SELF_REFLECTION
))

# Retrieve relevant context
result = await memory.retrieve("how to help frustrated users", k=6)
print(f"Found {result.total_retrieved} memories across {len(result.tier_counts)} tiers")
```

### User Context Management

```python
# Store user conversation with automatic user_id
memory.current_user_id = "igor_123"

await memory.store(MemoryChunk(
    id="conv-001", 
    text="User Igor prefers detailed technical explanations",
    embedding=[],
    tier=MemoryTier.USER,
    memory_type=MemoryType.USER_PREFERENCE,
    metadata={"user_id": "igor_123", "preference_type": "explanation_style"}
))

# Retrieve user-specific context
user_context = await memory.retrieve("technical explanation style", user_id="igor_123")
```

### Environment Integration (Future)

```python
# Store sensor data
await memory.store(MemoryChunk(
    id="sensor-001",
    text="Temperature sensor reading: 23.5°C, humidity: 45%",
    embedding=[],
    tier=MemoryTier.ENV,
    memory_type=MemoryType.SENSOR_DATA,
    metadata={"sensor_id": "temp_01", "location": "office"}
))
```

## Data Models

### MemoryChunk Structure

```python
@dataclass
class MemoryChunk:
    id: str                          # Unique identifier
    text: str                        # Content for embedding/search
    embedding: List[float]           # Vector representation
    tier: MemoryTier                 # Core-Self/User/Environment
    memory_type: MemoryType          # Specific classification
    metadata: dict[str, Any]         # Additional context
    timestamp: datetime              # Creation time
    is_summary: bool = False         # Condensed from multiple memories
    confidence: float = 1.0          # Quality/certainty score
    source: str = ""                 # Origin context
```

### Retrieval Results

```python
@dataclass
class RetrievalResult:
    chunks: List[MemoryChunk]        # Retrieved memories in priority order
    tier_counts: dict[MemoryTier, int]  # Memories per tier
    total_retrieved: int             # Total count
    search_query: str               # Original query
```

## Integration with Orchestrator

### Pre-Processing Hook

Before generating responses, the orchestrator retrieves relevant context:

```python
# In orchestrator.py
async def process_user_input(self, user_input: str) -> dict:
    # Retrieve relevant memories across all tiers
    memory_context = await self.memory_controller.retrieve(user_input, k=6)
    
    # Build enriched prompt with tiered context
    prompt = self._build_context_prompt(user_input, memory_context)
    
    # Generate response with full context awareness
    response = await self.router.execute_task(prompt)
    
    return response
```

### Post-Processing Hook

After generating responses, experiences are stored in appropriate tiers:

```python
async def store_experience(self, user_input: str, response: str, metadata: dict):
    # Create memory chunks for the interaction
    user_chunk = MemoryChunk(
        id=f"user-{uuid.uuid4()}",
        text=user_input,
        embedding=[],  # Generated by store()
        tier=MemoryTier.USER,  # Will be auto-classified
        memory_type=MemoryType.CONVERSATION,
        metadata=metadata
    )
    
    response_chunk = MemoryChunk(
        id=f"response-{uuid.uuid4()}",
        text=response,
        embedding=[],
        tier=MemoryTier.USER,
        memory_type=MemoryType.CONVERSATION,
        metadata=metadata
    )
    
    # Store both parts of the conversation
    await self.memory_controller.store(user_chunk)
    await self.memory_controller.store(response_chunk)
    
    # Check for self-reflection opportunities
    if self._should_reflect(response, metadata):
        reflection = await self._generate_reflection(user_input, response)
        await self.memory_controller.store(reflection)  # Auto-classified to Core-Self
```

## Migration from Single-Tier System

### Migration Script

To migrate existing ChromaDB data to the new three-tier system:

```python
# migration/migrate_to_three_tier.py
import asyncio
from aletheia.memory.vector_store import VectorStore
from aletheia.memory.controller import MemoryController
from aletheia.memory.enums import MemoryTier, MemoryType

async def migrate_existing_memories():
    """Migrate single-tier memories to three-tier system."""
    
    # Load existing vector store
    old_store = VectorStore(collection_name="aletheia_memory")
    new_controller = MemoryController()
    
    # Get all existing memories
    existing_memories = await old_store.get_all_memories()  # Would need implementation
    
    migrated_count = {"core_self": 0, "user": 0, "env": 0}
    
    for memory in existing_memories:
        # Classify memory into appropriate tier
        chunk = MemoryChunk(
            id=memory["id"],
            text=memory["content"],
            embedding=memory.get("embedding", []),
            tier=MemoryTier.USER,  # Will be auto-classified
            memory_type=MemoryType.CONVERSATION,
            metadata=memory.get("metadata", {})
        )
        
        # Store in new system (auto-classifies tier)
        await new_controller.store(chunk)
        
        # Count migrations by tier
        migrated_count[chunk.tier.value] += 1
    
    print(f"Migration complete: {migrated_count}")
    
    # Archive old collection
    await old_store.archive_collection()

# Run migration
if __name__ == "__main__":
    asyncio.run(migrate_existing_memories())
```

## Performance Characteristics

### Retrieval Performance

- **Core-Self queries**: ~50-100ms (highly curated, small dataset)
- **User queries**: ~100-200ms (moderate dataset with user filtering)
- **Environment queries**: ~150-300ms (larger dataset, lower threshold)
- **Cross-tier queries**: ~200-400ms (searches all tiers if needed)

### Storage Performance

- **Classification**: ~1-5ms (rule-based, local processing)
- **Embedding generation**: ~50-100ms (depends on text length)
- **Vector storage**: ~10-50ms (ChromaDB write performance)
- **Overflow check**: ~5-10ms (count estimation)

### Memory Usage

- **Core-Self**: ~50MB (500 chunks × ~100KB average)
- **User**: ~100MB (1000 chunks × ~100KB average)  
- **Environment**: ~30MB (300 chunks × ~100KB average)
- **Total**: ~180MB for full system

## Configuration

### Environment Variables

```env
# Memory system configuration
MEMORY_CORE_SELF_MAX_CHUNKS=500
MEMORY_USER_MAX_CHUNKS=1000  
MEMORY_ENV_MAX_CHUNKS=300

MEMORY_CORE_SELF_THRESHOLD=0.75
MEMORY_USER_THRESHOLD=0.70
MEMORY_ENV_THRESHOLD=0.65

MEMORY_SUMMARIZATION_RATIO=0.1
MEMORY_BACKGROUND_CLEANUP=true

# Memory safety configuration
DEVELOPMENT_MODE=true
ALLOW_COMPLETE_MEMORY_RESET=true
```

### Custom Tier Configuration

```python
from aletheia.memory.models import TierConfig
from aletheia.memory.enums import MemoryTier

custom_configs = {
    MemoryTier.CORE_SELF: TierConfig(
        max_chunks=1000,           # More self-reflection capacity
        similarity_threshold=0.80,  # Higher quality requirement
        summarization_ratio=0.05,   # Very selective summarization
        collection_name="aletheia_enhanced_core"
    ),
    MemoryTier.USER: TierConfig(
        max_chunks=2000,           # Extensive user modeling
        similarity_threshold=0.65,  # More inclusive user memories
        summarization_ratio=0.25,   # Preserve more user context
    ),
    MemoryTier.ENV: TierConfig(
        max_chunks=500,            # More environmental context
        similarity_threshold=0.60,  # Broad environmental awareness
        summarization_ratio=0.20,   # Keep recent environmental state
    )
}

memory = MemoryController(tier_configs=custom_configs)
```

## Best Practices

### For Autonomous Operation
1. Set `DEVELOPMENT_MODE=false`
2. Set `ALLOW_COMPLETE_MEMORY_RESET=false`
3. Use `reset` for user privacy/cleanup needs
4. Monitor CORE_SELF memory growth and value

### For Development
1. Use `reset_all` sparingly to avoid losing valuable test knowledge
2. Consider backing up learned knowledge before major resets
3. Test with `reset` to ensure tier-specific behavior works correctly

### For Production Deployment
1. Always disable complete memory reset
2. Implement memory backup/restore for disaster recovery
3. Monitor memory usage and implement archival for old data
4. Provide user controls for their own data reset (USER tier only)

### Migration Path

#### Phase 1: Current (Safe Default)
- `reset` performs full reset with warning about CORE_SELF
- `reset_all` available only in development mode
- Clear user communication about limitations

#### Phase 2: Tier-Specific (Future)
- `reset` performs selective USER/ENV reset
- CORE_SELF preserved during normal resets
- `reset_all` remains development-only for complete reset

## Future Enhancements

### Planned Features

1. **Machine Learning Classification**: Replace rule-based classification with trained models
2. **Semantic Clustering**: Group related memories for better summarization
3. **Cross-Tier Relationships**: Track connections between different context types
4. **Federated Memory**: Sync memory across multiple agent instances
5. **Memory Compression**: Advanced techniques for long-term storage efficiency

### Sensor Integration

The Environment tier is designed for future sensor integration:

```python
# Future sensor integration example
class SensorManager:
    async def on_sensor_data(self, sensor_id: str, data: dict):
        """Handle incoming sensor data."""
        chunk = MemoryChunk(
            id=f"sensor-{sensor_id}-{timestamp}",
            text=f"Sensor {sensor_id}: {data}",
            embedding=[],
            tier=MemoryTier.ENV,
            memory_type=MemoryType.SENSOR_DATA,
            metadata={"sensor_id": sensor_id, "data": data}
        )
        await self.memory_controller.store(chunk)
```

This three-tier memory architecture provides Aletheia with sophisticated context awareness while maintaining clear boundaries between self-knowledge, user relationships, and environmental awareness. 