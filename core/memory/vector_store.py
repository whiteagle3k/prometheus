"""Vector store implementation using ChromaDB."""

import asyncio
import uuid
from datetime import datetime
from typing import Any

import chromadb
from chromadb.config import Settings

from core.config import config


class VectorStore:
    """ChromaDB-based vector store for agent memory."""

    def __init__(self) -> None:
        """Initialize the vector store."""
        self.client = chromadb.PersistentClient(
            path=str(config.chroma_persist_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Add lock for parallel access protection (o3's issue #6)
        self._access_lock = asyncio.Lock()

        # Get or create collections
        self.memory_collection = self.client.get_or_create_collection(
            name="agent_memory",
            metadata={"description": "Long-term agent memory and experiences"},
        )

        self.reflection_collection = self.client.get_or_create_collection(
            name="reflections",
            metadata={"description": "Agent self-critiques and improvements"},
        )

    async def store_memory(
        self,
        content: str,
        memory_type: str = "experience",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a memory entry."""
        memory_id = str(uuid.uuid4())

        entry_metadata = {
            "timestamp": datetime.now().isoformat(),
            "type": memory_type,
            **(metadata or {}),
        }

        # Run in thread pool to avoid blocking
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.memory_collection.add(
                documents=[content],
                metadatas=[entry_metadata],
                ids=[memory_id],
            ),
        )

        return memory_id

    async def search_memories(
        self,
        query: str,
        n_results: int = 5,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for relevant memories."""
        where_filter = {}
        if memory_type:
            where_filter["type"] = memory_type

        # Get the actual collection size to avoid requesting more than available
        collection_count = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.memory_collection.count(),
        )

        # Adjust n_results to not exceed available entries
        actual_n_results = min(n_results, collection_count) if collection_count > 0 else 0

        # Skip search if no memories available
        if actual_n_results == 0:
            return []

        results = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.memory_collection.query(
                query_texts=[query],
                n_results=actual_n_results,
                where=where_filter if where_filter else None,
            ),
        )

        memories = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                memory = {
                    "id": results["ids"][0][i],
                    "content": doc,
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results["distances"] else None,
                }
                memories.append(memory)

        return memories

    async def store_reflection(
        self,
        task: str,
        critique: str,
        improvements: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a reflection/self-critique entry."""
        reflection_id = str(uuid.uuid4())

        content = f"Task: {task}\nCritique: {critique}\nImprovements: {improvements}"

        entry_metadata = {
            "timestamp": datetime.now().isoformat(),
            "type": "reflection",
            **(metadata or {}),
        }

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.reflection_collection.add(
                documents=[content],
                metadatas=[entry_metadata],
                ids=[reflection_id],
            ),
        )

        return reflection_id

    async def get_memory_count(self) -> int:
        """Get total number of memory entries."""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.memory_collection.count(),
        )

    async def update_memory_metadata(self, memory_id: str, metadata_updates: dict[str, Any]) -> bool:
        """Update metadata for a specific memory entry (needed for summarization)."""
        try:
            async with self._access_lock:
                # Get current entry
                current = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.memory_collection.get(ids=[memory_id]),
                )

                if not current["ids"] or memory_id not in current["ids"]:
                    return False

                # Find the index of the memory
                idx = current["ids"].index(memory_id)
                current_metadata = current["metadatas"][idx]

                # Update metadata
                updated_metadata = {**current_metadata, **metadata_updates}

                # Update in ChromaDB
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.memory_collection.update(
                        ids=[memory_id],
                        metadatas=[updated_metadata],
                    ),
                )

                return True

        except Exception as e:
            print(f"❌ Failed to update memory metadata for {memory_id}: {e}")
            return False

    async def delete_memories(self, memory_ids: list[str]) -> int:
        """Delete multiple memory entries by IDs (needed for cleanup after summarization)."""
        if not memory_ids:
            return 0

        try:
            async with self._access_lock:
                # Filter out any IDs that don't exist
                existing = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.memory_collection.get(ids=memory_ids),
                )

                valid_ids = [id_ for id_ in memory_ids if id_ in existing["ids"]]

                if not valid_ids:
                    return 0

                # Delete the memories
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.memory_collection.delete(ids=valid_ids),
                )

                return len(valid_ids)

        except Exception as e:
            print(f"❌ Failed to delete memories: {e}")
            return 0

    async def cleanup_old_memories(self, keep_count: int | None = None) -> int:
        """Remove old memories if over threshold."""
        if keep_count is None:
            keep_count = config.max_memory_entries

        current_count = await self.get_memory_count()

        if current_count <= keep_count:
            return 0

        # Get oldest memories to delete
        to_delete = current_count - keep_count

        # For now, simple implementation - in production would be more sophisticated
        all_memories = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.memory_collection.get(),
        )

        if not all_memories["ids"]:
            return 0

        # Sort by timestamp and delete oldest
        memories_with_time = [
            (id_, meta.get("timestamp", ""))
            for id_, meta in zip(all_memories["ids"], all_memories["metadatas"], strict=False)
        ]

        memories_with_time.sort(key=lambda x: x[1])
        ids_to_delete = [id_ for id_, _ in memories_with_time[:to_delete]]

        if ids_to_delete:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.memory_collection.delete(ids=ids_to_delete),
            )

        return len(ids_to_delete)

    async def reset_all(self) -> None:
        """Reset all collections (for testing/debugging)."""
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.client.reset(),
        )

        # Recreate collections
        self.memory_collection = self.client.get_or_create_collection(
            name="agent_memory",
            metadata={"description": "Long-term agent memory and experiences"},
        )

        self.reflection_collection = self.client.get_or_create_collection(
            name="reflections",
            metadata={"description": "Agent self-critiques and improvements"},
        )
