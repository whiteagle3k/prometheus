"""
Minimal Redis-based task queue for supervisor-agent coordination.
"""

import json
import os
from typing import Any, Dict

try:
    import redis
except ImportError:
    print("Warning: redis not installed. Task queue will not work.")
    redis = None

# Redis connection - lazy initialization
_redis_client = None

def get_redis_client():
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        if not redis:
            raise RuntimeError("redis package not installed")
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.from_url(redis_url)
        
        # Test connection
        try:
            _redis_client.ping()
            print(f"✅ Connected to Redis: {redis_url}")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            raise
    
    return _redis_client

def push(queue_name: str, obj: Dict[str, Any]) -> None:
    """Push object to queue (FIFO - left push)."""
    r = get_redis_client()
    serialized = json.dumps(obj)
    r.lpush(queue_name, serialized)

def pop(queue_name: str) -> Dict[str, Any]:
    """Pop object from queue (blocking right pop)."""
    r = get_redis_client()
    _, serialized = r.brpop(queue_name, 0)  # 0 = block indefinitely
    return json.loads(serialized)

def peek(queue_name: str) -> Dict[str, Any] | None:
    """Peek at next item without removing it."""
    r = get_redis_client()
    serialized = r.lindex(queue_name, -1)  # Right-most (next to be popped)
    return json.loads(serialized) if serialized else None

def queue_length(queue_name: str) -> int:
    """Get queue length."""
    r = get_redis_client()
    return r.llen(queue_name)

def clear_queue(queue_name: str) -> int:
    """Clear all items from queue. Returns number of items removed."""
    r = get_redis_client()
    return r.delete(queue_name)

# Queue name constants
HIGHLEVEL_IN = "highlevel:in"
DEVTASKS_WAITING = "devtasks:waiting"
DEVTASKS_PROCESSING = "devtasks:processing"
DEVTASKS_DONE = "devtasks:done"
DEVTASKS_DONE_LOCAL = "devtasks:done_local"  # Local completion without push
DEVTASKS_FAILED = "devtasks:failed"
PUBLISH_REQUESTS = "publish:requests"  # For offline publish requests 