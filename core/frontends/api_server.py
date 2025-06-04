"""
Universal API Server

Provides REST API endpoints for interacting with any entity.
Uses runtime registry to support multiple agents simultaneously.
"""

import json
import logging
import time
import uuid
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram

from ..runtime.registry import get_agent, get_running_agents, get_registry_stats

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',  # We'll use JSON format
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class StructuredLogger:
    """Structured JSON logger for request tracing."""
    
    @staticmethod
    def log_request(request_id: str, method: str, path: str, entity: str = None, user_id: str = None):
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
    def log_response(request_id: str, status_code: int, latency: float, entity: str = None, route: str = None):
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
    def log_error(request_id: str, error: str, entity: str = None, user_id: str = None):
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
    'prometheus_route_decisions_total',
    'Route decisions made by agents',
    ['route', 'user_id', 'frontend', 'entity']
)

llm_processing_time = Histogram(
    'prometheus_llm_processing_seconds',
    'Time spent in LLM processing',
    ['route', 'approach', 'frontend', 'entity']
)

memory_operations = Counter(
    'prometheus_memory_operations_total',
    'Memory operations performed',
    ['operation_type', 'user_id', 'frontend', 'entity']
)

request_duration = Histogram(
    'prometheus_api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint', 'status_code', 'entity']
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
    entity_name = request.query_params.get('entity', 'aletheia')
    
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
    content_length = request.headers.get('content-length')
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
            "registry": "/v1/registry",
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from ..runtime.lifecycle import system_health_check
    
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
    request_id = getattr(http_request.state, 'request_id', str(uuid.uuid4()))
    
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
        if hasattr(response, 'route_used'):
            route = response.route_used
        elif isinstance(response, dict):
            execution_details = response.get('execution_details', {})
            route = execution_details.get('route_used', 'unknown')
            approach = execution_details.get('approach', 'unknown')
        
        # Update Prometheus metrics with entity label
        frontend = "api"
        route_decisions.labels(
            route=route, 
            user_id=request.user_id, 
            frontend=frontend, 
            entity=entity
        ).inc()
        
        if isinstance(response, dict):
            execution_details = response.get('execution_details', {})
            execution_time = execution_details.get('execution_time', 0)
            if execution_time > 0:
                llm_processing_time.labels(
                    route=route, 
                    approach=approach, 
                    frontend=frontend,
                    entity=entity
                ).observe(execution_time)
        
        # Count memory operations if available
        if isinstance(response, dict):
            execution_details = response.get('execution_details', {})
            if execution_details.get('memories_used', 0) > 0:
                memory_operations.labels(
                    operation_type='retrieval', 
                    user_id=request.user_id, 
                    frontend=frontend,
                    entity=entity
                ).inc()
            if execution_details.get('user_profile_used', False):
                memory_operations.labels(
                    operation_type='profile_access', 
                    user_id=request.user_id, 
                    frontend=frontend,
                    entity=entity
                ).inc()
        
        # Extract answer text
        answer = str(response)
        if isinstance(response, dict) and 'result' in response:
            answer = response['result']
        
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
            route='error', 
            user_id=request.user_id, 
            frontend='api',
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