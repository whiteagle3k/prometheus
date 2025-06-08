"""
Supervisor Entity - Development Task Manager

Autonomous agent that:
1. Takes high-level briefs from users
2. Breaks them into atomic development tasks
3. Coordinates task execution through queue system
4. Manages development workflow
"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from core.base_entity import BaseEntity
from core.task_queue.queue import push, pop, HIGHLEVEL_IN, DEVTASKS_WAITING


class SupervisorEntity(BaseEntity):
    """Development supervisor agent that manages task decomposition and coordination."""
    
    IDENTITY_PATH = Path(__file__).parent / "identity"
    
    def __init__(self):
        super().__init__()
        self._running = False
    
    def _load_identity(self) -> Dict[str, Any]:
        """Load supervisor identity configuration."""
        identity_file = self.IDENTITY_PATH / "identity.json"
        
        # Fallback identity configuration
        fallback_identity = {
            "name": "Петрович",
            "version": "0.1.0",
            "description": "Development task supervisor and coordinator agent",
            "identity": {
                "summary": "Analytical development manager focused on task decomposition and workflow coordination",
                "personality": ["systematic", "clear", "efficient", "quality-focused", "organized"]
            },
            "core_values": ["clarity", "atomicity", "efficiency", "quality", "progress"],
            "llm_instructions": "You are a development supervisor agent focused on breaking down complex tasks into atomic, implementable units with clear acceptance criteria.",
            "external_llms": {
                "primary_provider": "openai",
                "providers": {
                    "openai": {
                        "enabled": True,
                        "model": "gpt-4o-mini",
                        "temperature": 0.3,
                        "max_tokens": 3000
                    }
                },
                "routing_preferences": {
                    "prefer_external": True
                }
            }
        }
        
        if not identity_file.exists():
            print(f"⚠️ Supervisor identity file not found: {identity_file}")
            print("   Using fallback configuration")
            return fallback_identity
        
        try:
            with open(identity_file, encoding="utf-8") as f:
                loaded_config = json.load(f)
            
            print(f"✅ Loaded supervisor identity from: {identity_file}")
            
            # Merge with fallback defaults
            merged_config = {**fallback_identity, **loaded_config}
            return merged_config
            
        except Exception as e:
            print(f"⚠️ Error loading supervisor identity: {e}")
            return fallback_identity
    
    async def autonomous_loop(self):
        """Main autonomous processing loop."""
        print("🎯 Supervisor: Starting autonomous task processing loop...")
        self._running = True
        
        while self._running:
            try:
                print("🔄 Supervisor: Waiting for high-level tasks...")
                brief = pop(HIGHLEVEL_IN)  # Blocking pop - waits for tasks
                
                print(f"📋 Supervisor: Received task brief: {brief.get('brief', 'Unknown')}")
                
                # Plan and decompose the brief into subtasks
                subtasks = await self.plan(brief)
                
                print(f"✅ Supervisor: Created {len(subtasks)} subtasks")
                
                # Queue each subtask for workers
                for task in subtasks:
                    push(DEVTASKS_WAITING, task)
                    print(f"📤 Supervisor: Queued task: {task.get('title', 'Untitled')}")
                
            except KeyboardInterrupt:
                print("🛑 Supervisor: Shutting down...")
                self._running = False
                break
            except Exception as e:
                print(f"❌ Supervisor: Error in autonomous loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def plan(self, brief: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Break down high-level brief into atomic development tasks.
        
        Args:
            brief: High-level task description
            
        Returns:
            List of atomic development tasks
        """
        brief_text = brief.get("brief", "")
        context = brief.get("context", "")
        priority = brief.get("priority", "normal")
        
        # Detailed planning prompt for task decomposition
        planning_prompt = f"""You are a development supervisor. Break down this high-level task into specific, atomic development tasks.

High-level brief: {brief_text}
Context: {context}
Priority: {priority}

For each atomic task, provide:
1. Clear, specific title
2. Detailed description of what needs to be done
3. File paths that need to be modified/created
4. Acceptance criteria
5. Estimated complexity (low/medium/high)
6. Dependencies on other tasks

Return a JSON list of tasks with this structure:
[
  {{
    "id": "unique_task_id",
    "title": "Clear task title",
    "description": "Detailed task description",
    "files": ["path/to/file1.py", "path/to/file2.py"],
    "acceptance_criteria": ["Criterion 1", "Criterion 2"],
    "complexity": "medium",
    "dependencies": ["task_id_1", "task_id_2"],
    "type": "implementation|test|documentation|refactor"
  }}
]

Make tasks atomic and independently testable. Ensure proper ordering and dependencies."""

        try:
            # Use external LLM for planning (OpenAI/Claude)
            response = await self._call_external_llm(planning_prompt)
            
            # Parse the response as JSON
            if isinstance(response, str):
                # Try to extract JSON from response
                response = response.strip()
                if response.startswith("```json"):
                    response = response[7:]
                if response.endswith("```"):
                    response = response[:-3]
                response = response.strip()
                
                subtasks = json.loads(response)
            else:
                subtasks = response
            
            # Add metadata to each task
            base_id = str(uuid.uuid4())[:8]
            for i, task in enumerate(subtasks):
                task["id"] = f"{base_id}_{i+1}"
                task["brief_id"] = brief.get("id", base_id)
                task["created_at"] = datetime.now().isoformat()
                task["status"] = "waiting"
                task["priority"] = priority
            
            return subtasks
            
        except Exception as e:
            print(f"❌ Supervisor: Planning failed: {e}")
            
            # Fallback: Create a single task from the brief
            fallback_task = {
                "id": str(uuid.uuid4())[:8],
                "title": brief_text[:50] + "..." if len(brief_text) > 50 else brief_text,
                "description": f"Implement: {brief_text}",
                "files": [],
                "acceptance_criteria": ["Task completed successfully"],
                "complexity": "medium",
                "dependencies": [],
                "type": "implementation",
                "brief_id": brief.get("id", "unknown"),
                "created_at": datetime.now().isoformat(),
                "status": "waiting",
                "priority": priority
            }
            
            return [fallback_task]
    
    async def _call_external_llm(self, prompt: str) -> str:
        """Call external LLM for planning."""
        try:
            # Use the entity's LLM routing system
            response = await self.think(prompt, user_id="supervisor_system")
            return response
        except Exception as e:
            print(f"❌ Supervisor: External LLM call failed: {e}")
            raise
    
    def stop_autonomous_loop(self):
        """Stop the autonomous processing loop."""
        self._running = False
    
    async def start_autonomous_loop(self):
        """Start the autonomous processing loop in background."""
        if not self._running:
            print("🚀 Starting supervisor autonomous loop...")
            asyncio.create_task(self.autonomous_loop())
            return {"status": "started", "message": "Autonomous loop started"}
        else:
            return {"status": "already_running", "message": "Autonomous loop is already running"}
    
    async def publish_task(self, task_id: str) -> Dict[str, Any]:
        """
        Publish a completed task by pushing its branch to remote repository.
        
        Args:
            task_id: ID of the task to publish
            
        Returns:
            Publication result with status and details
        """
        try:
            from core.task_queue.queue import get_redis_client
            import subprocess
            
            r = get_redis_client()
            
            # Get diff data from Redis
            diff_data = r.hget("task:diffs", task_id)
            if not diff_data:
                return {
                    "status": "error", 
                    "message": f"Task {task_id} not found in local storage",
                    "task_id": task_id
                }
            
            # Parse diff data to get branch name
            diff_info = json.loads(diff_data.decode())
            branch_name = diff_info.get("branch", f"task/{task_id}")
            
            # Check if tests passed before allowing publish
            tests_passed = diff_info.get("tests_passed", False)
            ready_for_publish = diff_info.get("ready_for_publish", False)
            
            if not tests_passed or not ready_for_publish:
                return {
                    "status": "error",
                    "message": f"Task {task_id} cannot be published: tests failed",
                    "task_id": task_id,
                    "tests_passed": tests_passed,
                    "error_code": 409  # Conflict - tests must pass first
                }
            
            print(f"📤 Publishing task {task_id} to remote...")
            print(f"🌿 Branch: {branch_name}")
            print(f"✅ Tests verified as passing")
            
            # Execute git push
            try:
                result = subprocess.run(
                    ["git", "push", "-u", "origin", branch_name],
                    capture_output=True,
                    text=True,
                    timeout=60  # 1 minute timeout
                )
                
                if result.returncode == 0:
                    # Mark as published
                    diff_info["published"] = True
                    diff_info["published_at"] = datetime.now().isoformat()
                    r.hset("task:diffs", task_id, json.dumps(diff_info))
                    
                    print(f"✅ Task {task_id} published successfully")
                    
                    # Clean up: remove from diff storage after successful publish
                    r.hdel("task:diffs", task_id)
                    print(f"🧹 Cleaned up diff storage for task {task_id}")
                    
                    return {
                        "status": "success",
                        "message": f"Task {task_id} published to {branch_name}",
                        "task_id": task_id,
                        "branch": branch_name,
                        "git_output": result.stdout
                    }
                else:
                    print(f"❌ Git push failed: {result.stderr}")
                    return {
                        "status": "error",
                        "message": f"Git push failed: {result.stderr}",
                        "task_id": task_id,
                        "git_error": result.stderr
                    }
                    
            except subprocess.TimeoutExpired:
                return {
                    "status": "error",
                    "message": "Git push timed out after 60 seconds",
                    "task_id": task_id
                }
                
        except Exception as e:
            print(f"❌ Failed to publish task {task_id}: {e}")
            return {
                "status": "error",
                "message": f"Publication failed: {str(e)}",
                "task_id": task_id
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get supervisor status and queue information."""
        from core.task_queue.queue import queue_length, DEVTASKS_WAITING, DEVTASKS_PROCESSING, DEVTASKS_DONE, DEVTASKS_DONE_LOCAL, DEVTASKS_FAILED
        
        return {
            "supervisor_running": self._running,
            "queues": {
                "highlevel_pending": queue_length(HIGHLEVEL_IN),
                "tasks_waiting": queue_length(DEVTASKS_WAITING),
                "tasks_processing": queue_length(DEVTASKS_PROCESSING),
                "tasks_done": queue_length(DEVTASKS_DONE),
                "tasks_done_local": queue_length(DEVTASKS_DONE_LOCAL),
                "tasks_failed": queue_length(DEVTASKS_FAILED)
            },
            "entity_status": "active" if self._running else "stopped"
        }


def register() -> Dict[str, Any]:
    """Register Supervisor entity with the framework."""
    return {
        "id": "supervisor",                    # 🔧 Technical ID for registry/API
        "name": {                             # 🏷️ Multilingual human-readable names
            "en": "Petrovich",
            "ru": "Петрович"
        },
        "class": SupervisorEntity,            # 🏗️ Implementation class
        "description": "Senior development supervisor with 30 years experience - analytical, methodical, validation-focused",
        "version": "2.0.0",
        "role": "supervisor",                 # 🎭 Functional role
        "capabilities": [
            "task_decomposition",
            "strategic_planning",
            "team_coordination",
            "validation_and_review",
            "workflow_management",
            "quality_oversight",
            "project_leadership",
            "experience_based_guidance",
            "senior_supervision"
        ],
        "team_position": "team_lead",
        "experience_years": 30,
        "personality": "phlegmatic_wise_validator",
        "direct_reports": ["developer", "qa"],   # 🔧 Using technical IDs
        "display_info": {
            "icon": "👨‍💼",
            "color": "#2563EB",
            "short_name": "Петрович"
        }
    } 