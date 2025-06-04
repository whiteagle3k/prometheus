# Telegram Bot Configuration Guide

Prometheus supports **two approaches** for Telegram bots:

1. **Universal Bot** - One bot that can switch between entities
2. **Entity-Specific Bots** - Dedicated bots for each entity

## 🤖 Universal Bot (Default)

**One bot serves multiple entities with switching capability.**

### Setup:
```bash
# 1. Create bot with @BotFather
# 2. Set environment variable
export TELEGRAM_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"

# 3. Start universal bot
python prometheus.py telegram --entities "aletheia,tesla"
```

### Features:
- ✅ One bot to manage
- ✅ Easy entity switching with `/use <entity>`
- ✅ Commands: `/start`, `/use`, `/entities`, `/status`, `/help`
- ❌ Users need to remember to switch entities
- ❌ Responses show "🤖 **Aletheia**: ..." prefix

### User Experience:
```
User: /start
Bot: 👋 Привет! Я универсальный бот Prometheus.
     🤖 Активная сущность: **Aletheia**

User: Hello
Bot: 🤖 **Aletheia**: Hello! I'm Aletheia, how can I help?

User: /use tesla
Bot: ✅ Переключено на сущность: **Tesla**

User: Hello  
Bot: 🤖 **Tesla**: Hi! I'm Tesla, ready to assist!
```

## 🎭 Entity-Specific Bots (Your Preferred Approach)

**Dedicated bots for each entity with fixed personalities.**

### Setup:

#### Step 1: Create Multiple Bots
```bash
# Create separate bots with @BotFather:
# - aletheia_assistant_bot → Token A
# - tesla_helper_bot → Token B
# - etc.
```

#### Step 2: Set Entity-Specific Tokens
```bash
# Method A: Entity-specific environment variables
export TELEGRAM_TOKEN_ALETHEIA="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
export TELEGRAM_TOKEN_TESLA="987654321:XYZabcDEFghiJKLmnoPQRstu"

# Method B: Generic token (for single entity)
export TELEGRAM_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
```

#### Step 3: Launch Entity-Specific Bots
```bash
# Launch Aletheia bot
python scripts/entity_bot.py aletheia

# Launch Tesla bot (in separate terminal/process)
python scripts/entity_bot.py tesla

# Or with explicit token
python scripts/entity_bot.py aletheia "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
```

### Features:
- ✅ Clear branding per entity
- ✅ Fixed personality (no switching confusion)
- ✅ Commands: `/start`, `/status`, `/help` (no `/use` needed)
- ✅ Clean responses without entity prefixes
- ❌ Multiple bots to manage
- ❌ Requires multiple bot tokens

### User Experience:
```
# Aletheia Bot
User: /start
Bot: 👋 Привет! Я Aletheia.
     🤖 AI Assistant with philosophical insights
     
User: Hello
Bot: Hello! I'm Aletheia. How can I help you explore ideas today?

# Tesla Bot (separate bot)
User: /start  
Bot: 👋 Привет! Я Tesla.
     🤖 Engineering and innovation assistant
     
User: Hello
Bot: Hi! I'm Tesla, ready to discuss engineering and innovation!
```

## 🔧 Production Deployment

### Universal Bot (Simple)
```bash
# Single process
docker run -e TELEGRAM_TOKEN=xxx prometheus:latest telegram --entities "aletheia,tesla"
```

### Entity-Specific Bots (Advanced)
```bash
# Multiple processes/containers
docker run -e TELEGRAM_TOKEN_ALETHEIA=xxx prometheus:latest scripts/entity_bot.py aletheia &
docker run -e TELEGRAM_TOKEN_TESLA=yyy prometheus:latest scripts/entity_bot.py tesla &

# Or with docker-compose
version: '3.8'
services:
  aletheia-bot:
    image: prometheus:latest
    environment:
      - TELEGRAM_TOKEN_ALETHEIA=${TELEGRAM_TOKEN_ALETHEIA}
    command: python scripts/entity_bot.py aletheia
    
  tesla-bot:
    image: prometheus:latest
    environment:
      - TELEGRAM_TOKEN_TESLA=${TELEGRAM_TOKEN_TESLA}
    command: python scripts/entity_bot.py tesla
```

## 🎯 Recommendation

**For your use case (clear entity branding), use Entity-Specific Bots:**

1. Create separate bots: `aletheia_bot`, `tesla_bot`, etc.
2. Use `scripts/entity_bot.py` for each
3. Each bot has its own personality and branding
4. Users know exactly who they're talking to

## ⚙️ Configuration

Both approaches share the same core features:
- **Rate Limiting**: Exponential back-pressure (5s→300s)
- **Prometheus Metrics**: Full monitoring support
- **Error Handling**: Graceful recovery
- **Multi-Entity Registry**: Shared agent system

The only difference is the **user interface** and **bot management** approach. 