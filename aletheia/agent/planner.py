"""Task planning and chain-of-thought reasoning."""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..llm.router import LLMRouter, TaskContext


@dataclass
class SubTask:
    """Represents a sub-task in a plan."""
    id: str
    description: str
    reasoning: str
    dependencies: List[str]
    estimated_difficulty: float  # 0-1 scale
    requires_external_llm: bool = False


@dataclass
class Plan:
    """Represents a complete task plan."""
    original_task: str
    subtasks: List[SubTask]
    execution_order: List[str]
    created_at: datetime
    reasoning: str


class TaskPlanner:
    """Plans and breaks down complex tasks using chain-of-thought reasoning."""

    def __init__(self, router: LLMRouter) -> None:
        """Initialize the planner."""
        self.router = router

    def create_planning_prompt(self, task: str) -> str:
        """Create a prompt for task planning."""
        return f"""I need to break down this task into smaller, manageable sub-tasks.

Task: {task}

Please analyze this task and break it down following these steps:

1. UNDERSTANDING: What is the core objective and what are the key requirements?

2. DECOMPOSITION: Break the task into 3-7 logical sub-tasks that:
   - Are specific and actionable
   - Build upon each other logically
   - Can be completed independently where possible
   - Cover all aspects of the original task

3. DEPENDENCIES: Identify which sub-tasks depend on others

4. COMPLEXITY: Rate each sub-task's difficulty (1-5 scale)

5. REASONING: Explain why this breakdown makes sense

Format your response as:

## Understanding
[Your analysis of the task]

## Sub-tasks
1. **Sub-task 1**: [Description]
   - Reasoning: [Why this is needed]
   - Dependencies: [List any dependencies]
   - Difficulty: [1-5 rating]

2. **Sub-task 2**: [Description]
   - Reasoning: [Why this is needed]
   - Dependencies: [List any dependencies]  
   - Difficulty: [1-5 rating]

[Continue for all sub-tasks]

## Execution Order
[Recommended order considering dependencies]

## Overall Strategy
[Explanation of the approach and why it will work]

Be thorough but concise. Focus on creating actionable sub-tasks."""

    async def create_plan(self, task: str) -> Optional[Plan]:
        """Create a plan for the given task."""
        
        # Create planning context
        planning_context = TaskContext(
            prompt=self.create_planning_prompt(task),
            max_tokens=1500,
            requires_deep_reasoning=True,
            cost_sensitive=False,  # Planning is worth the cost
        )

        try:
            # Execute planning
            result = await self.router.execute_task(planning_context)
            
            if not result.get("result"):
                print(f"Planning failed: {result.get('error', 'Unknown error')}")
                return None

            planning_output = result["result"]
            
            # Parse the planning output into structured plan
            plan = self._parse_planning_output(task, planning_output)
            
            if plan:
                print(f"✅ Created plan with {len(plan.subtasks)} sub-tasks")
                return plan
            else:
                print("⚠️  Failed to parse planning output")
                return None
                
        except Exception as e:
            print(f"Error creating plan: {e}")
            return None

    def _parse_planning_output(self, original_task: str, output: str) -> Optional[Plan]:
        """Parse LLM output into structured Plan object."""
        
        # This is a simplified parser - in production you'd want more robust parsing
        try:
            subtasks = []
            execution_order = []
            reasoning = ""
            
            lines = output.split('\n')
            current_section = None
            current_subtask = None
            
            for line in lines:
                line = line.strip()
                
                if not line:
                    continue
                    
                # Section headers
                if line.startswith('## Understanding'):
                    current_section = 'understanding'
                elif line.startswith('## Sub-tasks'):
                    current_section = 'subtasks'
                elif line.startswith('## Execution Order'):
                    current_section = 'execution'
                elif line.startswith('## Overall Strategy'):
                    current_section = 'strategy'
                elif line.startswith('#'):
                    current_section = None
                
                # Parse content based on section
                elif current_section == 'subtasks':
                    if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.')):
                        # New subtask
                        if '**' in line:
                            task_desc = line.split('**')[1] if '**' in line else line[3:].strip()
                            current_subtask = {
                                'id': f"subtask_{len(subtasks) + 1}",
                                'description': task_desc,
                                'reasoning': '',
                                'dependencies': [],
                                'difficulty': 0.5,
                            }
                            subtasks.append(current_subtask)
                    elif current_subtask and line.startswith('- Reasoning:'):
                        current_subtask['reasoning'] = line[12:].strip()
                    elif current_subtask and line.startswith('- Dependencies:'):
                        deps_text = line[15:].strip()
                        if deps_text.lower() not in ['none', 'none.', '']:
                            current_subtask['dependencies'] = [dep.strip() for dep in deps_text.split(',')]
                    elif current_subtask and line.startswith('- Difficulty:'):
                        try:
                            diff_text = line[13:].strip()
                            difficulty = float(diff_text.split()[0]) / 5.0  # Convert 1-5 to 0-1
                            current_subtask['difficulty'] = min(max(difficulty, 0.0), 1.0)
                        except:
                            current_subtask['difficulty'] = 0.5
                
                elif current_section == 'execution':
                    # Simple parsing of execution order
                    if any(char.isdigit() for char in line):
                        execution_order.append(line)
                
                elif current_section == 'strategy':
                    reasoning += line + " "
            
            # Convert dict subtasks to SubTask objects
            subtask_objects = []
            for i, st in enumerate(subtasks):
                subtask_obj = SubTask(
                    id=st['id'],
                    description=st['description'],
                    reasoning=st['reasoning'],
                    dependencies=st['dependencies'],
                    estimated_difficulty=st['difficulty'],
                    requires_external_llm=st['difficulty'] > 0.7,  # Hard tasks use external LLM
                )
                subtask_objects.append(subtask_obj)
            
            # Generate execution order if not parsed properly
            if not execution_order:
                execution_order = [st.id for st in subtask_objects]
            
            return Plan(
                original_task=original_task,
                subtasks=subtask_objects,
                execution_order=execution_order,
                created_at=datetime.now(),
                reasoning=reasoning.strip(),
            )
            
        except Exception as e:
            print(f"Error parsing planning output: {e}")
            return None

    async def refine_plan(self, plan: Plan, feedback: str) -> Optional[Plan]:
        """Refine an existing plan based on feedback."""
        
        refinement_prompt = f"""I have an existing plan that needs refinement based on feedback.

Original Task: {plan.original_task}

Current Plan:
{self._plan_to_text(plan)}

Feedback: {feedback}

Please provide an improved version of this plan that addresses the feedback while maintaining the same structure. Focus on:
1. Addressing specific issues mentioned in the feedback
2. Improving task descriptions or breaking down complex steps further
3. Adjusting dependencies if needed
4. Maintaining logical flow

Use the same format as before."""

        refinement_context = TaskContext(
            prompt=refinement_prompt,
            max_tokens=1500,
            requires_deep_reasoning=True,
        )

        try:
            result = await self.router.execute_task(refinement_context)
            
            if result.get("result"):
                refined_plan = self._parse_planning_output(plan.original_task, result["result"])
                if refined_plan:
                    print("✅ Plan refined successfully")
                    return refined_plan
            
            print("⚠️  Plan refinement failed, returning original")
            return plan
            
        except Exception as e:
            print(f"Error refining plan: {e}")
            return plan

    def _plan_to_text(self, plan: Plan) -> str:
        """Convert plan to text representation."""
        text = f"Sub-tasks:\n"
        for i, subtask in enumerate(plan.subtasks, 1):
            text += f"{i}. {subtask.description}\n"
            text += f"   - Reasoning: {subtask.reasoning}\n"
            text += f"   - Dependencies: {', '.join(subtask.dependencies) or 'None'}\n"
            text += f"   - Difficulty: {subtask.estimated_difficulty:.1f}\n\n"
        
        text += f"Execution Order: {' → '.join(plan.execution_order)}\n\n"
        text += f"Strategy: {plan.reasoning}"
        
        return text

    def get_next_task(self, plan: Plan, completed_tasks: List[str]) -> Optional[SubTask]:
        """Get the next task to execute based on dependencies."""
        
        for task_id in plan.execution_order:
            # Find the subtask
            subtask = next((st for st in plan.subtasks if st.id == task_id), None)
            if not subtask:
                continue
                
            # Skip if already completed
            if task_id in completed_tasks:
                continue
                
            # Check if dependencies are satisfied
            dependencies_met = all(dep_id in completed_tasks for dep_id in subtask.dependencies)
            
            if dependencies_met:
                return subtask
        
        return None

    def estimate_plan_complexity(self, plan: Plan) -> Dict[str, Any]:
        """Estimate overall plan complexity and resource requirements."""
        
        total_difficulty = sum(st.estimated_difficulty for st in plan.subtasks)
        avg_difficulty = total_difficulty / len(plan.subtasks) if plan.subtasks else 0
        
        external_llm_tasks = sum(1 for st in plan.subtasks if st.requires_external_llm)
        
        # Estimate time (very rough)
        estimated_minutes = len(plan.subtasks) * 2 + (external_llm_tasks * 3)
        
        return {
            "total_subtasks": len(plan.subtasks),
            "average_difficulty": avg_difficulty,
            "total_difficulty": total_difficulty,
            "external_llm_required": external_llm_tasks,
            "estimated_time_minutes": estimated_minutes,
            "complexity_level": "High" if avg_difficulty > 0.7 else "Medium" if avg_difficulty > 0.4 else "Low",
        } 