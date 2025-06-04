"""
FastAPI Server for Aletheia Service

Provides REST API endpoints for interacting with Aletheia.
Uses singleton service to share instance across requests.
"""

import time
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .singleton import get_agent


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    user_id: str
    message: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    answer: str
    route: str
    latency: float


# Create FastAPI application
app = FastAPI(
    title="Aletheia AI Service",
    description="RESTful API for Aletheia autonomous AI agent",
    version="0.6.0"
)

# Add CORS middleware for web frontend compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Aletheia AI Service",
        "version": "0.6.0",
        "status": "running",
        "endpoints": {
            "chat": "/v1/chat",
            "docs": "/docs",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat with Aletheia AI agent.
    
    Args:
        request: Chat request with user_id and message
        
    Returns:
        Chat response with answer, route, and latency
    """
    start_time = time.time()
    
    try:
        # Get singleton agent instance
        agent = await get_agent()
        
        # Process the message with user context
        response = await agent.think(request.message, user_id=request.user_id)
        
        # Calculate latency
        latency = time.time() - start_time
        
        # Extract route information if available
        route = "unknown"
        if hasattr(response, 'route_used'):
            route = response.route_used
        elif isinstance(response, dict) and 'route_used' in response:
            route = response['route_used']
        
        # Extract answer text
        answer = str(response)
        if isinstance(response, dict) and 'result' in response:
            answer = response['result']
        
        return ChatResponse(
            answer=answer,
            route=route,
            latency=latency
        )
        
    except Exception as e:
        # Calculate latency even for errors
        latency = time.time() - start_time
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "latency": latency,
                "user_id": request.user_id
            }
        )


# TODO: Mount static documentation files
# app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 