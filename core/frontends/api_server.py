"""
Universal API Server

Provides REST API endpoints for interacting with any entity.
Uses runtime registry to support multiple agents simultaneously.
"""

import json
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

from core.runtime.registry import get_agent, get_registry_stats, get_running_agents

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",  # We'll use JSON format
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class StructuredLogger:
    """Structured JSON logger for request tracing."""

    @staticmethod
    def log_request(request_id: str, method: str, path: str, entity: str | None = None, user_id: str | None = None):
        """Log incoming request."""
        log_data = {
            "timestamp": time.time(),
            "level": "INFO",
            "event": "request_start",
            "request_id": request_id,
            "method": method,
            "path": path,
            "entity": entity,
            "user_id": user_id,
            "service": "universal-api"
        }
        logger.info(json.dumps(log_data))

    @staticmethod
    def log_response(request_id: str, status_code: int, latency: float, entity: str | None = None, route: str | None = None):
        """Log response with metrics."""
        log_data = {
            "timestamp": time.time(),
            "level": "INFO",
            "event": "request_complete",
            "request_id": request_id,
            "status_code": status_code,
            "latency_seconds": latency,
            "entity": entity,
            "route": route,
            "service": "universal-api"
        }
        logger.info(json.dumps(log_data))

    @staticmethod
    def log_error(request_id: str, error: str, entity: str | None = None, user_id: str | None = None):
        """Log error with context."""
        log_data = {
            "timestamp": time.time(),
            "level": "ERROR",
            "event": "request_error",
            "request_id": request_id,
            "error": error,
            "entity": entity,
            "user_id": user_id,
            "service": "universal-api"
        }
        logger.error(json.dumps(log_data))


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    user_id: str = Field(..., max_length=100, description="User identifier")
    message: str = Field(..., max_length=4000, description="User message (max 4KB)")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    answer: str
    entity: str
    route: str
    latency: float
    request_id: str


class TaskBrief(BaseModel):
    """Request model for task submission to supervisor."""
    brief: str = Field(..., max_length=2000, description="High-level task description")
    context: str = Field(default="", max_length=1000, description="Additional context")
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$", description="Task priority")
    user_id: str = Field(..., max_length=100, description="User identifier")


class TaskResponse(BaseModel):
    """Response model for task submission."""
    task_id: str
    status: str
    brief: str
    priority: str
    queued_at: str
    request_id: str


class TaskDiff(BaseModel):
    """Response model for task diff."""
    task_id: str
    branch: str
    diff: str
    timestamp: str
    available: bool


class PublishResponse(BaseModel):
    """Response model for task publication."""
    status: str
    message: str
    task_id: str
    branch: str | None = None
    git_output: str | None = None


# Create FastAPI application
app = FastAPI(
    title="Prometheus Universal AI Service",
    description="RESTful API for multiple autonomous AI agents",
    version="0.6.0"
)

# Add security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Prometheus metrics instrumentation
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=[".*admin.*", "/metrics"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="inprogress",
    inprogress_labels=True,
)

# Custom metrics with entity labels
route_decisions = Counter(
    "prometheus_route_decisions_total",
    "Route decisions made by agents",
    ["route", "user_id", "frontend", "entity"]
)

llm_processing_time = Histogram(
    "prometheus_llm_processing_seconds",
    "Time spent in LLM processing",
    ["route", "approach", "frontend", "entity"]
)

memory_operations = Counter(
    "prometheus_memory_operations_total",
    "Memory operations performed",
    ["operation_type", "user_id", "frontend", "entity"]
)

request_duration = Histogram(
    "prometheus_api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint", "status_code", "entity"]
)

# Instrument the FastAPI app
instrumentator.instrument(app)

# Initialize structured logger
structured_logger = StructuredLogger()


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Structured logging middleware with request IDs."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()

    # Extract entity from query params
    entity_name = request.query_params.get("entity", "aletheia")

    # Log incoming request
    structured_logger.log_request(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        entity=entity_name
    )

    try:
        response = await call_next(request)

        # Calculate latency
        latency = time.time() - start_time

        # Log successful response
        structured_logger.log_response(
            request_id=request_id,
            status_code=response.status_code,
            latency=latency,
            entity=entity_name
        )

        # Add request ID to response
        response.headers["X-Request-ID"] = request_id

        # Update metrics
        request_duration.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            entity=entity_name
        ).observe(latency)

        return response

    except Exception as e:
        # Log error
        structured_logger.log_error(
            request_id=request_id,
            error=str(e),
            entity=entity_name
        )
        raise


@app.middleware("http")
async def limit_body_size_middleware(request: Request, call_next):
    """Limit request body size to 4KB for DOS protection."""
    content_length = request.headers.get("content-length")
    if content_length:
        content_length = int(content_length)
        if content_length > 4096:  # 4KB limit
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Request body too large",
                    "max_size": "4KB",
                    "received_size": f"{content_length}B"
                }
            )

    return await call_next(request)


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Prometheus Universal AI Service",
        "version": "0.6.0",
        "status": "running",
        "running_agents": get_running_agents(),
        "agent_count": len(get_running_agents()),
        "endpoints": {
            "chat": "/v1/chat?entity=<entity_name>",
            "task_submission": "/v1/task",
            "task_diff": "/v1/task/{task_id}/diff",
            "task_publish": "/v1/task/{task_id}/publish",
            "supervisor_status": "/v1/supervisor/status",
            "supervisor_start": "/v1/supervisor/start",
            "registry": "/v1/registry",
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from core.runtime.lifecycle import system_health_check

    try:
        health_report = await system_health_check()
        status_code = 200 if health_report["overall_status"] == "healthy" else 503

        return JSONResponse(
            status_code=status_code,
            content={
                "status": health_report["overall_status"],
                "timestamp": health_report["timestamp"],
                "running_agents": health_report["running_agents"],
                "agent_count": health_report["agent_count"],
                "checks": health_report["checks"]
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )


@app.get("/v1/registry")
async def registry_info():
    """Get agent registry information."""
    return get_registry_stats()


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    entity: str = Query(default="aletheia", description="Entity name to chat with")
) -> ChatResponse:
    """
    Chat with any AI agent entity.

    Args:
        request: Chat request with user_id and message
        http_request: FastAPI request object for accessing request_id
        entity: Entity name (e.g., "aletheia", "prometheus", "teslabot")

    Returns:
        Chat response with answer, entity, route, latency, and request_id
    """
    start_time = time.time()
    request_id = getattr(http_request.state, "request_id", str(uuid.uuid4()))

    try:
        # Get agent instance from registry
        agent = await get_agent(entity)

        # Process the message with user context
        response = await agent.think(request.message, user_id=request.user_id)

        # Calculate latency
        latency = time.time() - start_time

        # Extract route information if available
        route = "unknown"
        approach = "unknown"
        if hasattr(response, "route_used"):
            route = response.route_used
        elif isinstance(response, dict):
            execution_details = response.get("execution_details", {})
            route = execution_details.get("route_used", "unknown")
            approach = execution_details.get("approach", "unknown")

        # Update Prometheus metrics with entity label
        frontend = "api"
        route_decisions.labels(
            route=route,
            user_id=request.user_id,
            frontend=frontend,
            entity=entity
        ).inc()

        if isinstance(response, dict):
            execution_details = response.get("execution_details", {})
            execution_time = execution_details.get("execution_time", 0)
            if execution_time > 0:
                llm_processing_time.labels(
                    route=route,
                    approach=approach,
                    frontend=frontend,
                    entity=entity
                ).observe(execution_time)

        # Count memory operations if available
        if isinstance(response, dict):
            execution_details = response.get("execution_details", {})
            if execution_details.get("memories_used", 0) > 0:
                memory_operations.labels(
                    operation_type="retrieval",
                    user_id=request.user_id,
                    frontend=frontend,
                    entity=entity
                ).inc()
            if execution_details.get("user_profile_used", False):
                memory_operations.labels(
                    operation_type="profile_access",
                    user_id=request.user_id,
                    frontend=frontend,
                    entity=entity
                ).inc()

        # Extract answer text
        answer = str(response)
        if isinstance(response, dict) and "result" in response:
            answer = response["result"]

        return ChatResponse(
            answer=answer,
            entity=entity,
            route=route,
            latency=latency,
            request_id=request_id
        )

    except ImportError:
        # Entity not found
        latency = time.time() - start_time

        structured_logger.log_error(
            request_id=request_id,
            error=f"Entity '{entity}' not found",
            entity=entity,
            user_id=request.user_id
        )

        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Entity '{entity}' not found",
                "available_entities": get_running_agents(),
                "latency": latency,
                "request_id": request_id
            }
        )

    except Exception as e:
        # Calculate latency even for errors
        latency = time.time() - start_time

        # Track error metrics
        route_decisions.labels(
            route="error",
            user_id=request.user_id,
            frontend="api",
            entity=entity
        ).inc()

        # Log structured error
        structured_logger.log_error(
            request_id=request_id,
            error=str(e),
            entity=entity,
            user_id=request.user_id
        )

        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "entity": entity,
                "latency": latency,
                "user_id": request.user_id,
                "request_id": request_id
            }
        )


@app.post("/v1/task", response_model=TaskResponse)
async def submit_task(
    request: TaskBrief,
    http_request: Request
) -> TaskResponse:
    """
    Submit a high-level development task to the supervisor queue.
    
    Args:
        request: Task brief with description, context, and priority
        http_request: FastAPI request object for accessing request_id
        
    Returns:
        Task response with task_id, status, and metadata
    """
    import uuid
    from datetime import datetime
    from core.task_queue.queue import push, HIGHLEVEL_IN
    
    request_id = getattr(http_request.state, "request_id", str(uuid.uuid4()))
    task_id = str(uuid.uuid4())[:8]
    
    try:
        # Create task object
        task_data = {
            "id": task_id,
            "brief": request.brief,
            "context": request.context,
            "priority": request.priority,
            "user_id": request.user_id,
            "created_at": datetime.now().isoformat(),
            "status": "queued",
            "request_id": request_id
        }
        
        # Push to supervisor queue
        push(HIGHLEVEL_IN, task_data)
        
        # Log task submission
        structured_logger.log_request(
            request_id=request_id,
            method="POST",
            path="/v1/task",
            entity="supervisor"
        )
        
        return TaskResponse(
            task_id=task_id,
            status="queued",
            brief=request.brief,
            priority=request.priority,
            queued_at=task_data["created_at"],
            request_id=request_id
        )
        
    except Exception as e:
        structured_logger.log_error(
            request_id=request_id,
            error=f"Task submission failed: {str(e)}",
            entity="supervisor",
            user_id=request.user_id
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Failed to submit task: {str(e)}",
                "task_id": task_id,
                "request_id": request_id
            }
        )


@app.get("/v1/supervisor/status")
async def supervisor_status():
    """
    Get supervisor status and queue information.
    
    Returns:
        Supervisor status including queue lengths and running state
    """
    try:
        from core.task_queue.queue import queue_length, HIGHLEVEL_IN, DEVTASKS_WAITING, DEVTASKS_PROCESSING, DEVTASKS_DONE, DEVTASKS_DONE_LOCAL, DEVTASKS_FAILED
        
        # Try to get supervisor instance
        supervisor_running = False
        supervisor_status = "unknown"
        
        try:
            supervisor = await get_agent("supervisor")
            if hasattr(supervisor, "get_status"):
                supervisor_info = await supervisor.get_status()
                supervisor_running = supervisor_info.get("supervisor_running", False)
                supervisor_status = supervisor_info.get("entity_status", "unknown")
        except Exception as e:
            supervisor_status = f"error: {str(e)}"
        
        return {
            "supervisor": {
                "running": supervisor_running,
                "status": supervisor_status,
                "entity": "supervisor"
            },
            "queues": {
                "highlevel_pending": queue_length(HIGHLEVEL_IN),
                "tasks_waiting": queue_length(DEVTASKS_WAITING),
                "tasks_processing": queue_length(DEVTASKS_PROCESSING),
                "tasks_done": queue_length(DEVTASKS_DONE),
                "tasks_done_local": queue_length(DEVTASKS_DONE_LOCAL),
                "tasks_failed": queue_length(DEVTASKS_FAILED)
            },
            "system": {
                "timestamp": time.time(),
                "status": "active"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Failed to get supervisor status: {str(e)}",
                "timestamp": time.time()
            }
        )


@app.post("/v1/supervisor/start")
async def start_supervisor():
    """
    Start the supervisor autonomous loop.
    
    Returns:
        Status of the start operation
    """
    try:
        supervisor = await get_agent("supervisor")
        if hasattr(supervisor, "start_autonomous_loop"):
            result = await supervisor.start_autonomous_loop()
            return result
        else:
            return {
                "status": "error",
                "message": "Supervisor does not support autonomous loop"
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Failed to start supervisor: {str(e)}",
                "timestamp": time.time()
            }
        )


@app.get("/v1/task/{task_id}/diff", response_model=TaskDiff)
async def get_task_diff(task_id: str):
    """
    Get diff for a completed task.
    
    Args:
        task_id: Task ID to get diff for
        
    Returns:
        Task diff information including branch and code changes
    """
    try:
        from core.task_queue.queue import get_redis_client
        r = get_redis_client()
        
        # Get diff data from Redis
        diff_data = r.hget("task:diffs", task_id)
        
        if not diff_data:
            return TaskDiff(
                task_id=task_id,
                branch="",
                diff="",
                timestamp="",
                available=False
            )
        
        # Parse stored diff data
        diff_info = json.loads(diff_data.decode())
        
        return TaskDiff(
            task_id=task_id,
            branch=diff_info.get("branch", ""),
            diff=diff_info.get("diff", ""),
            timestamp=diff_info.get("timestamp", ""),
            available=True
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Failed to get task diff: {str(e)}",
                "task_id": task_id
            }
        )


@app.post("/v1/task/{task_id}/publish", response_model=PublishResponse)
async def publish_task(task_id: str):
    """
    Publish a completed task.
    
    Args:
        task_id: Task ID to publish
        
    Returns:
        Publish response with status, message, task_id, branch, and git_output
    """
    try:
        # Get supervisor instance
        supervisor = await get_agent("supervisor")
        
        if not hasattr(supervisor, "publish_task"):
            return PublishResponse(
                status="error",
                message="Supervisor does not support task publishing",
                task_id=task_id,
                branch=None,
                git_output=None
            )
        
        # Call supervisor publish method
        result = await supervisor.publish_task(task_id)
        
        return PublishResponse(
            status=result.get("status", "unknown"),
            message=result.get("message", ""),
            task_id=task_id,
            branch=result.get("branch"),
            git_output=result.get("git_output")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Failed to publish task: {str(e)}",
                "task_id": task_id
            }
        )


# Expose metrics endpoint
@app.on_event("startup")
async def startup():
    """Expose metrics endpoint on startup."""
    instrumentator.expose(app, endpoint="/metrics")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=1,  # workers=1 for registry compatibility
        access_log=False  # Use structured logging
    )
