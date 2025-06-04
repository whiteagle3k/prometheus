"""
Default Planner for Prometheus Framework

Provides basic task planning capabilities that entities can use
or override with their own planning behavior.
"""

from typing import Dict, Any, Optional
from ..base_entity import BasePlanner


class DefaultPlanner(BasePlanner):
    """Default task planner implementation."""
    
    async def create_plan(self, task: str) -> Optional[Dict[str, Any]]:
        """
        Create a basic plan for the given task.
        
        This is a minimal implementation that entities can override
        for more sophisticated planning behavior.
        """
        
        # For now, just return a simple plan structure
        # Real implementation would analyze the task and create subtasks
        plan = {
            "original_task": task,
            "subtasks": [
                {
                    "id": "subtask_1",
                    "description": f"Analyze: {task[:50]}...",
                    "requires_external_llm": False
                },
                {
                    "id": "subtask_2", 
                    "description": f"Execute: {task[:50]}...",
                    "requires_external_llm": True
                }
            ],
            "approach": "default_planning"
        }
        
        return plan
    
    def create_planning_prompt(self, task: str) -> str:
        """Create a planning prompt for the task."""
        return f"""Please analyze this task and break it down into subtasks:

Task: {task}

Please provide a structured decomposition with:
1. Clear sub-task identification
2. Dependencies between tasks
3. Resource requirements
4. Expected outcomes

Structure your response as a detailed plan.""" 