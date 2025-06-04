# Aletheia Service Documentation

Prometheus v0.6.0 introduces a unified service architecture that allows Aletheia to be accessed through multiple frontends while sharing a single AI instance.

## 🏗️ **Service Architecture**

The service uses a **singleton pattern** to ensure all frontends share the same Aletheia instance:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Telegram      │    │   Terminal      │
│   REST Server   │    │   Bot           │    │   Shell         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Singleton      │
                    │  Aletheia       │
                    │  Instance       │
                    └─────────────────┘
```

**Benefits:**
- **Shared Memory**: All conversations across frontends share the same memory
- **Consistent Context**: User sessions persist across different interfaces  
- **Resource Efficiency**: Single AI instance serves multiple frontends
- **Unified Experience**: Same capabilities regardless of access method

## 🚀 **Getting Started**

### Installation

```bash
# Install dependencies
poetry install

# Or with pip
pip install fastapi[all] python-telegram-bot httpx
```

### Launch Modes

The service supports three frontend modes:

```bash
# REST API Server
python prometheus.py --mode api

# Telegram Bot  
python prometheus.py --mode telegram

# Interactive Shell
python prometheus.py --mode shell
```

## 📡 **REST API Mode**

### Starting the API Server

```bash
python prometheus.py --mode api
# Server starts on http://0.0.0.0:8000
# API docs available at http://localhost:8000/docs
```

**Custom host/port:**
```bash
python prometheus.py --mode api --host 127.0.0.1 --port 3000
```

### API Endpoints

#### **POST /v1/chat** - Chat with Aletheia

**Request:**
```json
{
  "user_id": "string",
  "message": "string"
}
```

**Response:**
```json
{
  "answer": "string",
  "route": "string", 
  "latency": 0.0
}
```

#### **GET /** - Service Information

**Response:**
```json
{
  "service": "Aletheia AI Service",
  "version": "0.6.0",
  "status": "running",
  "endpoints": {
    "chat": "/v1/chat",
    "docs": "/docs", 
    "health": "/health"
  }
}
```

#### **GET /health** - Health Check

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1234567890.0
}
```

### cURL Examples

**Basic chat request:**
```bash
curl -X POST "http://localhost:8000/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "Hello Aletheia, how are you?"
  }'
```

**Health check:**
```bash
curl http://localhost:8000/health
```

**Service info:**
```bash
curl http://localhost:8000/
```

**Complex technical question:**
```bash
curl -X POST "http://localhost:8000/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "developer",
    "message": "Explain the difference between async/await and traditional threading in Python"
  }'
```

## 🤖 **Telegram Bot Mode**

### Setup Steps

1. **Create a Telegram Bot:**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` command
   - Choose a name and username for your bot
   - Copy the bot token

2. **Set Environment Variable:**
   ```bash
   export TELEGRAM_TOKEN="your_bot_token_here"
   ```

3. **Start the Bot:**
   ```bash
   python prometheus.py --mode telegram
   ```

4. **Find Your Bot:**
   - Search for your bot username on Telegram
   - Send `/start` to begin chatting

### Bot Commands

- `/start` - Welcome message and introduction
- `/help` - Show available commands  
- `/status` - Display system status
- Just send any message to chat with Aletheia!

### Bot Features

- **Bilingual Support**: Responds in Russian or English based on input
- **Typing Indicators**: Shows "typing..." while processing
- **Error Handling**: Graceful error messages for technical issues
- **User Sessions**: Each Telegram user gets their own conversation context

### Example Conversation

```
You: /start
Bot: 👋 Привет! Я Алетейя, автономный ИИ-агент...

You: What is machine learning?
Bot: Machine learning is a subset of artificial intelligence...

You: Что такое нейронные сети?
Bot: Нейронные сети — это вычислительные модели...
```

## 🐚 **Terminal Shell Mode**

### Starting the Shell

```bash
python prometheus.py --mode shell
```

### Shell Interface

```
🐚 Aletheia Interactive Shell
========================================
Commands:
  - Type your message and press Enter
  - Type 'quit', 'exit' or Ctrl+C to exit
  - All conversations use user_id='terminal'
========================================

🐚 Shell: Hello Aletheia!
🤔 Thinking...

🤖 Aletheia: Hello! I'm ready to help with any questions...

🐚 Shell: quit
👋 Goodbye!
```

### Shell Features

- **Direct Access**: No network setup required
- **Debug Output**: Shows routing decisions and performance metrics
- **Session Persistence**: Maintains conversation context
- **Clean Exit**: Type `quit`, `exit`, or use Ctrl+C

## 🔧 **Advanced Configuration**

### Environment Variables

```bash
# Required for Telegram mode
export TELEGRAM_TOKEN="your_telegram_bot_token"

# Optional: External LLM API keys
export OPENAI_API_KEY="your_openai_key"
export ANTHROPIC_API_KEY="your_anthropic_key"
```

### Multiple Frontend Usage

You can run multiple frontends simultaneously:

```bash
# Terminal 1: Start API server
python prometheus.py --mode api

# Terminal 2: Start Telegram bot (same instance!)
python prometheus.py --mode telegram

# Terminal 3: Use shell (same instance!)
python prometheus.py --mode shell
```

**Note**: The system will warn if a service is already running but allows multiple frontends to share the same instance.

## 🧪 **Testing**

### Run Tests

```bash
# Test singleton behavior
pytest tests/test_singleton.py -v

# Test API endpoints  
pytest tests/test_api.py -v

# Run all tests
pytest tests/ -v
```

### Manual Testing

**API Testing:**
```bash
# Start API server
python prometheus.py --mode api

# In another terminal, test with curl
curl -X POST "http://localhost:8000/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "Hello"}'
```

**Telegram Testing:**
1. Set up bot token
2. Start bot: `python prometheus.py --mode telegram`
3. Message your bot on Telegram

**Shell Testing:**
```bash
python prometheus.py --mode shell
# Type some messages and verify responses
```

## 🔍 **Troubleshooting**

### Common Issues

**"TELEGRAM_TOKEN not set"**
```bash
export TELEGRAM_TOKEN="your_token_from_botfather"
```

**"FastAPI not installed"**
```bash
pip install fastapi[all]
# or
poetry install
```

**"Port already in use"**
```bash
python prometheus.py --mode api --port 3000
```

**Service already running warning:**
- This is normal when running multiple frontends
- Each frontend shares the same Aletheia instance
- Choose 'y' to continue or 'n' to abort

### Debug Information

All modes show debug output including:
- Route decisions (local vs external LLM)
- Performance metrics (latency, cost estimates)
- Memory usage and context information
- User session management

### Logs

Service logs are stored in:
- Router decisions: `data/logs/router.csv`
- Application logs: Console output with timestamps

## 📊 **Performance & Monitoring**

### Metrics Available

- **Response Latency**: Time to generate responses
- **Route Decisions**: Local vs external LLM usage
- **Memory Usage**: Context and conversation storage
- **User Sessions**: Active user tracking
- **Error Rates**: Failed requests and recovery

### Health Monitoring

```bash
# Check service health
curl http://localhost:8000/health

# Get detailed status via Telegram
/status

# Shell status (built into debug output)
```

## 🔮 **Future Enhancements**

- **WebSocket Support**: Real-time bidirectional communication
- **Authentication**: User authentication and authorization
- **Rate Limiting**: Request throttling and quotas
- **Metrics Dashboard**: Web-based monitoring interface
- **Multi-Entity Support**: Switch between different AI entities
- **Plugin System**: Custom frontend integrations 