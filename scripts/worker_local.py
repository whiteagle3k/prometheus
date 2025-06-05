#!/usr/bin/env python3
"""
Local Development Worker

Processes development tasks from the supervisor queue:
1. Pops tasks from devtasks:waiting queue
2. Creates git branches for each task
3. Applies LLM-generated patches/changes
4. Runs tests and validates results
5. Pushes branches and marks tasks as done/failed
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.task_queue.queue import pop, push, DEVTASKS_WAITING, DEVTASKS_PROCESSING, DEVTASKS_DONE, DEVTASKS_DONE_LOCAL, DEVTASKS_FAILED


def run_command(cmd: str, cwd: str | None = None) -> tuple[int, str, str]:
    """Run shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out after 5 minutes"
    except Exception as e:
        return -1, "", str(e)


def git_create_branch(task_id: str) -> bool:
    """Create and checkout a new git branch for the task, handling conflicts."""
    branch_name = f"task/{task_id}"
    
    # Ensure we're on main/master
    code, _, _ = run_command("git checkout main")
    if code != 0:
        code, _, _ = run_command("git checkout master")
        if code != 0:
            print(f"❌ Failed to checkout main/master branch")
            return False
    
    # Pull latest changes
    code, _, stderr = run_command("git pull")
    if code != 0:
        print(f"⚠️  Failed to pull latest changes: {stderr}")
    
    # Check if branch already exists
    code, _, _ = run_command(f"git rev-parse --verify {branch_name}")
    
    if code == 0:
        # Branch exists - decide how to handle
        print(f"🔄 Branch {branch_name} already exists")
        
        # Check if there are uncommitted changes on that branch
        code, _, _ = run_command(f"git checkout {branch_name}")
        if code != 0:
            print(f"❌ Failed to checkout existing branch {branch_name}")
            return False
            
        # Check if branch has unpushed commits
        code, output, _ = run_command("git log --oneline @{u}..HEAD")
        has_unpushed = bool(output.strip())
        
        if has_unpushed:
            print(f"📝 Branch has unpushed commits, will amend last commit")
            return True  # Will use --amend in commit
        else:
            # Create versioned branch
            version = 2
            while True:
                versioned_branch = f"task/{task_id}-v{version}"
                code, _, _ = run_command(f"git rev-parse --verify {versioned_branch}")
                if code != 0:  # Branch doesn't exist
                    branch_name = versioned_branch
                    break
                version += 1
                if version > 10:  # Prevent infinite loop
                    print(f"❌ Too many versions for task {task_id}")
                    return False
            
            print(f"🆕 Creating versioned branch: {branch_name}")
            code, _, _ = run_command("git checkout main")
    
    # Create and checkout new branch
    code, stdout, stderr = run_command(f"git checkout -b {branch_name}")
    if code != 0:
        print(f"❌ Failed to create branch {branch_name}: {stderr}")
        return False
    
    print(f"✅ Created and checked out branch: {branch_name}")
    return True


def write_task_file(task_spec: Dict[str, Any]) -> None:
    """Write task specification to .cursor_task.json for reference."""
    task_file = PROJECT_ROOT / ".cursor_task.json"
    with open(task_file, "w") as f:
        json.dump(task_spec, f, indent=2)
    print(f"📝 Task spec written to {task_file}")


def apply_llm_patch(task_spec: Dict[str, Any]) -> bool:
    """
    Apply LLM-generated changes for the task.
    
    This is a placeholder implementation that would:
    1. Generate detailed implementation prompt from task_spec
    2. Call LLM to generate code changes
    3. Apply the changes to specified files
    4. Validate the changes
    
    For now, it's a stub that creates a simple change.
    """
    task_id = task_spec["id"]
    title = task_spec["title"]
    description = task_spec["description"]
    files = task_spec.get("files", [])
    
    print(f"🔧 Applying changes for task: {title}")
    print(f"📋 Description: {description}")
    
    # TODO: Implement actual LLM integration for code generation
    # For now, create a simple placeholder implementation
    
    # Create a task log file
    log_file = PROJECT_ROOT / f"task_{task_id}.md"
    log_content = f"""# Task Implementation Log

## Task: {title}

**ID:** {task_id}
**Created:** {task_spec.get('created_at', 'unknown')}
**Priority:** {task_spec.get('priority', 'normal')}

## Description
{description}

## Files to Modify
{chr(10).join(f"- {file}" for file in files)}

## Acceptance Criteria
{chr(10).join(f"- {criteria}" for criteria in task_spec.get('acceptance_criteria', []))}

## Implementation Status
- [x] Task received and processed
- [ ] Code changes applied
- [ ] Tests passing
- [ ] Ready for review

## Notes
This is a placeholder implementation. Actual LLM-driven code generation will be implemented later.

Generated at: {datetime.now().isoformat()}
"""
    
    with open(log_file, "w") as f:
        f.write(log_content)
    
    # Add the log file to git
    code, _, _ = run_command(f"git add {log_file}")
    if code != 0:
        print(f"⚠️  Failed to add log file to git")
        return False
    
    # Check if we should amend existing commit
    code, output, _ = run_command("git log --oneline -1")
    should_amend = code == 0 and f"Task {task_id}:" in output
    
    # Commit the placeholder
    commit_msg = f"Task {task_id}: {title}\n\n{description}"
    if should_amend:
        print(f"📝 Amending existing commit for task {task_id}")
        code, _, stderr = run_command(f'git commit --amend -m "{commit_msg}"')
    else:
        code, _, stderr = run_command(f'git commit -m "{commit_msg}"')
        
    if code != 0:
        print(f"❌ Failed to commit changes: {stderr}")
        return False
    
    commit_type = "amended" if should_amend else "created"
    print(f"✅ Placeholder implementation {commit_type} for task {task_id}")
    return True


def run_tests() -> bool:
    """Run project tests to validate changes."""
    print("🧪 Running tests...")
    
    # Run pytest
    code, stdout, stderr = run_command("poetry run pytest tests/ -x --tb=short")
    
    if code == 0:
        print("✅ All tests passed")
        return True
    else:
        print(f"❌ Tests failed:")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        return False


def save_diff_locally(task_id: str, tests_passed: bool) -> bool:
    """Save diff to Redis instead of pushing to remote."""
    branch_name = f"task/{task_id}"
    
    try:
        # Get diff from last commit
        code, diff_output, stderr = run_command("git diff HEAD~1")
        if code != 0:
            print(f"❌ Failed to get diff: {stderr}")
            return False
        
        # Save diff to Redis for later review
        from core.task_queue.queue import get_redis_client
        r = get_redis_client()
        
        # Store diff data with test results
        diff_data = {
            "branch": branch_name,
            "diff": diff_output,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "tests_passed": tests_passed,
            "ready_for_publish": tests_passed
        }
        
        # Save to Redis hash for easy retrieval
        r.hset("task:diffs", task_id, json.dumps(diff_data))
        
        print(f"✅ Diff saved for task {task_id} (no remote push)")
        print(f"📝 Branch: {branch_name}")
        print(f"📊 Diff size: {len(diff_output)} chars")
        print(f"🧪 Tests: {'✅ PASSED' if tests_passed else '❌ FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to save diff for {task_id}: {e}")
        return False


def process_task(task_spec: Dict[str, Any]) -> bool:
    """Process a single development task."""
    task_id = task_spec["id"]
    title = task_spec["title"]
    
    print(f"\n{'='*60}")
    print(f"🔨 Processing task {task_id}: {title}")
    print(f"{'='*60}")
    
    try:
        # Mark task as processing
        task_spec["status"] = "processing"
        task_spec["started_at"] = datetime.now().isoformat()
        push(DEVTASKS_PROCESSING, task_spec)
        
        # Create git branch
        if not git_create_branch(task_id):
            return False
        
        # Write task specification file
        write_task_file(task_spec)
        
        # Apply LLM-generated changes
        if not apply_llm_patch(task_spec):
            return False
        
        # Run tests
        tests_passed = run_tests()
        if not tests_passed:
            print("❌ Tests failed - saving diff but marking as not ready for publish")
        
        # Save diff locally (always save, but mark test status)
        if not save_diff_locally(task_id, tests_passed):
            return False
        
        print(f"✅ Task {task_id} completed {'with passing tests' if tests_passed else 'but tests failed'}")
        return tests_passed  # Return test status for final task marking
        
    except Exception as e:
        print(f"❌ Task {task_id} failed with exception: {e}")
        return False


def main():
    """Main worker loop."""
    print("🚀 Local Development Worker starting...")
    print(f"📁 Working directory: {PROJECT_ROOT}")
    
    # Verify we're in a git repository
    code, _, _ = run_command("git status")
    if code != 0:
        print("❌ Not in a git repository. Exiting.")
        sys.exit(1)
    
    print("🔄 Waiting for tasks from supervisor...")
    
    while True:
        try:
            # Wait for tasks (blocking pop)
            print("⏳ Waiting for next task...")
            task_spec = pop(DEVTASKS_WAITING)
            
            # Process the task
            success = process_task(task_spec)
            
            # Update task status
            task_spec["completed_at"] = datetime.now().isoformat()
            
            if success:
                task_spec["status"] = "done_local"
                push(DEVTASKS_DONE_LOCAL, task_spec)
                print(f"✅ Task {task_spec['id']} marked as DONE_LOCAL (ready for review)")
            else:
                task_spec["status"] = "failed"
                push(DEVTASKS_FAILED, task_spec)
                print(f"❌ Task {task_spec['id']} marked as FAILED")
            
        except KeyboardInterrupt:
            print("\n🛑 Worker stopped by user")
            break
        except Exception as e:
            print(f"❌ Worker error: {e}")
            time.sleep(5)  # Wait before retrying


if __name__ == "__main__":
    main() 