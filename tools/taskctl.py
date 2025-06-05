#!/usr/bin/env python3
"""
TaskCtl - CLI utility for managing development tasks

Commands:
- list: Show all tasks with their status
- diff <task_id>: Show diff for a specific task
- publish <task_id>: Publish a task to remote repository
- status: Show supervisor and queue status
"""

import json
import sys
import requests
from pathlib import Path
from typing import Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

API_BASE = "http://localhost:8000"

def make_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make HTTP request to the API."""
    url = f"{API_BASE}{endpoint}"
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {e}")
        sys.exit(1)

def cmd_status():
    """Show supervisor and queue status."""
    print("📊 Supervisor Status")
    print("=" * 50)
    
    status = make_request("GET", "/v1/supervisor/status")
    
    supervisor = status.get("supervisor", {})
    queues = status.get("queues", {})
    
    print(f"Supervisor: {supervisor.get('status', 'unknown')}")
    print(f"Running: {'✅' if supervisor.get('running', False) else '❌'}")
    print()
    print("📋 Queue Status:")
    print(f"  High-level pending: {queues.get('highlevel_pending', 0)}")
    print(f"  Tasks waiting: {queues.get('tasks_waiting', 0)}")
    print(f"  Tasks processing: {queues.get('tasks_processing', 0)}")
    print(f"  Tasks done (local): {queues.get('tasks_done_local', 0)} 🔍")
    print(f"  Tasks done (remote): {queues.get('tasks_done', 0)}")
    print(f"  Tasks failed: {queues.get('tasks_failed', 0)}")

def cmd_list():
    """List all tasks."""
    try:
        import redis
        import os
        
        # Connect to Redis directly
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        
        # Get all tasks from done_local queue
        done_local_tasks = []
        queue_length = r.llen("devtasks:done_local")
        
        for i in range(queue_length):
            task_data = r.lindex("devtasks:done_local", i)
            if task_data:
                task = json.loads(task_data.decode())
                done_local_tasks.append(task)
        
        # Get diff info for each task
        diff_keys = r.hkeys("task:diffs")
        diff_info = {}
        
        for key in diff_keys:
            task_id = key.decode()
            diff_data = r.hget("task:diffs", task_id)
            if diff_data:
                diff_info[task_id] = json.loads(diff_data.decode())
        
        print("📋 Local Tasks Ready for Review")
        print("=" * 60)
        
        if not done_local_tasks:
            print("No tasks ready for review.")
            return
        
        for task in done_local_tasks:
            task_id = task.get("id", "unknown")
            title = task.get("title", "No title")
            created = task.get("created_at", "")
            completed = task.get("completed_at", "")
            
            diff = diff_info.get(task_id, {})
            branch = diff.get("branch", "unknown")
            published = diff.get("published", False)
            tests_passed = diff.get("tests_passed", False)
            ready_for_publish = diff.get("ready_for_publish", False)
            
            # Status icons based on state
            if published:
                status_icon = "📤"
            elif ready_for_publish and tests_passed:
                status_icon = "✅"
            elif not tests_passed:
                status_icon = "❌"
            else:
                status_icon = "🔍"
            
            print(f"{status_icon} {task_id}")
            print(f"   Title: {title}")
            print(f"   Branch: {branch}")
            print(f"   Created: {created[:19] if created else 'unknown'}")
            print(f"   Completed: {completed[:19] if completed else 'unknown'}")
            print(f"   Tests: {'✅ PASSED' if tests_passed else '❌ FAILED'}")
            print(f"   Ready: {'✅ YES' if ready_for_publish else '❌ NO'}")
            print(f"   Published: {'✅' if published else '❌'}")
            print()
            
    except Exception as e:
        print(f"❌ Failed to list tasks: {e}")
        sys.exit(1)

def cmd_diff(task_id: str):
    """Show diff for a specific task."""
    print(f"🔍 Diff for Task: {task_id}")
    print("=" * 60)
    
    try:
        diff_data = make_request("GET", f"/v1/task/{task_id}/diff")
        
        if not diff_data.get("available", False):
            print(f"❌ No diff available for task {task_id}")
            return
        
        print(f"Branch: {diff_data.get('branch', 'unknown')}")
        print(f"Timestamp: {diff_data.get('timestamp', 'unknown')}")
        print()
        print("Changes:")
        print("-" * 40)
        
        diff_content = diff_data.get("diff", "")
        if diff_content:
            print(diff_content)
        else:
            print("No changes in diff.")
            
    except Exception as e:
        print(f"❌ Failed to get diff: {e}")
        sys.exit(1)

def cmd_publish(task_id: str = None, publish_all: bool = False):
    """Publish a task to remote repository."""
    if publish_all:
        # Publish all tasks with passed tests
        print("📤 Publishing All Passed Tasks")
        print("=" * 50)
        
        try:
            import redis
            import os
            
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url)
            
            # Get all diff keys
            diff_keys = r.hkeys("task:diffs")
            ready_tasks = []
            
            for key in diff_keys:
                task_id_bytes = key.decode()
                diff_data = r.hget("task:diffs", task_id_bytes)
                if diff_data:
                    diff_info = json.loads(diff_data.decode())
                    if diff_info.get("ready_for_publish", False) and diff_info.get("tests_passed", False):
                        ready_tasks.append(task_id_bytes)
            
            if not ready_tasks:
                print("No tasks ready for publishing.")
                return
            
            print(f"Found {len(ready_tasks)} tasks ready for publishing:")
            for tid in ready_tasks:
                print(f"  - {tid}")
            
            # Publish each ready task
            success_count = 0
            for tid in ready_tasks:
                try:
                    result = make_request("POST", f"/v1/task/{tid}/publish")
                    if result.get("status") == "success":
                        print(f"✅ Published {tid}")
                        success_count += 1
                    else:
                        print(f"❌ Failed to publish {tid}: {result.get('message', 'Unknown error')}")
                except Exception as e:
                    print(f"❌ Error publishing {tid}: {e}")
            
            print(f"\n📊 Published {success_count}/{len(ready_tasks)} tasks successfully")
            
        except Exception as e:
            print(f"❌ Failed to publish all tasks: {e}")
            sys.exit(1)
            
    else:
        # Publish single task
        print(f"📤 Publishing Task: {task_id}")
        print("=" * 50)
        
        try:
            result = make_request("POST", f"/v1/task/{task_id}/publish")
            
            status = result.get("status", "unknown")
            message = result.get("message", "")
            branch = result.get("branch", "")
            
            if status == "success":
                print(f"✅ {message}")
                print(f"🌿 Branch: {branch}")
            elif status == "error" and result.get("error_code") == 409:
                print(f"⚠️  {message}")
                print("🧪 Tests must pass before publishing")
            else:
                print(f"❌ {message}")
                
        except Exception as e:
            print(f"❌ Failed to publish task: {e}")
            sys.exit(1)

def cmd_submit(brief: str):
    """Submit a new high-level task."""
    print(f"📝 Submitting Task: {brief}")
    print("=" * 50)
    
    try:
        data = {
            "brief": brief,
            "user_id": "taskctl",
            "priority": "normal"
        }
        
        result = make_request("POST", "/v1/task", json=data)
        
        task_id = result.get("task_id", "unknown")
        status = result.get("status", "unknown")
        
        print(f"✅ Task submitted successfully")
        print(f"🔗 Task ID: {task_id}")
        print(f"📊 Status: {status}")
        
    except Exception as e:
        print(f"❌ Failed to submit task: {e}")
        sys.exit(1)

def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("TaskCtl - Development Task Management")
        print()
        print("Usage:")
        print("  ./tools/taskctl.py status            - Show supervisor status")
        print("  ./tools/taskctl.py list              - List all local tasks")
        print("  ./tools/taskctl.py diff <task_id>    - Show task diff")
        print("  ./tools/taskctl.py publish <task_id> - Publish specific task")
        print("  ./tools/taskctl.py publish --all-passed - Publish all ready tasks")
        print("  ./tools/taskctl.py submit '<brief>'  - Submit new task")
        print()
        print("Task Status Icons:")
        print("  ✅ Ready for publish (tests passed)")
        print("  ❌ Tests failed")
        print("  🔍 Processing or needs review")
        print("  📤 Already published")
        print()
        print("Examples:")
        print("  ./tools/taskctl.py list")
        print("  ./tools/taskctl.py diff 4d49d981")
        print("  ./tools/taskctl.py publish 4d49d981")
        print("  ./tools/taskctl.py publish --all-passed")
        print("  ./tools/taskctl.py submit 'add logging to worker'")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "status":
        cmd_status()
    elif command == "list":
        cmd_list()
    elif command == "diff":
        if len(sys.argv) < 3:
            print("❌ Usage: taskctl diff <task_id>")
            sys.exit(1)
        cmd_diff(sys.argv[2])
    elif command == "publish":
        if len(sys.argv) >= 3 and sys.argv[2] == "--all-passed":
            cmd_publish(publish_all=True)
        elif len(sys.argv) >= 3:
            cmd_publish(sys.argv[2])
        else:
            print("❌ Usage: taskctl publish <task_id> or taskctl publish --all-passed")
            sys.exit(1)
    elif command == "submit":
        if len(sys.argv) < 3:
            print("❌ Usage: taskctl submit '<brief>'")
            sys.exit(1)
        cmd_submit(sys.argv[2])
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main() 