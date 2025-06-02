"""Memory system data models for the three-tier context architecture."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, List
from .enums import MemoryTier, MemoryType


@dataclass
class MemoryChunk:
    """Core memory storage unit for the three-tier system.
    
    Each chunk contains content, embedding, tier assignment, and metadata
    for efficient storage and retrieval across Core-Self, User, and Environment contexts.
    """
    id: str
    text: str
    embedding: List[float]
    tier: MemoryTier
    memory_type: MemoryType
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    is_summary: bool = False
    confidence: float = 1.0
    source: str = ""
    
    def __post_init__(self):
        """Ensure required metadata fields are present."""
        if "user_id" not in self.metadata and self.tier == MemoryTier.USER:
            self.metadata["user_id"] = "default"
        if "timestamp" not in self.metadata:
            self.metadata["timestamp"] = self.timestamp.isoformat()


@dataclass
class RetrievalResult:
    """Result from memory retrieval with tier information and scoring."""
    chunks: List[MemoryChunk]
    tier_counts: dict[MemoryTier, int] = field(default_factory=dict)
    total_retrieved: int = 0
    search_query: str = ""
    
    def __post_init__(self):
        """Calculate tier counts and total."""
        self.tier_counts = {}
        for tier in MemoryTier:
            self.tier_counts[tier] = sum(1 for chunk in self.chunks if chunk.tier == tier)
        self.total_retrieved = len(self.chunks)


@dataclass
class MemoryStats:
    """Statistics for memory system monitoring."""
    core_self_count: int = 0
    user_count: int = 0
    env_count: int = 0
    total_count: int = 0
    summaries_count: int = 0
    last_summarization: Optional[datetime] = None
    
    def __post_init__(self):
        """Calculate total count."""
        self.total_count = self.core_self_count + self.user_count + self.env_count


@dataclass
class TierConfig:
    """Configuration for a memory tier."""
    max_chunks: int
    similarity_threshold: float
    summarization_ratio: float = 0.1  # Keep 10% when summarizing
    collection_name: str = ""
    
    def __post_init__(self):
        """Set default collection name if not provided."""
        if not self.collection_name:
            if hasattr(self, 'tier'):
                self.collection_name = f"aletheia_{self.tier.value}"


# Default tier configurations
DEFAULT_TIER_CONFIGS = {
    MemoryTier.CORE_SELF: TierConfig(
        max_chunks=500,
        similarity_threshold=0.75,
        collection_name="aletheia_core_self"
    ),
    MemoryTier.USER: TierConfig(
        max_chunks=1000,
        similarity_threshold=0.70,
        collection_name="aletheia_user"
    ),
    MemoryTier.ENV: TierConfig(
        max_chunks=300,
        similarity_threshold=0.65,
        collection_name="aletheia_environment"
    )
} 