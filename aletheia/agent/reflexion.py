"""Self-reflection and critique module for continuous improvement."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from ..llm.router import LLMRouter, TaskContext
from ..memory.vector_store import VectorStore


@dataclass
class ReflectionResult:
    """Result of a self-reflection process."""
    original_task: str
    agent_response: str
    critique: str
    improvements: list[str]
    confidence_score: float  # 0-1
    should_retry: bool
    created_at: datetime


class ReflectionEngine:
    """Handles agent self-reflection and continuous improvement."""

    def __init__(self, router: LLMRouter, vector_store: VectorStore) -> None:
        """Initialize the reflection engine."""
        self.router = router
        self.vector_store = vector_store

    def create_reflection_prompt(
        self,
        task: str,
        response: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """Create a prompt for self-reflection."""

        context_str = ""
        if context:
            context_str = f"\nAdditional Context:\n{context}\n"

        return f"""I need to critically evaluate my performance on a task and identify areas for improvement.

Original Task: {task}

My Response: {response}{context_str}

Please perform a thorough self-critique following these steps:

1. EVALUATION: How well did I complete the task?
   - Did I address all requirements?
   - Was my response accurate and helpful?
   - Are there any obvious errors or omissions?

2. CRITIQUE: What specific issues can I identify?
   - Factual errors or inaccuracies
   - Missing important points
   - Poor structure or clarity
   - Insufficient depth or detail
   - Irrelevant information

3. IMPROVEMENTS: How could I have done better?
   - What should I have included?
   - How could I improve the structure?
   - What knowledge gaps need to be filled?
   - What alternative approaches might work better?

4. CONFIDENCE: Rate my confidence in the original response (1-10)

5. RETRY RECOMMENDATION: Should this task be attempted again with improvements?

Format your response as:

## Evaluation
[Overall assessment of performance]

## Critique
[Specific issues identified]
- Issue 1: [Description]
- Issue 2: [Description]
[Continue as needed]

## Improvements
[Specific suggestions for improvement]
- Improvement 1: [Description]
- Improvement 2: [Description]
[Continue as needed]

## Confidence Score
[1-10 rating with explanation]

## Retry Recommendation
[Yes/No with reasoning]

Be honest and thorough in your self-assessment. Focus on constructive criticism that leads to actionable improvements."""

    async def reflect_on_task(
        self,
        task: str,
        response: str,
        context: Optional[dict[str, Any]] = None,
    ) -> Optional[ReflectionResult]:
        """Perform self-reflection on a completed task."""

        print("🤔 Starting self-reflection...")

        # Create reflection context
        reflection_context = TaskContext(
            prompt=self.create_reflection_prompt(task, response, context),
            max_tokens=1000,
            requires_deep_reasoning=True,
            cost_sensitive=False,  # Reflection is worth the cost
        )

        try:
            # Execute reflection
            result = await self.router.execute_task(reflection_context)

            if not result.get("result"):
                print(f"Reflection failed: {result.get('error', 'Unknown error')}")
                return None

            reflection_output = result["result"]

            # Parse the reflection output
            reflection_result = self._parse_reflection_output(
                task, response, reflection_output
            )

            if reflection_result:
                # Store reflection in memory
                await self.vector_store.store_reflection(
                    task=task,
                    critique=reflection_result.critique,
                    improvements="\n".join(reflection_result.improvements),
                    metadata={
                        "confidence_score": reflection_result.confidence_score,
                        "should_retry": reflection_result.should_retry,
                        "response_length": len(response),
                    },
                )

                print(f"✅ Reflection completed (confidence: {reflection_result.confidence_score:.1f})")
                return reflection_result
            else:
                print("⚠️  Failed to parse reflection output")
                return None

        except Exception as e:
            print(f"Error during reflection: {e}")
            return None

    def _parse_reflection_output(
        self,
        task: str,
        response: str,
        output: str,
    ) -> Optional[ReflectionResult]:
        """Parse reflection output into structured result."""

        try:
            evaluation = ""
            critique = ""
            improvements = []
            confidence_score = 0.5
            should_retry = False

            lines = output.split("\n")
            current_section = None

            for line in lines:
                line = line.strip()

                if not line:
                    continue

                # Section headers
                if line.startswith("## Evaluation"):
                    current_section = "evaluation"
                elif line.startswith("## Critique"):
                    current_section = "critique"
                elif line.startswith("## Improvements"):
                    current_section = "improvements"
                elif line.startswith("## Confidence Score"):
                    current_section = "confidence"
                elif line.startswith("## Retry Recommendation"):
                    current_section = "retry"
                elif line.startswith("#"):
                    current_section = None

                # Parse content based on section
                elif current_section == "evaluation":
                    evaluation += line + " "

                elif current_section == "critique":
                    if line.startswith("- "):
                        critique += line[2:] + "\n"
                    else:
                        critique += line + " "

                elif current_section == "improvements":
                    if line.startswith("- "):
                        improvements.append(line[2:])
                    elif line and not line.startswith("["):
                        improvements.append(line)

                elif current_section == "confidence":
                    # Extract confidence score
                    try:
                        # Look for numbers in the line
                        import re
                        numbers = re.findall(r"\d+", line)
                        if numbers:
                            score = float(numbers[0])
                            confidence_score = min(max(score / 10.0, 0.0), 1.0)
                    except:
                        confidence_score = 0.5

                elif current_section == "retry":
                    should_retry = "yes" in line.lower()

            return ReflectionResult(
                original_task=task,
                agent_response=response,
                critique=critique.strip(),
                improvements=improvements,
                confidence_score=confidence_score,
                should_retry=should_retry,
                created_at=datetime.now(),
            )

        except Exception as e:
            print(f"Error parsing reflection output: {e}")
            return None

    async def get_relevant_lessons(self, current_task: str, limit: int = 5) -> list[dict[str, Any]]:
        """Get relevant lessons learned from past reflections."""

        try:
            # Search for relevant reflections
            memories = await self.vector_store.search_memories(
                query=current_task,
                n_results=limit,
                memory_type="reflection",
            )

            lessons = []
            for memory in memories:
                lessons.append({
                    "content": memory["content"],
                    "metadata": memory["metadata"],
                    "relevance_score": 1.0 - (memory.get("distance", 0.5) or 0.5),
                })

            return lessons

        except Exception as e:
            print(f"Error retrieving lessons: {e}")
            return []

    async def create_improvement_plan(
        self,
        reflection: ReflectionResult,
    ) -> Optional[str]:
        """Create an actionable improvement plan based on reflection."""

        improvements_text = "\n".join([f"- {imp}" for imp in reflection.improvements])

        plan_prompt = f"""Based on my self-reflection, I need to create an actionable improvement plan.

Original Task: {reflection.original_task}

Issues Identified:
{reflection.critique}

Suggested Improvements:
{improvements_text}

Confidence Score: {reflection.confidence_score:.1f}/1.0

Please create a specific, actionable improvement plan that addresses these issues. The plan should:
1. Prioritize the most important improvements
2. Provide concrete steps I can take
3. Include specific knowledge or skills to develop
4. Suggest process changes for future similar tasks

Focus on practical, implementable changes."""

        planning_context = TaskContext(
            prompt=plan_prompt,
            max_tokens=800,
            requires_deep_reasoning=True,
        )

        try:
            result = await self.router.execute_task(planning_context)

            if result.get("result"):
                # Store the improvement plan
                await self.vector_store.store_memory(
                    content=result["result"],
                    memory_type="improvement_plan",
                    metadata={
                        "original_task": reflection.original_task,
                        "confidence_score": reflection.confidence_score,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

                return result["result"]

        except Exception as e:
            print(f"Error creating improvement plan: {e}")

        return None

    async def analyze_performance_trends(self, days_back: int = 7) -> dict[str, Any]:
        """Analyze performance trends from recent reflections."""

        try:
            # Get recent reflections
            recent_reflections = await self.vector_store.search_memories(
                query="reflection analysis performance",
                n_results=50,
                memory_type="reflection",
            )

            if not recent_reflections:
                return {"message": "No recent reflections found"}

            # Extract confidence scores and trends
            confidence_scores = []
            common_issues = {}
            improvement_areas = {}

            for reflection in recent_reflections:
                metadata = reflection.get("metadata", {})

                # Confidence trends
                if "confidence_score" in metadata:
                    confidence_scores.append(float(metadata["confidence_score"]))

                # Parse content for common patterns
                content = reflection.get("content", "")

                # Simple keyword analysis for common issues
                if "accuracy" in content.lower():
                    common_issues["accuracy"] = common_issues.get("accuracy", 0) + 1
                if "clarity" in content.lower():
                    common_issues["clarity"] = common_issues.get("clarity", 0) + 1
                if "completeness" in content.lower():
                    common_issues["completeness"] = common_issues.get("completeness", 0) + 1
                if "structure" in content.lower():
                    common_issues["structure"] = common_issues.get("structure", 0) + 1

            # Calculate trends
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

            # Recent vs older confidence
            if len(confidence_scores) >= 6:
                recent_avg = sum(confidence_scores[:3]) / 3
                older_avg = sum(confidence_scores[-3:]) / 3
                trend = "improving" if recent_avg > older_avg else "declining" if recent_avg < older_avg else "stable"
            else:
                trend = "insufficient_data"

            return {
                "total_reflections": len(recent_reflections),
                "average_confidence": avg_confidence,
                "confidence_trend": trend,
                "common_issues": dict(sorted(common_issues.items(), key=lambda x: x[1], reverse=True)),
                "recent_confidence_scores": confidence_scores[:10],  # Last 10
            }

        except Exception as e:
            print(f"Error analyzing performance trends: {e}")
            return {"error": str(e)}

    async def should_reflect(self, task_complexity: float = 0.5) -> bool:
        """Determine if reflection should be performed for a task."""

        # More conservative reflection strategy to reduce external API usage

        # Always reflect on very complex tasks
        if task_complexity > 0.8:
            return True

        # Reflect less frequently on medium complexity tasks
        if task_complexity > 0.6:
            import random
            return random.random() < 0.3  # Reduced from 0.5

        # Rarely reflect on simple tasks
        import random
        return random.random() < 0.1  # Reduced from 0.2
