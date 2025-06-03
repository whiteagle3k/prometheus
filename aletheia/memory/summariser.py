"""Memory summarization and compression pipeline."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional, List

from ..config import config
from .vector_store import VectorStore


class MemorySummariser:
    """Handles periodic summarization and compression of agent memory."""

    def __init__(self, vector_store: VectorStore) -> None:
        """Initialize the summariser."""
        self.vector_store = vector_store
        self._summarization_lock = asyncio.Lock()  # Prevent parallel summarization conflicts

    async def should_summarize(self) -> bool:
        """Check if memory should be summarized based on threshold."""
        memory_count = await self.vector_store.get_memory_count()
        return memory_count >= config.memory_summarization_threshold

    async def get_memories_for_summarization(
        self,
        days_back: int = 7,
        max_entries: int = 100,
        exclude_summaries: bool = True,
    ) -> list[dict[str, Any]]:
        """Get recent memories that should be summarized."""
        # Get all memories from the last N days
        cutoff_date = datetime.now() - timedelta(days=days_back)

        # Search for recent memories
        memories = await self.vector_store.search_memories(
            query="recent experiences and learnings",
            n_results=max_entries,
        )

        # Filter by date and exclude existing summaries
        recent_memories = []
        for memory in memories:
            metadata = memory.get("metadata", {})
            
            # Skip if it's already a summary and we're excluding summaries
            if exclude_summaries and metadata.get("type") == "summary":
                continue
                
            # Skip if already processed in a summary
            if metadata.get("is_summarized", False):
                continue
                
            timestamp_str = metadata.get("timestamp", "")
            if timestamp_str:
                try:
                    memory_date = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    if memory_date >= cutoff_date:
                        recent_memories.append(memory)
                except ValueError:
                    # Skip memories with invalid timestamps
                    continue

        return recent_memories

    def create_summary_prompt(self, memories: list[dict[str, Any]]) -> str:
        """Create a prompt for summarizing memories."""
        memories_text = "\n\n".join([
            f"Memory {i+1} ({mem['metadata'].get('timestamp', 'Unknown time')}):\n{mem['content']}"
            for i, mem in enumerate(memories)
        ])

        return f"""Analyze and summarize the following agent memories and experiences.
Extract key insights, patterns, and learnings. Focus on:

1. Important decisions and outcomes
2. Successful strategies and approaches  
3. Common patterns and lessons learned
4. Key knowledge gained
5. User preferences and context

Create a concise summary that preserves essential information.

MEMORIES TO ANALYZE:
{memories_text}

SUMMARY FORMAT:
## Key Insights
[Main learnings and patterns]

## User Context
[Important user preferences and context]

## Decisions & Outcomes
[Important decisions made and their results]

## Knowledge Gained
[New knowledge and capabilities acquired]

Keep the summary comprehensive but concise."""

    async def create_summary(
        self,
        memories: list[dict[str, Any]],
        use_local_llm: bool = True,
    ) -> Optional[str]:
        """Create a summary of memories using local LLM for TL;DR compression."""
        if not memories:
            return None

        prompt = self.create_summary_prompt(memories)

        if use_local_llm:
            try:
                # Use local LLM for summarization (as recommended by o3)
                from ..llm.local_llm import LocalLLM
                local_llm = LocalLLM()
                
                await local_llm.ensure_loaded()
                
                # Generate summary using local LLM
                summary = await local_llm.generate(
                    prompt=prompt,
                    max_tokens=800,  # Reasonable length for summary
                    temperature=0.3,  # Lower temperature for consistent summarization
                    system_prompt="You are a memory summarization assistant. Create concise, accurate summaries that preserve key information and insights."
                )
                
                return summary
                
            except Exception as e:
                print(f"❌ Local LLM summarization failed: {e}")
                # Fall back to simple summary
                return self._create_simple_summary(memories)
        else:
            # Fallback to simple concatenation if no LLM available
            return self._create_simple_summary(memories)

    def _create_simple_summary(self, memories: list[dict[str, Any]]) -> str:
        """Create a simple text-based summary without LLM."""
        memory_types = {}
        content_snippets = []

        for memory in memories:
            mem_type = memory["metadata"].get("type", "unknown")
            memory_types[mem_type] = memory_types.get(mem_type, 0) + 1

            # Take first 200 chars of content
            content = memory["content"][:200]
            if len(memory["content"]) > 200:
                content += "..."
            content_snippets.append(content)

        summary = f"""## Memory Summary ({len(memories)} entries)
Generated: {datetime.now().isoformat()}

### Memory Types Distribution:
{chr(10).join([f"- {type_}: {count}" for type_, count in memory_types.items()])}

### Key Content Highlights:
{chr(10).join([f"- {snippet}" for snippet in content_snippets[:10]])}

Total memories processed: {len(memories)}
Compression ratio: {len(memories)}:1
"""
        return summary

    async def cleanup_summarized_memories(self, memory_ids: List[str]) -> bool:
        """Delete raw memory chunks after successful summarization (o3's recommendation)."""
        try:
            if not memory_ids:
                return True
                
            print(f"🗑️  Cleaning up {len(memory_ids)} summarized memory chunks...")
            
            # Mark memories as summarized first (safer than immediate deletion)
            for memory_id in memory_ids:
                try:
                    await self.vector_store.update_memory_metadata(
                        memory_id=memory_id,
                        metadata_updates={"is_summarized": True, "summarized_at": datetime.now().isoformat()}
                    )
                except Exception as e:
                    print(f"⚠️ Failed to mark memory {memory_id} as summarized: {e}")
            
            # Actually delete the memories to free space
            deleted_count = await self.vector_store.delete_memories(memory_ids)
            print(f"✅ Cleaned up {deleted_count}/{len(memory_ids)} memory chunks")
            
            return deleted_count == len(memory_ids)
            
        except Exception as e:
            print(f"❌ Memory cleanup failed: {e}")
            return False

    async def summarize_and_compress(
        self,
        delete_originals: bool = True,  # Enable cleanup by default (o3's recommendation)
        min_memories_for_cleanup: int = 20,  # Safety threshold
    ) -> Optional[str]:
        """Perform full summarization and compression cycle with cleanup."""
        # Use lock to prevent parallel summarization conflicts (o3's issue #6)
        async with self._summarization_lock:
            if not await self.should_summarize():
                return None

            print("🧠 Starting memory summarization...")

            # Get memories to summarize
            memories = await self.get_memories_for_summarization()

            if not memories:
                print("ℹ️  No recent memories found for summarization")
                return None

            print(f"📊 Summarizing {len(memories)} memory entries...")

            # Create summary using local LLM
            summary = await self.create_summary(memories, use_local_llm=True)

            if summary:
                # Store summary as a special memory entry
                summary_metadata = {
                    "type": "summary",
                    "original_count": len(memories),
                    "summarization_date": datetime.now().isoformat(),
                    "is_compressed": True,
                    "is_summary": True,  # Flag for easy identification
                    "compression_ratio": f"{len(memories)}:1"
                }
                
                summary_id = await self.vector_store.store_memory(
                    content=summary,
                    memory_type="summary",
                    metadata=summary_metadata,
                )

                print(f"✅ Memory summary created with ID: {summary_id}")

                # Cleanup original memories to save space (o3's recommendation)
                if delete_originals and len(memories) >= min_memories_for_cleanup:
                    memory_ids = [mem.get("id") for mem in memories if mem.get("id")]
                    cleanup_success = await self.cleanup_summarized_memories(memory_ids)
                    
                    if cleanup_success:
                        print(f"🎯 Successfully compressed {len(memories)} memories into 1 summary")
                    else:
                        print("⚠️  Summary created but cleanup partially failed")
                else:
                    print(f"⏭️  Skipping cleanup (only {len(memories)} memories, threshold: {min_memories_for_cleanup})")

                return summary_id

            else:
                print("❌ Failed to create memory summary")
                return None

    async def run_periodic_summarization(
        self,
        interval_hours: int = 24,
    ) -> None:
        """Run periodic summarization in background."""
        print(f"📅 Starting periodic summarization (every {interval_hours} hours)")

        while True:
            try:
                result = await self.summarize_and_compress()
                if result:
                    print(f"✅ Periodic summarization completed: {result}")
                else:
                    print("ℹ️  Periodic summarization: nothing to summarize")
                    
                await asyncio.sleep(interval_hours * 3600)  # Convert to seconds
            except Exception as e:
                print(f"❌ Error in periodic summarization: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour on error

    async def get_summarization_stats(self) -> dict[str, Any]:
        """Get statistics about summarization activities."""
        try:
            # Count total memories
            total_memories = await self.vector_store.get_memory_count()
            
            # Count summaries
            summary_search = await self.vector_store.search_memories(
                query="summary",
                n_results=1000,  # High number to get all summaries
            )
            
            summaries = [m for m in summary_search if m.get("metadata", {}).get("type") == "summary"]
            
            # Calculate compression stats
            total_compressed = sum(
                m.get("metadata", {}).get("original_count", 0) 
                for m in summaries
            )
            
            return {
                "total_memories": total_memories,
                "summaries_count": len(summaries),
                "memories_compressed": total_compressed,
                "compression_ratio": f"{total_compressed}:{len(summaries)}" if summaries else "0:0",
                "space_saved_estimate": total_compressed - len(summaries),
                "summarization_threshold": config.memory_summarization_threshold,
            }
            
        except Exception as e:
            print(f"❌ Failed to get summarization stats: {e}")
            return {"error": str(e)}
