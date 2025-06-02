"""Hierarchical memory store implementing tiered memory management."""

import asyncio
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from ..config import config
from .vector_store import VectorStore


class MemoryTier(Enum):
    """Memory storage tiers."""
    RAW = "raw"  # Recent detailed memories in ChromaDB
    SUMMARY = "summary"  # Compressed summaries in ChromaDB
    KEY_FACTS = "key_facts"  # Essential facts in ChromaDB
    ARCHIVED = "archived"  # Old memories on disk/S3


@dataclass
class MemoryEntry:
    """Structured memory entry with metadata."""
    id: str
    content: str
    tier: MemoryTier
    timestamp: datetime
    metadata: Dict[str, Any]
    importance_score: float = 0.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None


class HierarchicalMemoryStore:
    """Hierarchical memory management with automatic tiering and compression."""

    def __init__(self, vector_store: VectorStore) -> None:
        """Initialize the hierarchical memory store."""
        self.vector_store = vector_store
        self.archive_dir = Path(config.chroma_persist_dir).parent / "archived_memories"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Tier thresholds (configurable)
        self.raw_memory_limit = 200  # Keep 200 most recent raw memories
        self.summary_memory_limit = 100  # Keep 100 summary memories
        self.key_facts_limit = 50  # Keep 50 essential key facts
        self.archive_after_days = 30  # Archive memories older than 30 days

    async def store_memory(
        self,
        content: str,
        memory_type: str = "experience",
        metadata: Optional[Dict[str, Any]] = None,
        importance_score: float = 0.0,
    ) -> str:
        """Store a new memory and trigger tiering if needed."""
        
        # Store in RAW tier initially
        memory_id = await self.vector_store.store_memory(
            content=content,
            memory_type=f"raw_{memory_type}",
            metadata={
                **(metadata or {}),
                "tier": MemoryTier.RAW.value,
                "importance_score": importance_score,
                "access_count": 0,
            }
        )

        # Trigger memory management
        await self._manage_memory_tiers()
        
        return memory_id

    async def search_memories(
        self,
        query: str,
        n_results: int = 5,
        include_tiers: List[MemoryTier] = None,
    ) -> List[Dict[str, Any]]:
        """Search across memory tiers with access tracking."""
        
        if include_tiers is None:
            # Search all tiers by default, prioritizing recent
            include_tiers = [MemoryTier.RAW, MemoryTier.SUMMARY, MemoryTier.KEY_FACTS]
        
        all_results = []
        
        # Search all memories and filter by tier
        all_memories = await self.vector_store.search_memories(
            query=query,
            n_results=n_results * len(include_tiers),  # Get more to filter by tiers
        )
        
        # Filter by requested tiers and add tier information
        for memory in all_memories:
            memory_tier = memory["metadata"].get("tier")
            
            # Check if this memory belongs to one of the requested tiers
            for tier in include_tiers:
                if memory_tier == tier.value:
                    memory["tier"] = tier.value
                    
                    # Add tier boost for scoring
                    if tier == MemoryTier.RAW:
                        memory["tier_boost"] = 1.0
                    elif tier == MemoryTier.SUMMARY:
                        memory["tier_boost"] = 0.8
                    elif tier == MemoryTier.KEY_FACTS:
                        memory["tier_boost"] = 1.2  # Key facts are most important
                    else:
                        memory["tier_boost"] = 0.5
                    
                    all_results.append(memory)
                    break
        
        # Sort by relevance with tier boosting
        all_results.sort(key=lambda x: (x.get("tier_boost", 0.5) * (1 - x.get("distance", 1.0))), reverse=True)
        
        # Update access tracking for returned results
        for result in all_results[:n_results]:
            await self._update_access_tracking(result["id"])
        
        return all_results[:n_results]

    async def _manage_memory_tiers(self) -> None:
        """Manage memory tiers and perform automatic compression/archiving."""
        
        try:
            # 1. Check if raw memories need compression
            await self._compress_raw_memories()
            
            # 2. Check if summaries need key fact extraction
            await self._extract_key_facts()
            
            # 3. Archive old memories
            await self._archive_old_memories()
            
            # 4. Cleanup if still over limits
            await self._enforce_tier_limits()
            
        except Exception as e:
            print(f"⚠️  Error managing memory tiers: {e}")

    async def _compress_raw_memories(self) -> None:
        """Compress old raw memories into summaries."""
        
        # Get raw memories older than 7 days
        cutoff_date = datetime.now() - timedelta(days=7)
        
        old_raw_memories = await self._get_memories_by_age_and_tier(
            tier=MemoryTier.RAW,
            older_than=cutoff_date,
            limit=50  # Process in batches
        )
        
        if len(old_raw_memories) < 5:  # Need minimum batch for meaningful summary
            return
        
        print(f"🗜️  Compressing {len(old_raw_memories)} raw memories into summary...")
        
        # Group related memories for better summarization
        memory_groups = self._group_related_memories(old_raw_memories)
        
        for group in memory_groups:
            summary = await self._create_memory_summary(group)
            if summary:
                # Store as summary tier
                await self.vector_store.store_memory(
                    content=summary["content"],
                    memory_type=f"summary_{summary['type']}",
                    metadata={
                        "tier": MemoryTier.SUMMARY.value,
                        "original_count": len(group),
                        "compression_date": datetime.now().isoformat(),
                        "importance_score": summary["importance_score"],
                        "time_range": summary["time_range"],
                    }
                )
                
                # Delete original raw memories
                for memory in group:
                    await self._delete_memory(memory["id"])

    async def _extract_key_facts(self) -> None:
        """Extract key facts from summaries."""
        
        # Get summaries older than 14 days
        cutoff_date = datetime.now() - timedelta(days=14)
        
        old_summaries = await self._get_memories_by_age_and_tier(
            tier=MemoryTier.SUMMARY,
            older_than=cutoff_date,
            limit=20
        )
        
        if len(old_summaries) < 3:
            return
        
        print(f"🔑 Extracting key facts from {len(old_summaries)} summaries...")
        
        key_facts = await self._extract_essential_facts(old_summaries)
        
        if key_facts:
            # Store as key facts
            await self.vector_store.store_memory(
                content=key_facts["content"],
                memory_type=f"key_facts_{key_facts['domain']}",
                metadata={
                    "tier": MemoryTier.KEY_FACTS.value,
                    "extraction_date": datetime.now().isoformat(),
                    "source_summaries": len(old_summaries),
                    "importance_score": key_facts["importance_score"],
                    "domains": key_facts["domains"],
                }
            )
            
            # Delete original summaries
            for summary in old_summaries:
                await self._delete_memory(summary["id"])

    async def _archive_old_memories(self) -> None:
        """Archive very old memories to disk."""
        
        cutoff_date = datetime.now() - timedelta(days=self.archive_after_days)
        
        # Archive old summaries and key facts
        for tier in [MemoryTier.SUMMARY, MemoryTier.KEY_FACTS]:
            old_memories = await self._get_memories_by_age_and_tier(
                tier=tier,
                older_than=cutoff_date,
                limit=100
            )
            
            if old_memories:
                print(f"📦 Archiving {len(old_memories)} {tier.value} memories to disk...")
                await self._archive_to_disk(old_memories, tier)
                
                # Delete from ChromaDB
                for memory in old_memories:
                    await self._delete_memory(memory["id"])

    async def _enforce_tier_limits(self) -> None:
        """Enforce maximum limits for each tier."""
        
        # Check raw memory limit
        raw_count = await self._count_memories_by_tier(MemoryTier.RAW)
        if raw_count > self.raw_memory_limit:
            excess = raw_count - self.raw_memory_limit
            await self._delete_oldest_memories(MemoryTier.RAW, excess)
            print(f"🗑️  Deleted {excess} excess raw memories")
        
        # Check summary limit
        summary_count = await self._count_memories_by_tier(MemoryTier.SUMMARY)
        if summary_count > self.summary_memory_limit:
            excess = summary_count - self.summary_memory_limit
            await self._delete_oldest_memories(MemoryTier.SUMMARY, excess)
            print(f"🗑️  Deleted {excess} excess summary memories")
        
        # Check key facts limit
        facts_count = await self._count_memories_by_tier(MemoryTier.KEY_FACTS)
        if facts_count > self.key_facts_limit:
            excess = facts_count - self.key_facts_limit
            await self._delete_oldest_memories(MemoryTier.KEY_FACTS, excess)
            print(f"🗑️  Deleted {excess} excess key fact memories")

    # Helper methods

    async def _get_memories_by_age_and_tier(
        self,
        tier: MemoryTier,
        older_than: datetime,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get memories from specific tier older than date."""
        
        # Get actual collection size to avoid over-requesting
        collection_count = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.vector_store.memory_collection.count(),
        )
        
        # Adjust limit to not exceed available entries
        actual_limit = min(limit * 2, collection_count) if collection_count > 0 else 0
        
        if actual_limit == 0:
            return []
        
        # This is a simplified implementation - would need more sophisticated filtering
        all_memories = await self.vector_store.search_memories(
            query="*",  # Get all
            n_results=actual_limit,  # Use adjusted limit
        )
        
        filtered = []
        for memory in all_memories:
            # Check tier
            if memory["metadata"].get("tier") != tier.value:
                continue
                
            # Check age
            timestamp_str = memory["metadata"].get("timestamp", "")
            if timestamp_str:
                try:
                    memory_date = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    if memory_date < older_than:
                        filtered.append(memory)
                        if len(filtered) >= limit:
                            break
                except ValueError:
                    continue
        
        return filtered

    def _group_related_memories(self, memories: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group related memories for better summarization."""
        
        # Simple grouping by topic/session - could be more sophisticated
        groups = {}
        
        for memory in memories:
            # Group by session_id or topic
            session_id = memory["metadata"].get("session_id", "unknown")
            topic = memory["metadata"].get("current_topic", "general")
            
            group_key = f"{session_id}_{topic}"
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(memory)
        
        # Return groups with at least 3 memories
        return [group for group in groups.values() if len(group) >= 3]

    async def _create_memory_summary(self, memories: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Create a summary from a group of related memories."""
        
        # Extract key information
        contents = [mem["content"] for mem in memories]
        timestamps = [mem["metadata"].get("timestamp", "") for mem in memories]
        
        # Analyze LLM sources in this group
        llm_sources = {}
        for mem in memories:
            source = mem["metadata"].get("llm_source", "unknown")
            provider = mem["metadata"].get("llm_provider", "unknown")
            llm_sources[f"{source}_{provider}"] = llm_sources.get(f"{source}_{provider}", 0) + 1
        
        # Create summary content with enhanced source tracking
        summary_content = f"""Memory Summary ({len(memories)} entries)
Time Range: {min(timestamps)} to {max(timestamps)}

LLM Sources: {', '.join([f"{k}: {v}" for k, v in llm_sources.items()])}

Key Interactions:
{chr(10).join([f"- {content[:100]}..." for content in contents[:5]])}

Common Patterns:
- Session involved {len(set(mem['metadata'].get('session_id', '') for mem in memories))} sessions
- Average response time: {sum(float(mem['metadata'].get('execution_time', 0)) for mem in memories) / len(memories):.2f}s
- External routing: {sum(1 for mem in memories if mem['metadata'].get('llm_source') == 'external')}/{len(memories)} times
- Average importance: {sum(float(mem['metadata'].get('importance_score', 0.5)) for mem in memories) / len(memories):.2f}
"""
        
        # Calculate importance score - boost if contains external LLM results
        external_count = sum(1 for mem in memories if mem["metadata"].get("llm_source") == "external")
        base_importance = sum(float(mem["metadata"].get("importance_score", 0.5)) for mem in memories) / len(memories)
        
        # Boost importance if this summary contains valuable external results
        if external_count > 0:
            external_ratio = external_count / len(memories)
            importance_score = min(base_importance + (external_ratio * 0.3), 1.0)
        else:
            importance_score = base_importance
        
        return {
            "content": summary_content,
            "type": memories[0]["metadata"].get("memory_type", "general"),
            "importance_score": importance_score,
            "time_range": f"{min(timestamps)} to {max(timestamps)}",
            "llm_sources": llm_sources,
            "external_ratio": external_count / len(memories) if memories else 0.0
        }

    async def _extract_essential_facts(self, summaries: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract key facts from summaries."""
        
        # Combine summaries
        combined_content = "\n\n".join([summary["content"] for summary in summaries])
        
        # Extract domains
        domains = set()
        for summary in summaries:
            summary_type = summary["metadata"].get("type", "")
            if summary_type:
                domains.add(summary_type.replace("summary_", ""))
        
        # Create key facts content
        key_facts_content = f"""Essential Knowledge ({len(summaries)} summaries processed)
Domains: {', '.join(domains)}
Extracted: {datetime.now().isoformat()}

Key Patterns and Learnings:
{combined_content[:500]}...

Success Patterns:
- Most successful routing decisions
- Common user preferences 
- Effective response strategies
- Technical knowledge areas
"""
        
        importance_score = max(float(s["metadata"].get("importance_score", 0.5)) for s in summaries)
        
        return {
            "content": key_facts_content,
            "domain": "_".join(list(domains)[:3]),  # Top 3 domains
            "importance_score": importance_score,
            "domains": list(domains)
        }

    async def _archive_to_disk(self, memories: List[Dict[str, Any]], tier: MemoryTier) -> None:
        """Archive memories to disk storage."""
        
        archive_file = self.archive_dir / f"{tier.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        
        try:
            # Save as pickle for efficient storage/retrieval
            with open(archive_file, 'wb') as f:
                pickle.dump(memories, f)
            
            # Also save metadata as JSON for easy inspection
            metadata_file = archive_file.with_suffix('.json')
            metadata = {
                "tier": tier.value,
                "count": len(memories),
                "archived_date": datetime.now().isoformat(),
                "file": str(archive_file),
                "memory_ids": [mem["id"] for mem in memories]
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            print(f"⚠️  Error archiving to disk: {e}")

    async def _count_memories_by_tier(self, tier: MemoryTier) -> int:
        """Count memories in a specific tier."""
        
        # Get actual collection size to avoid over-requesting
        collection_count = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.vector_store.memory_collection.count(),
        )
        
        if collection_count == 0:
            return 0
        
        # Get all memories and count by tier metadata
        all_memories = await self.vector_store.search_memories(
            query="*",  # Get all memories
            n_results=collection_count,  # Use actual collection size
        )
        
        return sum(1 for mem in all_memories if mem["metadata"].get("tier") == tier.value)

    async def _delete_oldest_memories(self, tier: MemoryTier, count: int) -> None:
        """Delete oldest memories from a tier."""
        
        # Get all memories from tier, sorted by age
        memories = await self._get_memories_by_age_and_tier(
            tier=tier,
            older_than=datetime.now(),  # All memories
            limit=count
        )
        
        # Delete oldest ones
        for memory in memories[:count]:
            await self._delete_memory(memory["id"])

    async def _delete_memory(self, memory_id: str) -> None:
        """Delete a memory by ID."""
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.vector_store.memory_collection.delete(ids=[memory_id])
            )
        except Exception as e:
            print(f"⚠️  Error deleting memory {memory_id}: {e}")

    async def _update_access_tracking(self, memory_id: str) -> None:
        """Update access count and last accessed time for a memory."""
        
        # This would require updating metadata in ChromaDB
        # For now, just track that it was accessed
        pass

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        
        total_count = await self.vector_store.get_memory_count()
        
        raw_count = await self._count_memories_by_tier(MemoryTier.RAW)
        summary_count = await self._count_memories_by_tier(MemoryTier.SUMMARY)
        facts_count = await self._count_memories_by_tier(MemoryTier.KEY_FACTS)
        
        # Count archived files
        archived_files = list(self.archive_dir.glob("*.pkl"))
        
        return {
            "total_active_memories": total_count,
            "raw_memories": raw_count,
            "summary_memories": summary_count,
            "key_facts": facts_count,
            "archived_files": len(archived_files),
            "archive_directory": str(self.archive_dir),
            "tier_limits": {
                "raw": self.raw_memory_limit,
                "summary": self.summary_memory_limit,
                "key_facts": self.key_facts_limit,
            }
        } 