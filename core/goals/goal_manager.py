"""
Goal Manager for Prometheus Framework

Manages entity goals and autonomous task processing.
Provides interface to processing extractors as suggested by o3.
"""

from typing import Any


class GoalManager:
    """
    Manages goals and autonomous tasks for entities.

    Provides interface to processing extractors without directly
    importing processing.pipeline (as suggested by o3).
    """

    def __init__(self):
        """Initialize the goal manager."""
        self.active_goals: list[dict[str, Any]] = []
        self.completed_goals: list[dict[str, Any]] = []
        self._extractor_interface = None

    def set_extractor_interface(self, extractor_interface):
        """
        Set the extractor interface for knowledge gap detection.

        This allows goal manager to use extractors without importing
        processing.pipeline directly (o3's suggestion).
        """
        self._extractor_interface = extractor_interface

    async def process_autonomous_goals(self) -> None:
        """Process autonomous goals and tasks."""
        # Placeholder for autonomous goal processing
        if not self.active_goals:
            return

        print(f"🎯 Processing {len(self.active_goals)} active goals...")

        # Future implementation will handle:
        # - Knowledge gap identification using extractor interface
        # - Goal prioritization
        # - Autonomous task execution
        # - Goal completion tracking

    async def add_goal(self, goal_description: str, priority: int = 5) -> str:
        """Add a new goal."""
        goal = {
            "id": f"goal_{len(self.active_goals) + len(self.completed_goals)}",
            "description": goal_description,
            "priority": priority,
            "created_at": None,  # Will use datetime
            "status": "active"
        }

        self.active_goals.append(goal)
        return goal["id"]

    async def complete_goal(self, goal_id: str) -> bool:
        """Mark a goal as completed."""
        for i, goal in enumerate(self.active_goals):
            if goal["id"] == goal_id:
                goal["status"] = "completed"
                self.completed_goals.append(self.active_goals.pop(i))
                return True
        return False

    def get_active_goals(self) -> list[dict[str, Any]]:
        """Get list of active goals."""
        return self.active_goals.copy()

    def get_completed_goals(self) -> list[dict[str, Any]]:
        """Get list of completed goals."""
        return self.completed_goals.copy()
