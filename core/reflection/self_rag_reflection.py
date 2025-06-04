"""
Self-RAG Enhanced Reflection Module

Advanced self-reflection capabilities inspired by Self-RAG paper.
Provides quality assessment, response critique, and improvement suggestions.
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass

from ..base_entity import BaseReflection
from ..llm.fast_llm import FastLLM


@dataclass
class ResponseQualityAssessment:
    """Assessment of response quality."""
    accuracy: float  # 0-1 score
    completeness: float  # 0-1 score
    relevance: float  # 0-1 score
    helpfulness: float  # 0-1 score
    overall: float  # Combined score
    confidence: str  # high/medium/low
    critique: str  # Detailed critique
    improvement_areas: List[str]


@dataclass
class RetrievalQualityAssessment:
    """Assessment of context retrieval quality."""
    relevance_score: float  # How relevant was retrieved context
    sufficiency_score: float  # Was enough context retrieved
    accuracy_score: float  # Was retrieved context accurate
    redundancy_score: float  # Was there unnecessary redundancy
    suggestions: List[str]  # Improvement suggestions


class SelfRAGReflection(BaseReflection):
    """
    Enhanced reflection engine with Self-RAG capabilities.
    
    Provides sophisticated response quality assessment,
    retrieval evaluation, and continuous improvement.
    """
    
    def __init__(self, identity_config: Optional[dict] = None):
        """Initialize with fast LLM for reflection."""
        self.utility_llm = FastLLM(identity_config=identity_config)
        self.reflection_stats = {
            "reflections_performed": 0,
            "quality_assessments": 0,
            "retrieval_assessments": 0,
            "improvement_suggestions": 0
        }
    
    async def should_reflect(self, complexity: float) -> bool:
        """
        Enhanced reflection trigger using multiple factors.
        
        Args:
            complexity: Task complexity score
            
        Returns:
            Whether reflection should be performed
        """
        # Base probability from complexity
        base_probability = min(complexity * 0.6, 0.9)
        
        # Increase probability for medium complexity tasks (most benefit)
        if 0.3 <= complexity <= 0.7:
            base_probability += 0.2
        
        # Random factor
        import random
        return random.random() < base_probability
    
    async def reflect_on_task(self, task: str, response: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Enhanced reflection with comprehensive quality assessment.
        
        Args:
            task: The original task/query
            response: The generated response
            context: Additional context including retrieval info
            
        Returns:
            Comprehensive reflection with quality scores
        """
        try:
            # Perform multiple types of assessment
            response_quality = await self._assess_response_quality(task, response, context)
            retrieval_quality = await self._assess_retrieval_quality(task, context)
            
            # Generate overall reflection
            overall_reflection = await self._generate_comprehensive_reflection(
                task, response, response_quality, retrieval_quality, context
            )
            
            self.reflection_stats["reflections_performed"] += 1
            
            return {
                "task": task,
                "response": response,
                "response_quality": response_quality,
                "retrieval_quality": retrieval_quality,
                "overall_reflection": overall_reflection,
                "timestamp": datetime.now().isoformat(),
                "approach": "self_rag_reflection"
            }
            
        except Exception as e:
            print(f"⚠️ Enhanced reflection failed: {e}")
            # Fallback to basic reflection
            return await super().reflect_on_task(task, response, context)
    
    async def _assess_response_quality(self, task: str, response: str, context: Dict[str, Any]) -> ResponseQualityAssessment:
        """
        Assess the quality of a generated response.
        
        Args:
            task: Original task
            response: Generated response
            context: Task context
            
        Returns:
            Quality assessment with scores and critique
        """
        prompt = f"""Assess the quality of this response to the given task:

TASK: {task}

RESPONSE: {response}

Evaluate the response on these dimensions (score 0.0-1.0):
1. ACCURACY: Is the response factually correct and accurate?
2. COMPLETENESS: Does it fully address the task requirements?
3. RELEVANCE: Is the response relevant to the specific question?
4. HELPFULNESS: How helpful is this response to the user?

Also assess:
- CONFIDENCE: How confident are you in this response? (high/medium/low)
- CRITIQUE: What are the main strengths and weaknesses?
- IMPROVEMENTS: What specific improvements would enhance this response?

Format your response as:
ACCURACY: [0.0-1.0]
COMPLETENESS: [0.0-1.0]
RELEVANCE: [0.0-1.0]
HELPFULNESS: [0.0-1.0]
CONFIDENCE: [high/medium/low]
CRITIQUE: [detailed analysis]
IMPROVEMENTS: [specific suggestions]"""

        try:
            result = await self.utility_llm.classify_prompt(
                prompt=prompt,
                classification_type="response_quality_assessment"
            )
            
            response_text = result.get("classification", "")
            
            # Parse the assessment
            scores = self._parse_quality_scores(response_text)
            confidence = self._extract_confidence(response_text)
            critique = self._extract_critique(response_text)
            improvements = self._extract_improvements(response_text)
            
            overall_score = (scores["accuracy"] + scores["completeness"] + 
                           scores["relevance"] + scores["helpfulness"]) / 4
            
            self.reflection_stats["quality_assessments"] += 1
            
            return ResponseQualityAssessment(
                accuracy=scores["accuracy"],
                completeness=scores["completeness"],
                relevance=scores["relevance"],
                helpfulness=scores["helpfulness"],
                overall=overall_score,
                confidence=confidence,
                critique=critique,
                improvement_areas=improvements
            )
            
        except Exception as e:
            print(f"⚠️ Response quality assessment failed: {e}")
            return ResponseQualityAssessment(
                accuracy=0.5, completeness=0.5, relevance=0.5, helpfulness=0.5,
                overall=0.5, confidence="medium", critique="Assessment failed",
                improvement_areas=["Unable to assess"]
            )
    
    async def _assess_retrieval_quality(self, task: str, context: Dict[str, Any]) -> RetrievalQualityAssessment:
        """
        Assess the quality of context retrieval for the task.
        
        Args:
            task: Original task
            context: Retrieved context and metadata
            
        Returns:
            Retrieval quality assessment
        """
        retrieved_context = context.get("conversation_context", "")
        memory_context = context.get("memory_context", "")
        
        if not retrieved_context and not memory_context:
            # No retrieval to assess
            return RetrievalQualityAssessment(
                relevance_score=1.0, sufficiency_score=1.0, accuracy_score=1.0,
                redundancy_score=1.0, suggestions=["No retrieval performed"]
            )
        
        prompt = f"""Assess the quality of context retrieval for this task:

TASK: {task}

RETRIEVED CONVERSATION CONTEXT:
{retrieved_context[:500] if retrieved_context else "None"}

RETRIEVED MEMORY CONTEXT:
{memory_context[:500] if memory_context else "None"}

Evaluate the retrieval quality (score 0.0-1.0):
1. RELEVANCE: How relevant is the retrieved context to the task?
2. SUFFICIENCY: Is there enough context to answer properly?
3. ACCURACY: Is the retrieved context accurate and reliable?
4. REDUNDANCY: Is there unnecessary redundant information? (1.0 = no redundancy)

Provide specific suggestions for improving context retrieval.

Format your response as:
RELEVANCE: [0.0-1.0]
SUFFICIENCY: [0.0-1.0]
ACCURACY: [0.0-1.0]
REDUNDANCY: [0.0-1.0]
SUGGESTIONS: [specific improvement suggestions]"""

        try:
            result = await self.utility_llm.classify_prompt(
                prompt=prompt,
                classification_type="retrieval_quality_assessment"
            )
            
            response_text = result.get("classification", "")
            
            # Parse the assessment
            scores = self._parse_retrieval_scores(response_text)
            suggestions = self._extract_suggestions(response_text)
            
            self.reflection_stats["retrieval_assessments"] += 1
            
            return RetrievalQualityAssessment(
                relevance_score=scores["relevance"],
                sufficiency_score=scores["sufficiency"],
                accuracy_score=scores["accuracy"],
                redundancy_score=scores["redundancy"],
                suggestions=suggestions
            )
            
        except Exception as e:
            print(f"⚠️ Retrieval quality assessment failed: {e}")
            return RetrievalQualityAssessment(
                relevance_score=0.5, sufficiency_score=0.5, accuracy_score=0.5,
                redundancy_score=0.5, suggestions=["Assessment failed"]
            )
    
    async def _generate_comprehensive_reflection(self, 
                                              task: str, 
                                              response: str,
                                              response_quality: ResponseQualityAssessment,
                                              retrieval_quality: RetrievalQualityAssessment,
                                              context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive reflection combining all assessments.
        
        Returns:
            Comprehensive reflection with actionable insights
        """
        prompt = f"""Generate a comprehensive reflection on this task completion:

TASK: {task}
RESPONSE: {response[:300]}...

RESPONSE QUALITY SCORES:
- Overall: {response_quality.overall:.2f}
- Accuracy: {response_quality.accuracy:.2f}
- Completeness: {response_quality.completeness:.2f}
- Relevance: {response_quality.relevance:.2f}
- Helpfulness: {response_quality.helpfulness:.2f}
- Confidence: {response_quality.confidence}

RETRIEVAL QUALITY SCORES:
- Relevance: {retrieval_quality.relevance_score:.2f}
- Sufficiency: {retrieval_quality.sufficiency_score:.2f}
- Accuracy: {retrieval_quality.accuracy_score:.2f}

Based on these assessments, provide:
1. Key insights about performance
2. Priority improvement areas
3. Specific action items for next time
4. Overall performance rating (excellent/good/satisfactory/needs_improvement)

Keep the reflection concise but actionable."""

        try:
            result = await self.utility_llm.classify_prompt(
                prompt=prompt,
                classification_type="comprehensive_reflection"
            )
            
            reflection_text = result.get("classification", "")
            
            return {
                "comprehensive_reflection": reflection_text,
                "overall_score": (response_quality.overall + 
                                (retrieval_quality.relevance_score + retrieval_quality.sufficiency_score) / 2) / 2,
                "key_insights": self._extract_insights(reflection_text),
                "priority_improvements": response_quality.improvement_areas[:3],  # Top 3
                "action_items": retrieval_quality.suggestions[:2]  # Top 2
            }
            
        except Exception as e:
            print(f"⚠️ Comprehensive reflection failed: {e}")
            return {
                "comprehensive_reflection": "Reflection generation failed",
                "overall_score": 0.5,
                "key_insights": ["Unable to generate insights"],
                "priority_improvements": ["Unable to assess"],
                "action_items": ["Unable to provide actions"]
            }
    
    def _parse_quality_scores(self, response: str) -> Dict[str, float]:
        """Parse quality scores from response."""
        scores = {"accuracy": 0.5, "completeness": 0.5, "relevance": 0.5, "helpfulness": 0.5}
        
        lines = response.split('\n')
        for line in lines:
            line = line.strip().upper()
            if line.startswith("ACCURACY:"):
                try:
                    scores["accuracy"] = float(line.split(":")[1].strip())
                except:
                    pass
            elif line.startswith("COMPLETENESS:"):
                try:
                    scores["completeness"] = float(line.split(":")[1].strip())
                except:
                    pass
            elif line.startswith("RELEVANCE:"):
                try:
                    scores["relevance"] = float(line.split(":")[1].strip())
                except:
                    pass
            elif line.startswith("HELPFULNESS:"):
                try:
                    scores["helpfulness"] = float(line.split(":")[1].strip())
                except:
                    pass
        
        return scores
    
    def _parse_retrieval_scores(self, response: str) -> Dict[str, float]:
        """Parse retrieval quality scores from response."""
        scores = {"relevance": 0.5, "sufficiency": 0.5, "accuracy": 0.5, "redundancy": 0.5}
        
        lines = response.split('\n')
        for line in lines:
            line = line.strip().upper()
            if line.startswith("RELEVANCE:"):
                try:
                    scores["relevance"] = float(line.split(":")[1].strip())
                except:
                    pass
            elif line.startswith("SUFFICIENCY:"):
                try:
                    scores["sufficiency"] = float(line.split(":")[1].strip())
                except:
                    pass
            elif line.startswith("ACCURACY:"):
                try:
                    scores["accuracy"] = float(line.split(":")[1].strip())
                except:
                    pass
            elif line.startswith("REDUNDANCY:"):
                try:
                    scores["redundancy"] = float(line.split(":")[1].strip())
                except:
                    pass
        
        return scores
    
    def _extract_confidence(self, response: str) -> str:
        """Extract confidence level from response."""
        lines = response.split('\n')
        for line in lines:
            if line.strip().upper().startswith("CONFIDENCE:"):
                confidence = line.split(":", 1)[1].strip().lower()
                if confidence in ["high", "medium", "low"]:
                    return confidence
        return "medium"  # Default
    
    def _extract_critique(self, response: str) -> str:
        """Extract critique from response."""
        lines = response.split('\n')
        critique_lines = []
        capturing = False
        
        for line in lines:
            if line.strip().upper().startswith("CRITIQUE:"):
                capturing = True
                critique_content = line.split(":", 1)[1].strip() if ":" in line else ""
                if critique_content:
                    critique_lines.append(critique_content)
            elif capturing and line.strip().upper().startswith("IMPROVEMENTS:"):
                break
            elif capturing and line.strip():
                critique_lines.append(line.strip())
        
        return " ".join(critique_lines) if critique_lines else "No critique provided"
    
    def _extract_improvements(self, response: str) -> List[str]:
        """Extract improvement suggestions from response."""
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
        
        return improvements if improvements else ["Consider general improvements"]
    
    def _extract_suggestions(self, response: str) -> List[str]:
        """Extract suggestions from retrieval assessment."""
        lines = response.split('\n')
        suggestions = []
        capturing = False
        
        for line in lines:
            if line.strip().upper().startswith("SUGGESTIONS:"):
                capturing = True
                suggestion_content = line.split(":", 1)[1].strip() if ":" in line else ""
                if suggestion_content:
                    suggestions.append(suggestion_content.lstrip("- ").strip())
            elif capturing and line.strip():
                suggestions.append(line.strip().lstrip("- ").strip())
        
        return suggestions if suggestions else ["No specific suggestions"]
    
    def _extract_insights(self, reflection: str) -> List[str]:
        """Extract key insights from comprehensive reflection."""
        # Simple extraction - look for numbered points or bullet points
        insights = []
        lines = reflection.split('\n')
        
        for line in lines:
            line = line.strip()
            if (line.startswith(('1.', '2.', '3.', '-', '•')) or 
                'insight' in line.lower() or 'key' in line.lower()):
                clean_line = line.lstrip('123456789.-• ').strip()
                if clean_line and len(clean_line) > 10:
                    insights.append(clean_line)
        
        return insights[:3] if insights else ["General performance analysis completed"]
    
    def get_reflection_stats(self) -> Dict[str, int]:
        """Get reflection statistics."""
        return self.reflection_stats.copy()
    
    def create_reflection_prompt(self, task: str, response: str) -> str:
        """Create enhanced reflection prompt."""
        return f"""Perform comprehensive self-reflection on this task completion:

Task: {task}
Response: {response}

Provide detailed analysis including:
1. Response quality assessment (accuracy, completeness, relevance, helpfulness)
2. Confidence level in the response
3. Potential improvements and alternative approaches
4. Context retrieval effectiveness
5. Learning opportunities

Be specific and actionable in your feedback.""" 