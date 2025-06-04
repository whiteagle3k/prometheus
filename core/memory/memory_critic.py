"""
Memory Critic Module - Self-RAG Enhancement

Evaluates and improves memory quality through systematic critique.
Inspired by Self-RAG paper's approach to memory assessment.
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..llm.fast_llm import FastLLM


@dataclass
class MemoryQualityScore:
    """Memory quality assessment."""
    relevance: float  # 0-1 score
    accuracy: float   # 0-1 score
    completeness: float  # 0-1 score
    utility: float    # 0-1 score
    overall: float    # Combined score
    feedback: str     # Detailed critique
    improvement_suggestions: List[str]


@dataclass
class MemoryCritiqueResult:
    """Result of memory critique process."""
    original_memory: Dict[str, Any]
    quality_score: MemoryQualityScore
    should_keep: bool
    should_enhance: bool
    enhanced_version: Optional[str] = None
    consolidation_candidates: List[str] = None


class MemoryCritic:
    """
    Memory Critic for evaluating and improving memory quality.
    
    Uses fast LLM to provide intelligent memory assessment
    and improvement suggestions.
    """
    
    def __init__(self, identity_config: Optional[dict] = None):
        """Initialize memory critic with LLM."""
        self.utility_llm = FastLLM(identity_config=identity_config)
        self.critique_stats = {
            "memories_evaluated": 0,
            "memories_enhanced": 0,
            "memories_purged": 0,
            "consolidations_suggested": 0
        }
    
    async def evaluate_memory_quality(self, memory: Dict[str, Any]) -> MemoryQualityScore:
        """
        Evaluate the quality of a single memory entry.
        
        Args:
            memory: Memory entry with content and metadata
            
        Returns:
            Quality score and feedback
        """
        content = memory.get("content", "")
        metadata = memory.get("metadata", {})
        timestamp = metadata.get("timestamp", "")
        memory_type = metadata.get("type", "experience")
        
        # Create evaluation prompt
        prompt = f"""Evaluate this memory entry for quality and utility:

Memory Content: {content}
Type: {memory_type}
Timestamp: {timestamp}

Rate each aspect from 0.0 to 1.0:
1. RELEVANCE: Is this memory relevant and meaningful?
2. ACCURACY: Does the memory appear accurate and well-formed?
3. COMPLETENESS: Is the memory complete or missing important details?
4. UTILITY: How useful is this memory for future tasks?

Provide ratings and detailed feedback on improvement opportunities.

Format your response as:
RELEVANCE: [0.0-1.0]
ACCURACY: [0.0-1.0] 
COMPLETENESS: [0.0-1.0]
UTILITY: [0.0-1.0]
FEEDBACK: [detailed critique]
IMPROVEMENTS: [list of specific suggestions]"""

        try:
            result = await self.utility_llm.classify_prompt(
                prompt=prompt,
                classification_type="memory_quality_evaluation"
            )
            
            response = result.get("classification", "")
            
            # Parse the response
            scores = self._parse_quality_scores(response)
            feedback = self._extract_feedback(response)
            improvements = self._extract_improvements(response)
            
            overall_score = (scores["relevance"] + scores["accuracy"] + 
                           scores["completeness"] + scores["utility"]) / 4
            
            self.critique_stats["memories_evaluated"] += 1
            
            return MemoryQualityScore(
                relevance=scores["relevance"],
                accuracy=scores["accuracy"],
                completeness=scores["completeness"],
                utility=scores["utility"],
                overall=overall_score,
                feedback=feedback,
                improvement_suggestions=improvements
            )
            
        except Exception as e:
            print(f"⚠️ Memory quality evaluation failed: {e}")
            # Return neutral scores on failure
            return MemoryQualityScore(
                relevance=0.5, accuracy=0.5, completeness=0.5, utility=0.5,
                overall=0.5, feedback="Evaluation failed", improvement_suggestions=[]
            )
    
    async def critique_memory_set(self, memories: List[Dict[str, Any]]) -> List[MemoryCritiqueResult]:
        """
        Critique a set of memories and provide improvement recommendations.
        
        Args:
            memories: List of memory entries to evaluate
            
        Returns:
            List of critique results with recommendations
        """
        results = []
        
        for memory in memories:
            quality_score = await self.evaluate_memory_quality(memory)
            
            # Tightened critic rules as suggested by o3:
            # Require higher quality threshold and more strict relevance
            should_keep = (
                quality_score.overall >= 0.4 and  # Raised from 0.3
                quality_score.relevance > 0.35    # New relevance threshold
            )
            should_enhance = (
                0.35 <= quality_score.overall < 0.7 and  # Adjusted range
                quality_score.relevance > 0.35           # Must meet relevance threshold
            )
            
            # If relevance is too low, drop the memory entirely
            if quality_score.relevance <= 0.35:
                should_keep = False
                should_enhance = False
                print(f"🗑️ Dropping low-relevance memory (relevance: {quality_score.relevance:.2f})")
            
            enhanced_version = None
            if should_enhance:
                enhanced_version = await self._enhance_memory(memory, quality_score)
                if enhanced_version:
                    self.critique_stats["memories_enhanced"] += 1
            
            if not should_keep:
                self.critique_stats["memories_purged"] += 1
            
            # Find consolidation candidates only for kept memories
            consolidation_candidates = []
            if should_keep:
                consolidation_candidates = await self._find_consolidation_candidates(
                    memory, memories
                )
            
            result = MemoryCritiqueResult(
                original_memory=memory,
                quality_score=quality_score,
                should_keep=should_keep,
                should_enhance=should_enhance,
                enhanced_version=enhanced_version,
                consolidation_candidates=consolidation_candidates
            )
            
            results.append(result)
        
        return results
    
    async def _enhance_memory(self, memory: Dict[str, Any], quality_score: MemoryQualityScore) -> str:
        """
        Enhance a memory based on quality assessment.
        
        Args:
            memory: Original memory entry
            quality_score: Quality assessment with improvement suggestions
            
        Returns:
            Enhanced memory content
        """
        content = memory.get("content", "")
        improvements = quality_score.improvement_suggestions
        
        prompt = f"""Enhance this memory entry based on the quality assessment:

Original Memory: {content}

Quality Issues:
{quality_score.feedback}

Improvement Suggestions:
{chr(10).join(f"- {suggestion}" for suggestion in improvements)}

Rewrite the memory to address these issues while preserving the core information.
Make it more complete, accurate, and useful for future reference.

Enhanced Memory:"""

        try:
            result = await self.utility_llm.classify_prompt(
                prompt=prompt,
                classification_type="memory_enhancement"
            )
            
            enhanced = result.get("classification", content)
            
            # Clean up the response
            if "Enhanced Memory:" in enhanced:
                enhanced = enhanced.split("Enhanced Memory:")[-1].strip()
            
            self.critique_stats["memories_enhanced"] += 1
            return enhanced
            
        except Exception as e:
            print(f"⚠️ Memory enhancement failed: {e}")
            return content
    
    async def _find_consolidation_candidates(self, 
                                          target_memory: Dict[str, Any], 
                                          all_memories: List[Dict[str, Any]]) -> List[str]:
        """
        Find memories that could be consolidated with the target memory.
        
        Args:
            target_memory: Memory to find consolidation candidates for
            all_memories: All available memories to search
            
        Returns:
            List of memory IDs that are consolidation candidates
        """
        target_content = target_memory.get("content", "")
        candidates = []
        
        # Simple similarity check - in production would use vector similarity
        for memory in all_memories:
            if memory.get("id") == target_memory.get("id"):
                continue
                
            other_content = memory.get("content", "")
            
            # Basic overlap detection
            target_words = set(target_content.lower().split())
            other_words = set(other_content.lower().split())
            
            if len(target_words) > 0 and len(other_words) > 0:
                overlap = len(target_words & other_words) / len(target_words | other_words)
                
                if overlap > 0.3:  # 30% word overlap
                    candidates.append(memory.get("id", ""))
        
        return [c for c in candidates if c]  # Filter out empty IDs
    
    def _parse_quality_scores(self, response: str) -> Dict[str, float]:
        """Parse quality scores from LLM response."""
        scores = {"relevance": 0.5, "accuracy": 0.5, "completeness": 0.5, "utility": 0.5}
        
        lines = response.split('\n')
        for line in lines:
            line = line.strip().upper()
            if line.startswith("RELEVANCE:"):
                try:
                    scores["relevance"] = float(line.split(":")[1].strip())
                except:
                    pass
            elif line.startswith("ACCURACY:"):
                try:
                    scores["accuracy"] = float(line.split(":")[1].strip())
                except:
                    pass
            elif line.startswith("COMPLETENESS:"):
                try:
                    scores["completeness"] = float(line.split(":")[1].strip())
                except:
                    pass
            elif line.startswith("UTILITY:"):
                try:
                    scores["utility"] = float(line.split(":")[1].strip())
                except:
                    pass
        
        return scores
    
    def _extract_feedback(self, response: str) -> str:
        """Extract feedback from LLM response."""
        lines = response.split('\n')
        feedback_lines = []
        capturing = False
        
        for line in lines:
            if line.strip().upper().startswith("FEEDBACK:"):
                capturing = True
                feedback_content = line.split(":", 1)[1].strip() if ":" in line else ""
                if feedback_content:
                    feedback_lines.append(feedback_content)
            elif capturing and line.strip().upper().startswith("IMPROVEMENTS:"):
                break
            elif capturing and line.strip():
                feedback_lines.append(line.strip())
        
        return " ".join(feedback_lines) if feedback_lines else "No feedback provided"
    
    def _extract_improvements(self, response: str) -> List[str]:
        """Extract improvement suggestions from LLM response."""
        lines = response.split('\n')
        improvements = []
        capturing = False
        
        for line in lines:
            if line.strip().upper().startswith("IMPROVEMENTS:"):
                capturing = True
                improvement_content = line.split(":", 1)[1].strip() if ":" in line else ""
                if improvement_content:
                    improvements.append(improvement_content.lstrip("- ").strip())
            elif capturing and line.strip():
                improvements.append(line.strip().lstrip("- ").strip())
        
        return improvements if improvements else ["Consider adding more detail"]
    
    def get_critique_stats(self) -> Dict[str, int]:
        """Get memory critique statistics."""
        return self.critique_stats.copy()
    
    async def periodic_memory_audit(self, vector_store, max_memories: int = 100) -> Dict[str, Any]:
        """
        Perform periodic audit of memory store quality.
        
        Args:
            vector_store: Vector store instance to audit
            max_memories: Maximum number of memories to audit
            
        Returns:
            Audit results and recommendations
        """
        print("🔍 Starting periodic memory audit...")
        
        # Get recent memories for audit
        recent_memories = await vector_store.search_memories(
            query="recent experiences and tasks",
            n_results=max_memories
        )
        
        if not recent_memories:
            return {"status": "no_memories", "action_needed": False}
        
        # Critique the memory set
        critiques = await self.critique_memory_set(recent_memories)
        
        # Analyze results
        low_quality = [c for c in critiques if c.quality_score.overall < 0.3]
        medium_quality = [c for c in critiques if 0.3 <= c.quality_score.overall < 0.7]
        high_quality = [c for c in critiques if c.quality_score.overall >= 0.7]
        
        recommendations = {
            "total_memories_audited": len(critiques),
            "high_quality_count": len(high_quality),
            "medium_quality_count": len(medium_quality),
            "low_quality_count": len(low_quality),
            "purge_candidates": [c.original_memory.get("id") for c in low_quality if not c.should_keep],
            "enhancement_candidates": [c.original_memory.get("id") for c in medium_quality if c.should_enhance],
            "consolidation_opportunities": sum(len(c.consolidation_candidates) for c in critiques),
            "average_quality": sum(c.quality_score.overall for c in critiques) / len(critiques) if critiques else 0,
            "action_needed": len(low_quality) > 0 or len(medium_quality) > 0
        }
        
        print(f"📊 Memory Audit Complete:")
        print(f"   High Quality: {len(high_quality)}")
        print(f"   Medium Quality: {len(medium_quality)}")
        print(f"   Low Quality: {len(low_quality)}")
        print(f"   Average Quality: {recommendations['average_quality']:.2f}")
        
        return recommendations 