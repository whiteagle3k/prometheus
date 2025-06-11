# Supervisor Bootstrap Guide 🎯

Minimal supervisor-agent system for autonomous task management and development coordination.

## Architecture

```
User → REST API → Supervisor Agent → Task Queue → Local Worker
                      ↓
                  Subtask Planning (LLM)
                      ↓
                Git Branches + PRs ← Tests ← Code Generation
```

## Quick Start

### 1. Install Dependencies
```bash
poetry install
```

### 2. Setup Redis (Local)
```bash
# Option A: Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Option B: Native installation
brew install redis  # macOS
redis-server
```

### 3. Start Supervisor + API
```bash
# Start API with supervisor entity
python prometheus.py api --entities supervisor,aletheia

# Or with Docker Compose
docker compose up -d
```

### 4. Start Local Worker
```bash
# In another terminal
python scripts/worker_local.py
```

## Usage

### Submit High-Level Task
```bash
curl -X POST localhost:8000/v1/task \
  -H "Content-Type: application/json" \
  -d '{
    "brief": "Add rate limiting to API endpoints",
    "context": "Use Redis for storage, configurable limits",
    "priority": "normal",
    "user_id": "developer_001"
  }'
```

### Check Status
```bash
# Supervisor status and queue info
curl localhost:8000/v1/supervisor/status

# System health
curl localhost:8000/health
```

### Monitor Worker
The worker will:
1. 🔄 Wait for tasks from supervisor
2. 🌿 Create git branch `task/{task_id}`
3. 📝 Generate code changes (placeholder for now)
4. 🧪 Run tests
5. 📤 Push branch to remote
6. ✅ Mark task as done/failed

## Task Flow

1. **User**: Submit high-level brief via API
2. **Supervisor**: Break down into atomic subtasks using LLM
3. **Queue**: Store subtasks in Redis
4. **Worker**: Process subtasks sequentially
5. **Git**: Create branches and PRs for review
6. **User**: Review and merge completed tasks

## Current Status

✅ **Implemented**:
- Redis task queue system
- SupervisorEntity with LLM planning
- REST API endpoints (/v1/task, /v1/supervisor/status)
- Local worker with git integration
- Docker deployment setup

🚧 **Placeholder**:
- Code generation (currently creates task log files)
- LLM integration in worker
- Advanced error handling

## API Endpoints

- `POST /v1/task` - Submit development task
- `GET /v1/supervisor/status` - Check supervisor status
- `POST /v1/chat?entity=supervisor` - Chat with supervisor
- `GET /health` - System health check

## Example Workflow

```bash
# 1. Submit task
task_id=$(curl -s -X POST localhost:8000/v1/task \
  -H "Content-Type: application/json" \
  -d '{"brief":"Add Redis caching","user_id":"dev"}' | jq -r .task_id)

# 2. Monitor progress
curl localhost:8000/v1/supervisor/status

# 3. Check git branches
git branch -a | grep task/

# 4. Review generated PR
```

## Configuration

Supervisor uses OpenAI for task planning by default. Configure in:
- `entities/supervisor/identity/identity.json`
- Environment variables (OPENAI_API_KEY)

## Next Steps

Once the basic system is running, you can:
1. Enhance code generation in worker
2. Add more sophisticated task validation
3. Implement PR automation
4. Expand to multiple workers
5. Add task prioritization and dependencies

## Development Mode

For testing without Redis:
```python
# Mock queue operations for development
from core.task_queue.queue import push, pop
```

The system is designed to bootstrap itself - once running, you can submit tasks to improve the supervisor system itself! 🚀 