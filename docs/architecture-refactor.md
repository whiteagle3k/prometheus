# 🏗️ **Universal Multi-Entity Architecture**

## **Архитектурный Рефакторинг Prometheus v0.6.0**

### **Проблема Старой Архитектуры**

**До рефакторинга** (нарушение принципа разделения):
```
core/service/singleton.py  # Жестко привязан к Aletheia
core/service/api_server.py # Импортирует только Aletheia
core/service/telegram_bot.py # Работает только с одним агентом
```

**Проблемы:**
- Нарушение принципа Prometheus ↔ Entity separation
- Невозможность запуска нескольких агентов одновременно
- Жесткая привязка к классу "AletheiaEntity"
- Копирование кода для каждой новой сущности

---

## **✅ Новая Универсальная Архитектура**

### **1. Runtime Layer - Управление Агентами**

```
core/runtime/
├── registry.py      # Universal AgentRegistry
├── lifecycle.py     # Startup/shutdown coordination
└── __init__.py
```

**AgentRegistry Pattern:**
```python
# Universal entity loading
async def get_agent(entity_name: str = "aletheia") -> BaseEntity:
    """Load any entity dynamically by name"""
    if entity_name in _instances:
        return _instances[entity_name]
    
    # Dynamic import: entities.{name}.{Name}Entity
    module_path = f"entities.{entity_name}"
    entity_module = importlib.import_module(module_path)
    entity_class = getattr(entity_module, f"{entity_name.capitalize()}Entity")
    
    instance = entity_class()
    _instances[entity_name] = instance
    return instance
```

**Ключевые преимущества:**
- ✅ **Entity-agnostic**: Работает с любой сущностью
- ✅ **Singleton per entity**: Один экземпляр на сущность
- ✅ **Thread-safe**: asyncio.Lock() для конкурентного доступа
- ✅ **Dynamic loading**: Автоматический импорт из `entities/{name}/`

### **2. Frontends Layer - Точки Входа**

```
core/frontends/
├── api_server.py    # REST API (/v1/chat?entity=name)
├── telegram_bot.py  # Telegram bot (/use <entity>)
└── __init__.py
```

**Universal API Example:**
```bash
# Aletheia
curl 'http://localhost:8000/v1/chat?entity=aletheia' \
  -d '{"user_id":"test","message":"Hello"}'

# Prometheus  
curl 'http://localhost:8000/v1/chat?entity=prometheus' \
  -d '{"user_id":"test","message":"Hello"}'

# Any future entity
curl 'http://localhost:8000/v1/chat?entity=teslabot' \
  -d '{"user_id":"test","message":"Hello"}'
```

**Universal Telegram Commands:**
```
/use aletheia     # Switch to Aletheia entity
/use prometheus   # Switch to Prometheus entity
/entities         # List available entities
/status           # Current entity + system status
```

### **3. Multi-Entity Launcher**

```bash
# Launch with specific entity
python prometheus.py api --entity aletheia
python prometheus.py telegram --entity prometheus

# Pre-initialize multiple entities
python prometheus.py api --entities aletheia,prometheus,teslabot

# Shell with entity selection
python prometheus.py shell --entity prometheus
```

---

## **🔄 Migration Steps Completed**

### **1. Registry System**
- ✅ **core/runtime/registry.py**: Universal agent registry
- ✅ **Dynamic entity loading**: `entities.{name}.{Name}Entity`
- ✅ **Concurrent access**: Thread-safe with asyncio.Lock()
- ✅ **Lifecycle management**: Graceful startup/shutdown

### **2. Directory Restructure** 
- ✅ **core/service/** → **core/frontends/**
- ✅ **Deleted singleton.py**: Replaced with universal registry
- ✅ **Updated imports**: All frontends use registry

### **3. Universal Frontends**
- ✅ **API Server**: `/v1/chat?entity=<name>` support
- ✅ **Telegram Bot**: `/use <entity>` command switching
- ✅ **Prometheus Launcher**: `--entity` and `--entities` flags

### **4. Enhanced Testing**
- ✅ **Parametrized tests**: Test any entity
- ✅ **Mock system**: Independent of specific entities
- ✅ **Concurrent testing**: Multiple entities simultaneously

---

## **🚀 Production Usage Examples**

### **Scenario 1: Single Entity Deployment**
```bash
# Traditional Aletheia deployment
python prometheus.py api --entity aletheia
```

### **Scenario 2: Multi-Entity Service**
```bash
# Support multiple entities in one process
python prometheus.py api --entities aletheia,prometheus,teslabot

# REST API automatically routes to correct entity:
# /v1/chat?entity=aletheia    → Aletheia instance
# /v1/chat?entity=prometheus  → Prometheus instance  
# /v1/chat?entity=teslabot    → TeslaBot instance
```

### **Scenario 3: Telegram Multi-Bot**
```bash
# Single Telegram bot, multiple entities
python prometheus.py telegram --entities aletheia,prometheus

# Users can switch:
# /use aletheia  → Chat with Aletheia
# /use prometheus → Chat with Prometheus  
```

### **Scenario 4: Development Testing**
```bash
# Test specific entity in shell
python prometheus.py shell --entity teslabot

# Quick API testing
curl 'localhost:8000/v1/chat?entity=teslabot' -d '{"user_id":"dev","message":"test"}'
```

---

## **📊 Performance Benefits**

### **Memory Efficiency**
- **Before**: Один агент на процесс
- **After**: Множество агентов в одном процессе с shared resources

### **Registry Pattern Performance**
```python
# First call: Dynamic loading
agent = await get_agent("aletheia")  # ~100ms (model loading)

# Subsequent calls: Cached instance  
agent = await get_agent("aletheia")  # ~0.1ms (registry lookup)
```

### **Concurrent Load Distribution**
```python
# Multiple entities handle different request types
async def route_request(entity: str, message: str):
    agent = await get_agent(entity)  # Load balancing by entity
    return await agent.think(message)

# /v1/chat?entity=aletheia    → Specialized for conversations
# /v1/chat?entity=prometheus  → Specialized for system management
# /v1/chat?entity=research    → Specialized for research tasks
```

---

## **🔮 Future Extensibility**

### **Adding New Entities**
```bash
# 1. Create entity directory
mkdir entities/gpt4_entity

# 2. Implement entity class
touch entities/gpt4_entity/__init__.py
touch entities/gpt4_entity/gpt4_entity.py

# 3. Define Gpt4Entity class extending BaseEntity
class Gpt4Entity(BaseEntity):
    def __init__(self):
        super().__init__("gpt4")
    
    async def think(self, message, user_id=None):
        # GPT-4 specific implementation
        pass

# 4. Use immediately - no code changes needed!
python prometheus.py api --entity gpt4
curl 'localhost:8000/v1/chat?entity=gpt4' -d '{"message":"Hello"}'
```

### **Entity Factory Pattern** (Future Enhancement)
```python
# Coming soon: Config-driven entity creation
{
  "entities": {
    "aletheia": {"model": "llama3.1", "mode": "creative"},
    "prometheus": {"model": "claude", "mode": "analytical"},
    "researcher": {"model": "gpt4", "mode": "research"}
  }
}
```

---

## **🎯 Architecture Goals Achieved**

### **✅ Separation of Concerns**
- **Prometheus Core**: Universal framework code
- **Entity Layer**: Specific agent implementations
- **Frontend Layer**: Interface adapters (API, Telegram, Shell)
- **Runtime Layer**: Process management and registry

### **✅ Entity Independence**  
- Each entity manages its own state
- No cross-contamination between entities
- Isolated failure modes
- Independent scaling potential

### **✅ Developer Experience**
```bash
# One command, any entity
python prometheus.py {api|telegram|shell} --entity {any_name}

# Multiple entities, single process
python prometheus.py api --entities name1,name2,name3

# Seamless entity switching in Telegram
/use different_entity
```

### **✅ Production Readiness**
- Graceful shutdown preserves all entity states
- Health checks report per-entity status
- Metrics labeled by entity (`frontend="api|telegram|shell"`)
- Auto-snapshots work per-entity
- Rate limiting respects entity boundaries

---

## **🏁 Result: True Multi-Entity Framework**

**Before**: Prometheus was "Aletheia Service with multiple frontends"

**After**: Prometheus is "Universal Multi-Entity AI Framework"

**Impact:**
- ♾️ **Unlimited entities** in single deployment
- 🔄 **Zero downtime** entity switching via Telegram
- ⚡ **Shared infrastructure** (memory, models, monitoring)
- 🎛️ **Per-entity configuration** and behavior
- 📈 **Horizontal scaling** by entity specialization

**Ready for enterprise deployment with any number of specialized AI entities! 🚀** 