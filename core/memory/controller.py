"""Memory Controller - Unified API for three-tier context system.

Implements Core-Self, User, and Environment memory tiers with intelligent
retrieval ordering and automatic classification for write-back.
"""

import asyncio
import contextlib
import gzip
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .enums import MemoryTier, MemoryType
from .models import (
    DEFAULT_TIER_CONFIGS,
    MemoryChunk,
    MemoryStats,
    RetrievalResult,
    TierConfig,
)
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class MemoryController:
    """Unified controller for three-tier memory system.

    Manages Core-Self (Aletheia's autobiographical memory), User (per-user context),
    and Environment (external sensor/API data) tiers with intelligent retrieval
    and automatic classification.
    """

    def __init__(self, tier_configs: dict[MemoryTier, TierConfig] | None = None):
        """Initialize memory controller with tier configurations."""
        self.tier_configs = tier_configs or DEFAULT_TIER_CONFIGS
        self.stores: dict[MemoryTier, VectorStore] = {}
        self.current_user_id = "default"
        self._summarization_lock = asyncio.Lock()
        self._snapshot_lock = asyncio.Lock()

        # Auto-snapshot configuration
        self.enable_auto_snapshots = os.getenv("AUTONOMY_ENABLED", "false").lower() == "true"
        self.snapshot_interval = 3600  # 1 hour in seconds
        self.snapshots_dir = Path("data/snapshots")
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        # Initialize vector stores for each tier
        # Note: Current VectorStore doesn't support custom collections,
        # so we'll use a unified store with tier-based metadata filtering
        self.unified_store = VectorStore()

        # For now, use the same store for all tiers with metadata filtering
        for tier in MemoryTier:
            self.stores[tier] = self.unified_store

        # Start auto-snapshot task if enabled
        self._snapshot_task = None
        if self.enable_auto_snapshots:
            logger.info("🔄 Auto-snapshots enabled (hourly)")
            self._start_auto_snapshot_task()

    def _start_auto_snapshot_task(self):
        """Start the auto-snapshot background task."""
        async def auto_snapshot_loop():
            while True:
                try:
                    await asyncio.sleep(self.snapshot_interval)
                    await self.create_snapshot(auto=True)
                except Exception as e:
                    logger.error(f"Error in auto-snapshot loop: {e}")
                    await asyncio.sleep(60)  # Wait 1 minute before retrying

        self._snapshot_task = asyncio.create_task(auto_snapshot_loop())
        logger.info("✅ Auto-snapshot task started")

    async def create_snapshot(self, auto: bool = False) -> str:
        """
        Create a gzipped snapshot of memory state.

        Args:
            auto: Whether this is an automatic snapshot

        Returns:
            Path to created snapshot file
        """
        async with self._snapshot_lock:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                snapshot_type = "auto" if auto else "manual"
                filename = f"memory_snapshot_{snapshot_type}_{timestamp}.json.gz"
                filepath = self.snapshots_dir / filename

                logger.info(f"📸 Creating memory snapshot: {filename}")

                # Gather memory data from all tiers
                snapshot_data = {
                    "timestamp": datetime.now().isoformat(),
                    "version": "0.6.0",
                    "type": snapshot_type,
                    "tiers": {}
                }

                # For each tier, collect memories
                for tier in MemoryTier:
                    tier_memories = await self._export_tier_memories(tier)
                    snapshot_data["tiers"][tier.value] = {
                        "memory_count": len(tier_memories),
                        "memories": tier_memories
                    }

                # Add metadata
                snapshot_data["metadata"] = {
                    "current_user_id": self.current_user_id,
                    "tier_configs": {
                        tier.value: {
                            "max_chunks": config.max_chunks,
                            "similarity_threshold": config.similarity_threshold
                        }
                        for tier, config in self.tier_configs.items()
                    },
                    "stats": await self._get_snapshot_stats()
                }

                # Write compressed snapshot
                json_data = json.dumps(snapshot_data, indent=2, ensure_ascii=False)

                with gzip.open(filepath, "wt", encoding="utf-8") as f:
                    f.write(json_data)

                # Calculate file size
                file_size = filepath.stat().st_size
                compression_ratio = len(json_data.encode("utf-8")) / file_size

                logger.info(f"✅ Snapshot created: {filename} ({file_size} bytes, {compression_ratio:.1f}x compression)")

                # Cleanup old snapshots (keep last 10)
                await self._cleanup_old_snapshots()

                return str(filepath)

            except Exception as e:
                logger.error(f"❌ Failed to create snapshot: {e}")
                raise

    async def load_snapshot(self, snapshot_path: str) -> bool:
        """
        Load memory state from a snapshot file.

        Args:
            snapshot_path: Path to snapshot file

        Returns:
            True if loaded successfully
        """
        try:
            snapshot_file = Path(snapshot_path)
            if not snapshot_file.exists():
                logger.error(f"Snapshot file not found: {snapshot_path}")
                return False

            logger.info(f"📂 Loading memory snapshot: {snapshot_file.name}")

            # Read compressed snapshot
            with gzip.open(snapshot_file, "rt", encoding="utf-8") as f:
                snapshot_data = json.load(f)

            # Validate snapshot format
            if "version" not in snapshot_data or "tiers" not in snapshot_data:
                logger.error("Invalid snapshot format")
                return False

            # Clear existing memory (with confirmation)
            logger.warning("⚠️ Loading snapshot will clear existing memory")
            await self.reset_all_tiers(confirm=True)

            # Restore memories by tier
            restored_count = 0
            for tier_name, tier_data in snapshot_data["tiers"].items():
                tier = MemoryTier(tier_name)
                memories = tier_data.get("memories", [])

                for memory_data in memories:
                    # Reconstruct memory chunk
                    chunk = MemoryChunk(
                        id=memory_data.get("id", str(uuid.uuid4())),
                        text=memory_data["text"],
                        embedding=[],  # Will be regenerated
                        tier=tier,
                        memory_type=MemoryType(memory_data["memory_type"]),
                        metadata=memory_data.get("metadata", {})
                    )

                    # Store the chunk
                    await self.store(chunk, tier=tier)
                    restored_count += 1

            # Restore metadata
            if "metadata" in snapshot_data:
                metadata = snapshot_data["metadata"]
                self.current_user_id = metadata.get("current_user_id", "default")

            logger.info(f"✅ Snapshot loaded: {restored_count} memories restored")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load snapshot: {e}")
            return False

    async def get_latest_snapshot(self) -> str | None:
        """Get path to the most recent snapshot."""
        try:
            snapshots = list(self.snapshots_dir.glob("memory_snapshot_*.json.gz"))
            if not snapshots:
                return None

            # Sort by modification time (newest first)
            snapshots.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return str(snapshots[0])

        except Exception as e:
            logger.error(f"Error finding latest snapshot: {e}")
            return None

    async def list_snapshots(self) -> list[dict[str, Any]]:
        """List available snapshots with metadata."""
        try:
            snapshots = []
            for snapshot_file in self.snapshots_dir.glob("memory_snapshot_*.json.gz"):
                try:
                    # Quick metadata extraction
                    with gzip.open(snapshot_file, "rt", encoding="utf-8") as f:
                        # Read just the first few lines to get basic info
                        header = f.read(1024)
                        if '"timestamp":' in header and '"type":' in header:
                            # Extract basic info without full parsing
                            import re
                            timestamp_match = re.search(r'"timestamp": "([^"]+)"', header)
                            type_match = re.search(r'"type": "([^"]+)"', header)

                            snapshots.append({
                                "filename": snapshot_file.name,
                                "filepath": str(snapshot_file),
                                "timestamp": timestamp_match.group(1) if timestamp_match else "unknown",
                                "type": type_match.group(1) if type_match else "unknown",
                                "size_bytes": snapshot_file.stat().st_size,
                                "created": datetime.fromtimestamp(snapshot_file.stat().st_ctime).isoformat()
                            })
                except Exception as e:
                    logger.warning(f"Error reading snapshot {snapshot_file.name}: {e}")

            # Sort by creation time (newest first)
            snapshots.sort(key=lambda s: s["created"], reverse=True)
            return snapshots

        except Exception as e:
            logger.error(f"Error listing snapshots: {e}")
            return []

    async def _export_tier_memories(self, tier: MemoryTier) -> list[dict[str, Any]]:
        """Export all memories from a specific tier."""
        try:
            # This is a simplified export - in full implementation,
            # we would query the vector store by tier metadata
            return []

            # For now, return sample structure
            # TODO: Implement actual tier-specific memory export


        except Exception as e:
            logger.error(f"Error exporting tier {tier.value}: {e}")
            return []

    async def _get_snapshot_stats(self) -> dict[str, Any]:
        """Get statistics for snapshot metadata."""
        try:
            total_count = await self.unified_store.get_memory_count()

            return {
                "total_memories": total_count,
                "estimated_tier_distribution": {
                    "core_self": total_count // 4,
                    "user": total_count // 2,
                    "environment": total_count // 4
                }
            }

        except Exception as e:
            logger.error(f"Error getting snapshot stats: {e}")
            return {}

    async def _cleanup_old_snapshots(self, keep_count: int = 10):
        """Clean up old snapshots, keeping only the most recent ones."""
        try:
            snapshots = list(self.snapshots_dir.glob("memory_snapshot_*.json.gz"))

            if len(snapshots) <= keep_count:
                return

            # Sort by modification time (oldest first for deletion)
            snapshots.sort(key=lambda p: p.stat().st_mtime)

            # Delete oldest snapshots
            to_delete = snapshots[:-keep_count]
            for snapshot_file in to_delete:
                snapshot_file.unlink()
                logger.info(f"🗑️ Cleaned up old snapshot: {snapshot_file.name}")

        except Exception as e:
            logger.error(f"Error cleaning up snapshots: {e}")

    async def stop_auto_snapshots(self):
        """Stop the auto-snapshot task."""
        if self._snapshot_task:
            self._snapshot_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._snapshot_task
            logger.info("🛑 Auto-snapshot task stopped")

    async def retrieve(self, query: str, k: int = 6, user_id: str | None = None) -> RetrievalResult:
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

    async def store(self, chunk: MemoryChunk, tier: MemoryTier | None = None, user_id: str | None = None) -> str:
        """Store memory chunk in specified tier or auto-classify.

        Args:
            chunk: Memory chunk to store
            tier: Target memory tier (if None, auto-classified)
            user_id: User identifier for USER tier storage (implements USER<id> prefix)

        If tier not specified, uses classification logic:
        - Self-reflection terms → CORE_SELF
        - User utterance/agent reply → USER
        - External event indicators → ENV
        """
        if tier is None:
            tier = self._classify_memory_tier(chunk)
            chunk.tier = tier

        # Handle user_id for USER tier with USER<id> prefix as specified in task
        effective_user_id = user_id or self.current_user_id
        if tier == MemoryTier.USER:
            chunk.metadata["user_id"] = effective_user_id
            # Implement USER<id> prefix in memory_type as specified in task
            memory_type_with_user = f"USER{effective_user_id}_{chunk.memory_type.value}"
        else:
            memory_type_with_user = f"{tier.value}_{chunk.memory_type.value}"

        # Add tier information to metadata for filtering
        chunk.metadata["memory_tier"] = tier.value
        chunk.metadata["memory_type"] = chunk.memory_type.value

        # Store in unified store with tier metadata and USER<id> prefix
        store = self.stores[tier]
        memory_id = await store.store_memory(
            content=chunk.text,
            memory_type=memory_type_with_user,  # Uses USER<id> prefix for user memories
            metadata=chunk.metadata
        )

        # Check for overflow and summarize if needed
        await self._check_overflow(tier)

        logger.debug(f"Stored memory {memory_id} in {tier.value} tier with type: {memory_type_with_user}")
        return memory_id

    async def summarise_if_needed(self) -> dict[MemoryTier, bool]:
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
        user_filter: str | None = None
    ) -> list[MemoryChunk]:
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
        self.tier_configs[tier]

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
