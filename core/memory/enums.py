"""Memory system enums for the three-tier context architecture."""

from enum import Enum


class MemoryTier(Enum):
    """Three-tier context system for memory storage and retrieval.
    
    Retrieval priority order: CORE_SELF -> USER -> ENV
    """
    CORE_SELF = "core_self"  # Aletheia's autobiographical memory, self-reflection, skills
    USER = "user"           # Per-user conversation history and preferences
    ENV = "environment"     # External sensor/API data and events


class MemoryType(Enum):
    """Types of memories for classification and storage."""
    # Core-Self types
    SELF_REFLECTION = "self_reflection"
    SKILL_ACQUISITION = "skill_acquisition"
    INTERNAL_GOAL = "internal_goal"
    SYSTEM_LEARNING = "system_learning"
    
    # User types
    CONVERSATION = "conversation"
    USER_PREFERENCE = "user_preference"
    USER_DATA = "user_data"
    USER_FEEDBACK = "user_feedback"
    
    # Environment types
    SENSOR_DATA = "sensor_data"
    API_EVENT = "api_event"
    EXTERNAL_UPDATE = "external_update"
    SYSTEM_EVENT = "system_event" 