"""Memory Controller - Unified API for three-tier context system.

Implements Core-Self, User, and Environment memory tiers with intelligent
retrieval ordering and automatic classification for write-back.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from .enums import MemoryTier, MemoryType
from .models import MemoryChunk, RetrievalResult, MemoryStats, DEFAULT_TIER_CONFIGS, TierConfig
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class MemoryController:
    """Unified controller for three-tier memory system.
    
    Manages Core-Self (Aletheia's autobiographical memory), User (per-user context),
    and Environment (external sensor/API data) tiers with intelligent retrieval
    and automatic classification.
    """
    
    def __init__(self, tier_configs: Optional[Dict[MemoryTier, TierConfig]] = None):
        """Initialize memory controller with tier configurations."""
        self.tier_configs = tier_configs or DEFAULT_TIER_CONFIGS
        self.stores: Dict[MemoryTier, VectorStore] = {}
        self.current_user_id = "default"
        self._summarization_lock = asyncio.Lock()
        
        # Initialize vector stores for each tier
        # Note: Current VectorStore doesn't support custom collections,
        # so we'll use a unified store with tier-based metadata filtering
        self.unified_store = VectorStore()
        
        # For now, use the same store for all tiers with metadata filtering
        for tier in MemoryTier:
            self.stores[tier] = self.unified_store
    
    async def retrieve(self, query: str, k: int = 6, user_id: Optional[str] = None) -> RetrievalResult:
        """Retrieve memories from all tiers with priority ordering.
        
        Retrieval strategy:
        1. Search CORE_SELF (threshold 0.75)
        2. If <k hits, search USER (threshold 0.7) 
        3. If still <k, search ENV (threshold 0.65)
        
        Returns merged list maintaining original tier priority.
        """
        if user_id:
            self.current_user_id = user_id
            
        all_chunks = []
        retrieved_count = 0
        
        # Step 1: Core-Self context (highest priority)
        if retrieved_count < k:
            core_chunks = await self._search_tier(
                MemoryTier.CORE_SELF, 
                query, 
                min(k, k - retrieved_count)
            )
            all_chunks.extend(core_chunks)
            retrieved_count += len(core_chunks)
            logger.debug(f"Retrieved {len(core_chunks)} from Core-Self tier")
        
        # Step 2: User context (medium priority)
        if retrieved_count < k:
            user_chunks = await self._search_tier(
                MemoryTier.USER, 
                query, 
                k - retrieved_count,
                user_filter=self.current_user_id
            )
            all_chunks.extend(user_chunks)
            retrieved_count += len(user_chunks)
            logger.debug(f"Retrieved {len(user_chunks)} from User tier")
        
        # Step 3: Environment context (lowest priority)
        if retrieved_count < k:
            env_chunks = await self._search_tier(
                MemoryTier.ENV, 
                query, 
                k - retrieved_count
            )
            all_chunks.extend(env_chunks)
            retrieved_count += len(env_chunks)
            logger.debug(f"Retrieved {len(env_chunks)} from Environment tier")
        
        result = RetrievalResult(chunks=all_chunks, search_query=query)
        logger.info(f"Total retrieved: {result.total_retrieved} chunks across {len(result.tier_counts)} tiers")
        return result
    
    async def store(self, chunk: MemoryChunk, tier: Optional[MemoryTier] = None) -> str:
        """Store memory chunk in specified tier or auto-classify.
        
        If tier not specified, uses classification logic:
        - Self-reflection terms → CORE_SELF
        - User utterance/agent reply → USER  
        - External event indicators → ENV
        """
        if tier is None:
            tier = self._classify_memory_tier(chunk)
            chunk.tier = tier
        
        # Ensure user_id for USER tier
        if tier == MemoryTier.USER and "user_id" not in chunk.metadata:
            chunk.metadata["user_id"] = self.current_user_id
        
        # Add tier information to metadata for filtering
        chunk.metadata["memory_tier"] = tier.value
        chunk.metadata["memory_type"] = chunk.memory_type.value
        
        # Store in unified store with tier metadata
        store = self.stores[tier]
        memory_id = await store.store_memory(
            content=chunk.text,
            memory_type=f"{tier.value}_{chunk.memory_type.value}",
            metadata=chunk.metadata
        )
        
        # Check for overflow and summarize if needed
        await self._check_overflow(tier)
        
        logger.debug(f"Stored memory {memory_id} in {tier.value} tier")
        return memory_id
    
    async def summarise_if_needed(self) -> Dict[MemoryTier, bool]:
        """Check all tiers for overflow and summarize if needed.
        
        Returns dict indicating which tiers were summarized.
        """
        async with self._summarization_lock:
            summary_results = {}
            
            for tier in MemoryTier:
                summary_results[tier] = await self._check_overflow(tier)
            
            return summary_results
    
    async def get_stats(self) -> MemoryStats:
        """Get comprehensive memory statistics across all tiers."""
        stats = MemoryStats()
        
        # Get total memory count from unified store
        total_count = await self.unified_store.get_memory_count()
        
        # For now, estimate tier distribution
        # In a full implementation, we'd query by tier metadata
        stats.core_self_count = total_count // 4  # Estimate
        stats.user_count = total_count // 2      # Estimate 
        stats.env_count = total_count // 4       # Estimate
        
        return stats
    
    async def reset_tier(self, tier: MemoryTier, confirm: bool = False) -> bool:
        """Reset/clear a specific memory tier. Requires confirmation."""
        if not confirm:
            logger.warning(f"Reset of {tier.value} tier requires confirmation=True")
            return False
        
        try:
            # Delete memories by tier metadata
            logger.info(f"Resetting {tier.value} tier...")
            
            # For now, we need to implement deletion by metadata filtering
            # This would require querying by tier metadata and deleting matching records
            # TODO: Implement tier-specific deletion in vector store
            
            logger.warning(f"Tier-specific reset not fully implemented yet for {tier.value}")
            return False
            
        except Exception as e:
            logger.error(f"Error resetting {tier.value} tier: {e}")
            return False
    
    async def reset_user_env_tiers(self, confirm: bool = False) -> bool:
        """Reset USER and ENV tiers while preserving CORE_SELF."""
        if not confirm:
            logger.warning("Reset of user/env tiers requires confirmation=True")
            return False
        
        try:
            logger.info("Resetting USER and ENV tiers, preserving CORE_SELF...")
            
            # Reset USER tier
            user_reset = await self.reset_tier(MemoryTier.USER, confirm=True)
            
            # Reset ENV tier  
            env_reset = await self.reset_tier(MemoryTier.ENV, confirm=True)
            
            if user_reset and env_reset:
                logger.info("Successfully reset USER and ENV tiers")
                return True
            else:
                logger.warning("Partial reset completed - tier-specific reset not fully implemented")
                return False
                
        except Exception as e:
            logger.error(f"Error resetting user/env tiers: {e}")
            return False
    
    async def reset_all_tiers(self, confirm: bool = False) -> bool:
        """Reset ALL memory tiers including CORE_SELF (development only)."""
        if not confirm:
            logger.warning("Complete memory reset requires confirmation=True")
            return False
        
        try:
            logger.warning("🚨 RESETTING ALL MEMORY TIERS INCLUDING CORE_SELF!")
            
            # For now, fall back to complete vector store reset
            await self.unified_store.reset_all()
            logger.info("Complete memory reset finished")
            return True
            
        except Exception as e:
            logger.error(f"Error during complete reset: {e}")
            return False
    
    # Private methods
    
    async def _search_tier(
        self, 
        tier: MemoryTier, 
        query: str, 
        k: int,
        user_filter: Optional[str] = None
    ) -> List[MemoryChunk]:
        """Search a specific tier with threshold filtering."""
        config = self.tier_configs[tier]
        store = self.stores[tier]
        
        try:
            # Search with tier-specific memory type filter
            memory_type_prefix = tier.value
            results = await store.search_memories(
                query=query,
                n_results=k * 2,  # Get more to allow for filtering
                memory_type=memory_type_prefix  # This will help filter by tier
            )
            
            # Convert to MemoryChunk objects and apply filtering
            chunks = []
            for result in results:
                # Filter by tier metadata
                metadata = result.get("metadata", {})
                if metadata.get("memory_tier") == tier.value:
                    
                    # Additional user filtering for USER tier
                    if tier == MemoryTier.USER and user_filter:
                        if metadata.get("user_id") != user_filter:
                            continue
                    
                    # Apply similarity threshold (simplified - using distance if available)
                    distance = result.get("distance", 0.0)
                    similarity = 1.0 - distance if distance is not None else 1.0
                    
                    if similarity >= config.similarity_threshold:
                        chunk = MemoryChunk(
                            id=result.get("id", str(uuid.uuid4())),
                            text=result.get("content", ""),
                            embedding=[],  # Not needed for retrieval
                            tier=tier,
                            memory_type=MemoryType.CONVERSATION,  # Would parse from metadata
                            metadata=metadata,
                            confidence=similarity
                        )
                        chunks.append(chunk)
                        
                        if len(chunks) >= k:
                            break
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error searching {tier.value} tier: {e}")
            return []
    
    def _classify_memory_tier(self, chunk: MemoryChunk) -> MemoryTier:
        """Classify memory into appropriate tier based on content and metadata.
        
        Classification rules:
        - Self-reflection keywords → CORE_SELF
        - User/conversation content → USER
        - External events → ENV
        """
        text_lower = chunk.text.lower()
        
        # Core-Self indicators
        core_self_indicators = [
            "i learned", "i improved", "my skill", "self-reflection", 
            "internal goal", "я изучила", "я улучшила", "мой навык"
        ]
        
        # Environment indicators  
        env_indicators = [
            "sensor", "api", "external", "webhook", "event",
            "датчик", "внешний", "событие"
        ]
        
        # Check for Core-Self
        if any(indicator in text_lower for indicator in core_self_indicators):
            return MemoryTier.CORE_SELF
        
        # Check for Environment
        if any(indicator in text_lower for indicator in env_indicators):
            return MemoryTier.ENV
        
        # Default to User tier for conversation content
        return MemoryTier.USER
    
    async def _check_overflow(self, tier: MemoryTier) -> bool:
        """Check if tier has exceeded max_chunks and summarize if needed."""
        config = self.tier_configs[tier]
        
        # Get current count (simplified - would need actual count by tier)
        current_count = await self._estimate_tier_count(tier)
        
        if current_count > config.max_chunks:
            logger.info(f"Tier {tier.value} overflow detected: {current_count} > {config.max_chunks}")
            await self._summarize_tier(tier)
            return True
        
        return False
    
    async def _summarize_tier(self, tier: MemoryTier) -> None:
        """Summarize oldest memories in a tier when overflow occurs."""
        config = self.tier_configs[tier]
        
        # This is a placeholder - would need actual implementation
        # to retrieve oldest memories, generate summary, and replace them
        logger.info(f"Summarizing tier {tier.value} (placeholder implementation)")
        
        # Steps would be:
        # 1. Get oldest N memories for this tier
        # 2. Generate TL;DR summary using local LLM
        # 3. Create summary chunk with is_summary=True
        # 4. Delete original memories
        # 5. Store summary chunk
    
    async def _estimate_tier_count(self, tier: MemoryTier) -> int:
        """Estimate number of memories in a tier."""
        # Simplified estimation - would need proper tier counting
        total_count = await self.unified_store.get_memory_count()
        
        # Rough estimation based on tier
        if tier == MemoryTier.CORE_SELF:
            return total_count // 4
        elif tier == MemoryTier.USER:
            return total_count // 2
        elif tier == MemoryTier.ENV:
            return total_count // 4
        
        return 0 