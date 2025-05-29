"""Memory summarization and compression pipeline."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional

from ..config import config
from .vector_store import VectorStore


class MemorySummariser:
    """Handles periodic summarization and compression of agent memory."""

    def __init__(self, vector_store: VectorStore) -> None:
        """Initialize the summariser."""
        self.vector_store = vector_store

    async def should_summarize(self) -> bool:
        """Check if memory should be summarized based on threshold."""
        memory_count = await self.vector_store.get_memory_count()
        return memory_count >= config.memory_summarization_threshold

    async def get_memories_for_summarization(
        self,
        days_back: int = 7,
        max_entries: int = 100,
    ) -> list[dict[str, Any]]:
        """Get recent memories that should be summarized."""
        # Get all memories from the last N days
        cutoff_date = datetime.now() - timedelta(days=days_back)

        # Search for recent memories
        memories = await self.vector_store.search_memories(
            query="recent experiences and learnings",
            n_results=max_entries,
        )

        # Filter by date
        recent_memories = []
        for memory in memories:
            timestamp_str = memory["metadata"].get("timestamp", "")
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

        return f"""Please analyze and summarize the following agent memories and experiences.
Extract the key learnings, patterns, and insights. Focus on:
1. Important decisions and their outcomes
2. Successful strategies and approaches
3. Common failure modes and how to avoid them
4. Emerging patterns in tasks and solutions
5. Key knowledge gained

Memories to analyze:
{memories_text}

Provide a concise but comprehensive summary that captures the essential insights and learnings.
Format as a structured summary with clear sections."""

    async def create_summary(
        self,
        memories: list[dict[str, Any]],
        external_llm = None,
    ) -> Optional[str]:
        """Create a summary of memories using external LLM."""
        if not memories:
            return None

        if not external_llm:
            # Fallback to simple concatenation if no LLM available
            return self._create_simple_summary(memories)

        prompt = self.create_summary_prompt(memories)

        try:
            # Use external LLM for sophisticated summarization
            summary = await external_llm.generate(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.3,
            )
            return summary
        except Exception as e:
            print(f"Error creating LLM summary: {e}")
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

        summary = f"""Memory Summary ({len(memories)} entries)
Generated: {datetime.now().isoformat()}

Memory Types:
{chr(10).join([f"- {type_}: {count}" for type_, count in memory_types.items()])}

Key Content Themes:
{chr(10).join([f"- {snippet}" for snippet in content_snippets[:10]])}

Total memories processed: {len(memories)}
"""
        return summary

    async def summarize_and_compress(
        self,
        external_llm = None,
        delete_originals: bool = False,
    ) -> Optional[str]:
        """Perform full summarization and compression cycle."""
        if not await self.should_summarize():
            return None

        print("🧠 Starting memory summarization...")

        # Get memories to summarize
        memories = await self.get_memories_for_summarization()

        if not memories:
            print("No recent memories found for summarization")
            return None

        print(f"Summarizing {len(memories)} memory entries...")

        # Create summary
        summary = await self.create_summary(memories, external_llm)

        if summary:
            # Store summary as a special memory entry
            summary_id = await self.vector_store.store_memory(
                content=summary,
                memory_type="summary",
                metadata={
                    "original_count": len(memories),
                    "summarization_date": datetime.now().isoformat(),
                    "is_compressed": True,
                },
            )

            print(f"✅ Memory summary created with ID: {summary_id}")

            # Optionally delete original memories to save space
            if delete_originals and len(memories) > 50:  # Safety check
                # This would delete the original memories
                # Implementation depends on specific requirements
                print("⚠️  Original memory deletion not implemented yet")

            return summary_id

        return None

    async def run_periodic_summarization(
        self,
        external_llm = None,
        interval_hours: int = 24,
    ) -> None:
        """Run periodic summarization in background."""
        print(f"📅 Starting periodic summarization (every {interval_hours} hours)")

        while True:
            try:
                await self.summarize_and_compress(external_llm)
                await asyncio.sleep(interval_hours * 3600)  # Convert to seconds
            except Exception as e:
                print(f"Error in periodic summarization: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour on error
