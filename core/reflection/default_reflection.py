"""
Default Reflection Engine for Prometheus Framework

Provides basic self-reflection capabilities that entities can use
or override with their own reflection behavior.
"""

import random
from typing import Any

from ..base_entity import BaseReflection


class DefaultReflection(BaseReflection):
    """Default reflection engine implementation."""

    async def should_reflect(self, complexity: float) -> bool:
        """
        Determine if reflection is needed based on task complexity.

        Simple probabilistic model - entities can override for
        more sophisticated reflection triggers.
        """

        # Higher complexity increases reflection probability
        reflection_probability = min(complexity * 0.5, 0.8)
        return random.random() < reflection_probability

    async def reflect_on_task(self, task: str, response: str, context: dict[str, Any]) -> dict[str, Any] | None:
        """
        Reflect on a completed task.

        Basic implementation that entities can override for
        more sophisticated self-reflection.
        """

        # Create a simple reflection structure
        return {
            "task": task,
            "response": response,
            "confidence_score": 0.7,  # Default moderate confidence
            "critique": "Task completed with standard approach.",
            "improvements": ["Consider alternative approaches", "Gather more context"],
            "approach": "default_reflection"
        }


    def create_reflection_prompt(self, task: str, response: str) -> str:
        """Create a reflection prompt for the task and response."""
        return f"""Please reflect on this task completion:

Task: {task}
Response: {response}

Provide a critical self-assessment including:
1. Confidence level in the response
2. Potential improvements
3. Alternative approaches
4. Quality of reasoning
5. Areas for learning

Be honest about limitations and areas for improvement."""
