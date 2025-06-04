"""
Retrieval Optimizer Module - Self-RAG Enhancement

Optimizes context retrieval through intelligent filtering and selection.
Reduces noise and improves relevance of retrieved context.
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import re

from ..llm.fast_llm import FastLLM


@dataclass
class ContextItem:
    """A piece of context with relevance scoring."""
    content: str
    source: str  # "memory", "conversation", "knowledge"
    relevance_score: float  # 0-1 score
    importance_score: float  # 0-1 score
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RetrievalStrategy:
    """Strategy for context retrieval."""
    max_items: int = 10
    relevance_threshold: float = 0.3
    importance_threshold: float = 0.2
    diversity_bonus: float = 0.1  # Bonus for diverse sources
    recency_weight: float = 0.2  # Weight for recent items
    deduplication: bool = True


class RetrievalOptimizer:
    """
    Retrieval Optimizer for intelligent context selection.
    
    Uses fast LLM to assess relevance and importance,
    applies filtering and ranking strategies.
    """
    
    def __init__(self, identity_config: Optional[dict] = None):
        """Initialize optimizer with fast LLM."""
        self.utility_llm = FastLLM(identity_config=identity_config)
        self.optimization_stats = {
            "contexts_evaluated": 0,
            "contexts_filtered": 0,
            "relevance_assessments": 0,
            "deduplication_applied": 0
        }
    
    async def optimize_context_retrieval(self, 
                                       query: str,
                                       raw_contexts: List[Dict[str, Any]],
                                       strategy: Optional[RetrievalStrategy] = None) -> List[ContextItem]:
        """
        Optimize context retrieval by filtering and ranking.
        
        Args:
            query: The user query or task
            raw_contexts: Raw context items from various sources
            strategy: Retrieval strategy to apply
            
        Returns:
            Optimized and ranked context items
        """
        if not raw_contexts:
            return []
        
        strategy = strategy or RetrievalStrategy()
        
        print(f"🔍 Optimizing context retrieval for {len(raw_contexts)} items...")
        
        # Step 1: Convert raw contexts to ContextItems with initial scoring
        context_items = await self._assess_context_relevance(query, raw_contexts)
        
        # Step 2: Apply filtering based on thresholds
        filtered_contexts = self._apply_filtering(context_items, strategy)
        
        # Step 3: Apply deduplication if enabled
        if strategy.deduplication:
            filtered_contexts = await self._deduplicate_contexts(filtered_contexts)
        
        # Step 4: Apply ranking and selection
        final_contexts = self._rank_and_select(filtered_contexts, strategy)
        
        print(f"📊 Context optimization: {len(raw_contexts)} → {len(final_contexts)} items")
        
        return final_contexts
    
    async def _assess_context_relevance(self, query: str, raw_contexts: List[Dict[str, Any]]) -> List[ContextItem]:
        """
        Assess relevance and importance of context items.
        
        Args:
            query: The user query
            raw_contexts: Raw context data
            
        Returns:
            Context items with relevance scores
        """
        context_items = []
        
        for raw_context in raw_contexts:
            content = raw_context.get("content", "")
            source = raw_context.get("source", "unknown")
            
            if not content.strip():
                continue
            
            # Assess relevance using fast LLM
            try:
                relevance_result = await self._assess_single_context(query, content, source)
                
                context_item = ContextItem(
                    content=content,
                    source=source,
                    relevance_score=relevance_result["relevance"],
                    importance_score=relevance_result["importance"],
                    timestamp=raw_context.get("timestamp"),
                    metadata=raw_context.get("metadata", {})
                )
                
                context_items.append(context_item)
                self.optimization_stats["contexts_evaluated"] += 1
                
            except Exception as e:
                print(f"⚠️ Context assessment failed for item: {e}")
                # Add with neutral scores
                context_item = ContextItem(
                    content=content,
                    source=source,
                    relevance_score=0.5,
                    importance_score=0.5,
                    timestamp=raw_context.get("timestamp"),
                    metadata=raw_context.get("metadata", {})
                )
                context_items.append(context_item)
        
        return context_items
    
    async def _assess_single_context(self, query: str, content: str, source: str) -> Dict[str, float]:
        """
        Assess a single context item for relevance and importance.
        
        Args:
            query: User query
            content: Context content
            source: Context source
            
        Returns:
            Relevance and importance scores
        """
        # Truncate content for assessment to avoid overwhelming the LLM
        truncated_content = content[:400] if len(content) > 400 else content
        
        prompt = f"""Assess this context item for a user query:

QUERY: {query}

CONTEXT CONTENT: {truncated_content}
CONTEXT SOURCE: {source}

Rate this context on two dimensions (0.0-1.0):
1. RELEVANCE: How relevant is this context to answering the query?
2. IMPORTANCE: How important/useful is this information?

Consider:
- Direct relevance to the query topic
- Potential usefulness for generating a good response
- Information quality and completeness
- Source credibility

Format response as:
RELEVANCE: [0.0-1.0]
IMPORTANCE: [0.0-1.0]
REASON: [brief explanation]"""

        try:
            result = await self.utility_llm.classify_prompt(
                prompt=prompt,
                classification_type="context_relevance_assessment"
            )
            
            response = result.get("classification", "")
            
            # Parse scores
            relevance = self._extract_score(response, "RELEVANCE")
            importance = self._extract_score(response, "IMPORTANCE")
            
            self.optimization_stats["relevance_assessments"] += 1
            
            return {
                "relevance": relevance,
                "importance": importance,
                "reasoning": self._extract_reason(response)
            }
            
        except Exception as e:
            print(f"⚠️ Single context assessment failed: {e}")
            return {"relevance": 0.5, "importance": 0.5, "reasoning": "Assessment failed"}
    
    def _apply_filtering(self, context_items: List[ContextItem], strategy: RetrievalStrategy) -> List[ContextItem]:
        """
        Apply filtering based on relevance and importance thresholds.
        
        Args:
            context_items: Context items to filter
            strategy: Filtering strategy
            
        Returns:
            Filtered context items
        """
        initial_count = len(context_items)
        
        filtered = []
        for item in context_items:
            # Check relevance threshold
            if item.relevance_score < strategy.relevance_threshold:
                continue
            
            # Check importance threshold
            if item.importance_score < strategy.importance_threshold:
                continue
            
            filtered.append(item)
        
        filtered_count = initial_count - len(filtered)
        self.optimization_stats["contexts_filtered"] += filtered_count
        
        print(f"🔽 Filtered out {filtered_count} low-quality context items")
        
        return filtered
    
    async def _deduplicate_contexts(self, context_items: List[ContextItem]) -> List[ContextItem]:
        """
        Remove duplicate or highly similar context items.
        
        Args:
            context_items: Context items to deduplicate
            
        Returns:
            Deduplicated context items
        """
        if len(context_items) <= 1:
            return context_items
        
        deduplicated = []
        
        for i, current_item in enumerate(context_items):
            is_duplicate = False
            
            for existing_item in deduplicated:
                # Check for similarity
                similarity = self._calculate_similarity(current_item.content, existing_item.content)
                
                if similarity > 0.8:  # 80% similarity threshold
                    is_duplicate = True
                    # Keep the higher scoring item
                    if current_item.relevance_score > existing_item.relevance_score:
                        deduplicated.remove(existing_item)
                        deduplicated.append(current_item)
                    break
            
            if not is_duplicate:
                deduplicated.append(current_item)
        
        duplicates_removed = len(context_items) - len(deduplicated)
        if duplicates_removed > 0:
            self.optimization_stats["deduplication_applied"] += duplicates_removed
            print(f"🔄 Removed {duplicates_removed} duplicate context items")
        
        return deduplicated
    
    def _rank_and_select(self, context_items: List[ContextItem], strategy: RetrievalStrategy) -> List[ContextItem]:
        """
        Rank and select the best context items.
        
        Args:
            context_items: Context items to rank
            strategy: Selection strategy
            
        Returns:
            Top-ranked context items
        """
        # Calculate composite scores
        for item in context_items:
            # Base score from relevance and importance
            base_score = (item.relevance_score * 0.6 + item.importance_score * 0.4)
            
            # Apply diversity bonus
            source_diversity_bonus = 0
            if item.source in ["memory", "knowledge"]:  # Bonus for non-conversation sources
                source_diversity_bonus = strategy.diversity_bonus
            
            # Apply recency weight
            recency_bonus = 0
            if item.timestamp:
                try:
                    timestamp = datetime.fromisoformat(item.timestamp.replace('Z', '+00:00'))
                    age_hours = (datetime.now(timestamp.tzinfo) - timestamp).total_seconds() / 3600
                    # Bonus for items less than 24 hours old
                    if age_hours < 24:
                        recency_bonus = strategy.recency_weight * (1 - age_hours / 24)
                except:
                    pass  # Skip recency bonus if timestamp parsing fails
            
            # Calculate final score
            item.final_score = base_score + source_diversity_bonus + recency_bonus
        
        # Sort by final score (descending)
        ranked_items = sorted(context_items, key=lambda x: x.final_score, reverse=True)
        
        # Select top items
        selected_items = ranked_items[:strategy.max_items]
        
        print(f"🏆 Selected top {len(selected_items)} context items:")
        for i, item in enumerate(selected_items[:3]):  # Show top 3
            print(f"   {i+1}. {item.source} (relevance: {item.relevance_score:.2f}, final: {item.final_score:.2f})")
        
        return selected_items
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings.
        
        Simple implementation using word overlap.
        In production, could use more sophisticated embeddings.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        # Convert to lowercase and split into words
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_score(self, response: str, score_type: str) -> float:
        """
        Extract a score from LLM response.
        
        Args:
            response: LLM response text
            score_type: Type of score to extract (e.g., "RELEVANCE")
            
        Returns:
            Extracted score (0.0-1.0)
        """
        lines = response.split('\n')
        for line in lines:
            if line.strip().upper().startswith(f"{score_type}:"):
                try:
                    score_str = line.split(":", 1)[1].strip()
                    score = float(score_str)
                    return max(0.0, min(1.0, score))  # Clamp to 0-1 range
                except:
                    pass
        
        return 0.5  # Default neutral score
    
    def _extract_reason(self, response: str) -> str:
        """Extract reasoning from LLM response."""
        lines = response.split('\n')
        for line in lines:
            if line.strip().upper().startswith("REASON:"):
                return line.split(":", 1)[1].strip() if ":" in line else "No reason provided"
        return "No reasoning provided"
    
    async def smart_context_selection(self, 
                                    query: str,
                                    conversation_history: List[str],
                                    memory_items: List[Dict[str, Any]],
                                    max_context_length: int = 2000) -> Dict[str, Any]:
        """
        Intelligent context selection combining conversation and memory.
        
        Args:
            query: User query
            conversation_history: Recent conversation
            memory_items: Relevant memory items
            max_context_length: Maximum context length in characters
            
        Returns:
            Optimized context selection
        """
        # Prepare raw contexts
        raw_contexts = []
        
        # Add conversation history
        for i, msg in enumerate(conversation_history[-10:]):  # Last 10 messages
            raw_contexts.append({
                "content": msg,
                "source": "conversation",
                "timestamp": datetime.now().isoformat(),
                "metadata": {"position": len(conversation_history) - i}
            })
        
        # Add memory items
        for memory in memory_items:
            raw_contexts.append({
                "content": memory.get("content", ""),
                "source": "memory",
                "timestamp": memory.get("metadata", {}).get("timestamp"),
                "metadata": memory.get("metadata", {})
            })
        
        # Optimize context selection
        strategy = RetrievalStrategy(
            max_items=15,  # Allow more items initially
            relevance_threshold=0.2,  # Lower threshold for broader selection
            importance_threshold=0.1,
            diversity_bonus=0.2,  # Higher diversity bonus
            recency_weight=0.3  # Higher recency weight
        )
        
        optimized_contexts = await self.optimize_context_retrieval(query, raw_contexts, strategy)
        
        # Build final context within length limit
        selected_context = self._build_context_within_limit(optimized_contexts, max_context_length)
        
        return {
            "optimized_context": selected_context,
            "context_items_used": len(optimized_contexts),
            "total_items_evaluated": len(raw_contexts),
            "context_length": len(selected_context),
            "optimization_stats": self.optimization_stats.copy()
        }
    
    def _build_context_within_limit(self, context_items: List[ContextItem], max_length: int) -> str:
        """
        Build context string within character limit.
        
        Args:
            context_items: Optimized context items
            max_length: Maximum length in characters
            
        Returns:
            Context string within limit
        """
        context_parts = []
        current_length = 0
        
        for item in context_items:
            item_text = f"[{item.source}] {item.content}\n"
            
            if current_length + len(item_text) > max_length:
                # Try to fit a truncated version
                remaining_space = max_length - current_length - 50  # Leave some buffer
                if remaining_space > 100:  # Only if reasonable space remains
                    truncated = item.content[:remaining_space] + "..."
                    item_text = f"[{item.source}] {truncated}\n"
                    context_parts.append(item_text)
                break
            
            context_parts.append(item_text)
            current_length += len(item_text)
        
        return "".join(context_parts)
    
    def get_optimization_stats(self) -> Dict[str, int]:
        """Get retrieval optimization statistics."""
        return self.optimization_stats.copy()
    
    async def evaluate_retrieval_quality(self, query: str, selected_context: str) -> Dict[str, Any]:
        """
        Evaluate the quality of the final context selection.
        
        Args:
            query: Original query
            selected_context: Final selected context
            
        Returns:
            Quality evaluation
        """
        if not selected_context.strip():
            return {
                "quality_score": 0.0,
                "feedback": "No context selected",
                "suggestions": ["Improve context retrieval thresholds"]
            }
        
        prompt = f"""Evaluate the quality of this context selection for the given query:

QUERY: {query}

SELECTED CONTEXT:
{selected_context[:800]}{"..." if len(selected_context) > 800 else ""}

Rate the context quality (0.0-1.0) considering:
1. Relevance to the query
2. Completeness of information
3. Absence of noise/irrelevant information
4. Overall usefulness for answering

Format as:
QUALITY: [0.0-1.0]
FEEDBACK: [assessment]
SUGGESTIONS: [improvement suggestions]"""

        try:
            result = await self.utility_llm.classify_prompt(
                prompt=prompt,
                classification_type="context_quality_evaluation"
            )
            
            response = result.get("classification", "")
            
            return {
                "quality_score": self._extract_score(response, "QUALITY"),
                "feedback": self._extract_section(response, "FEEDBACK"),
                "suggestions": self._extract_suggestions_list(response, "SUGGESTIONS")
            }
            
        except Exception as e:
            print(f"⚠️ Context quality evaluation failed: {e}")
            return {
                "quality_score": 0.5,
                "feedback": "Evaluation failed",
                "suggestions": ["Unable to evaluate"]
            }
    
    def _extract_section(self, response: str, section: str) -> str:
        """Extract a section from response."""
        lines = response.split('\n')
        content_lines = []
        capturing = False
        
        for line in lines:
            if line.strip().upper().startswith(f"{section}:"):
                capturing = True
                content = line.split(":", 1)[1].strip() if ":" in line else ""
                if content:
                    content_lines.append(content)
            elif capturing and line.strip().upper().startswith(("SUGGESTIONS:", "FEEDBACK:", "QUALITY:")):
                break
            elif capturing and line.strip():
                content_lines.append(line.strip())
        
        return " ".join(content_lines) if content_lines else f"No {section.lower()} provided"
    
    def _extract_suggestions_list(self, response: str, section: str) -> List[str]:
        """Extract suggestions as a list."""
        content = self._extract_section(response, section)
        # Simple split on common delimiters
        suggestions = []
        for item in content.split('.'):
            item = item.strip().lstrip('- ').strip()
            if item and len(item) > 5:
                suggestions.append(item)
        return suggestions if suggestions else ["No specific suggestions"] 