#!/usr/bin/env python3
"""
OpenClaw Subagent Controller
Manages OpenClaw agents as subagents for development tasks
"""

import subprocess
import json
import os
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class OpenClawTaskType(Enum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    BUG_FIX = "bug_fix"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    FEATURE_IMPL = "feature_impl"
    PLANNING = "planning"


@dataclass
class OpenClawTask:
    id: str
    task_type: OpenClawTaskType
    description: str
    prompt: str
    context: Dict[str, Any] = None
    timeout: int = 300  # 5 minutes default
    max_retries: int = 2
    priority: int = 1
    model: str = "openclaw"  # Default model
    created_at: str = None
    started_at: str = None
    completed_at: str = None
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class OpenClawController:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.active_tasks: Dict[str, OpenClawTask] = {}
        self.completed_tasks: List[OpenClawTask] = []
        self.task_counter = 0
        self.timeout_threads: Dict[str, threading.Timer] = {}  # Track timeout timers

        # Verify OpenClaw CLI is available
        self._verify_openclaw()

    def _verify_openclaw(self):
        """Verify OpenClaw CLI is installed and accessible"""
        try:
            result = subprocess.run(['openclaw', '--version'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✅ OpenClaw CLI verified: {result.stdout.strip()}")
            else:
                # Try alternative check
                result = subprocess.run(['which', 'openclaw'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    print(f"✅ OpenClaw CLI found at: {result.stdout.strip()}")
                else:
                    print("⚠️  OpenClaw CLI not readily available, will attempt to use anyway")
        except Exception as e:
            print(f"⚠️  OpenClaw CLI verification issue: {e}")
            print("   Will attempt to use OpenClaw CLI anyway")

    def _setup_timeout(self, task_id: str, timeout_seconds: int, callback):
        """Setup a timeout using threading.Timer (works in any thread)"""
        def timeout_func():
            callback()

        timer = threading.Timer(timeout_seconds, timeout_func)
        timer.daemon = True  # Daemon thread won't block program exit
        self.timeout_threads[task_id] = timer
        timer.start()

    def _cancel_timeout(self, task_id: str):
        """Cancel a pending timeout"""
        if task_id in self.timeout_threads:
            self.timeout_threads[task_id].cancel()
            del self.timeout_threads[task_id]

    def create_task(self, task_type: OpenClawTaskType, description: str,
                   prompt: str, context: Dict = None, priority: int = 1,
                   timeout: int = 300, model: str = None) -> str:
        """Create a new OpenClaw task"""
        self.task_counter += 1
        task_id = f"openclaw-{self.task_counter:04d}"

        task = OpenClawTask(
            id=task_id,
            task_type=task_type,
            description=description,
            prompt=prompt,
            context=context or {},
            priority=priority,
            timeout=timeout,
            model=model or "openclaw"
        )

        self.active_tasks[task_id] = task
        print(f"📝 Created OpenClaw task {task_id}: {description}")
        return task_id

    def execute_task(self, task_id: str) -> bool:
        """Execute an OpenClaw task"""
        if task_id not in self.active_tasks:
            print(f"❌ Task {task_id} not found")
            return False

        task = self.active_tasks[task_id]
        if task.status != "pending":
            print(f"⚠️  Task {task_id} is not pending (status: {task.status})")
            return False

        print(f"🚀 Executing OpenClaw task {task_id}: {task.description}")
        task.status = "running"
        task.started_at = datetime.now().isoformat()

        # Set up timeout handling using threading (works in any thread)
        def timeout_callback():
            if task_id in self.active_tasks and self.active_tasks[task_id].status == "running":
                task = self.active_tasks[task_id]
                task.status = "failed"
                task.error = f"Task timed out after {task.timeout} seconds"
                task.completed_at = datetime.now().isoformat()
                print(f"⏰ OpenClaw task {task_id} timed out")
                self._move_to_completed(task_id)

        self._setup_timeout(task_id, task.timeout, timeout_callback)

        try:
            # Build the OpenClaw command to run an agent turn via the Gateway
            # Based on help: 'openclaw agent' requires -m/--message for message body
            cmd = [
                'openclaw',
                'agent',
                '-m', task.prompt,
                '--timeout', str(task.timeout)
            ]

            # Add context if provided
            if task.context:
                context_str = json.dumps(task.context, indent=2)
                # Add context as additional instructions to the prompt
                enhanced_prompt = task.prompt + f"\n\nContext:\n{context_str}"
                cmd[2] = enhanced_prompt  # Replace the message argument (after -m)

            print(f"   Executing: openclaw agent -m \"{task.prompt[:50]}...\" --timeout {task.timeout}")

            # Execute the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.workspace_root
            )

            # Cancel the timeout since we completed normally
            self._cancel_timeout(task_id)

            task.completed_at = datetime.now().isoformat()

            if result.returncode == 0:
                task.status = "completed"
                task.result = {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
                print(f"✅ OpenClaw task {task_id} completed successfully")
                self._move_to_completed(task_id)
                return True
            else:
                # Check for common issues
                error_output = result.stderr.strip()
                if "rate limit" in error_output.lower() or "429" in error_output:
                    task.status = "failed"
                    task.error = "Rate limit exceeded"
                elif "required option '-m, --message <text>' not specified" in error_output:
                    task.status = "failed"
                    task.error = "Message parameter not properly passed to OpenClaw CLI"
                elif "not found" in error_output.lower() or "command not found" in error_output.lower():
                    task.status = "failed"
                    task.error = "OpenClaw CLI not found or not properly installed"
                else:
                    task.status = "failed"
                    task.error = error_output

                task.result = {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
                print(f"❌ OpenClaw task {task_id} failed: {task.error}")
                return False

        except Exception as e:
            # Cancel the timeout on exception
            self._cancel_timeout(task_id)

            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.now().isoformat()
            print(f"💥 OpenClaw task {task_id} error: {e}")
            return False

    def _move_to_completed(self, task_id: str):
        """Move a task from active to completed"""
        if task_id in self.active_tasks:
            task = self.active_tasks.pop(task_id)
            self.completed_tasks.append(task)
            # Ensure timeout is cleaned up
            self._cancel_timeout(task_id)

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get the status of a task"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            return asdict(task)
        # Check completed tasks
        for task in self.completed_tasks:
            if task.id == task_id:
                return asdict(task)
        return None

    def list_active_tasks(self) -> List[Dict]:
        """List all active tasks"""
        return [asdict(task) for task in self.active_tasks.values()]

    def list_completed_tasks(self) -> List[Dict]:
        """List all completed tasks"""
        return [asdict(task) for task in self.completed_tasks]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            if task.status == "pending":
                task.status = "cancelled"
                task.completed_at = datetime.now().isoformat()
                self._move_to_completed(task_id)
                print(f"🛑 OpenClaw task {task_id} cancelled")
                return True
        return False


def main():
    """Demo the OpenClaw controller"""
    controller = OpenClawController(os.getcwd())

    # Create a sample task
    task_id = controller.create_task(
        task_type=OpenClawTaskType.RESEARCH,
        description="Research best practices for autonomous AI agent development",
        prompt="Research and document best practices for creating autonomous AI agent systems that can operate continuously with minimal human intervention. Focus on error handling, state persistence, and self-healing mechanisms.",
        context={
            "purpose": "Improve autonomous development system",
            "focus": "error handling and state persistence"
        },
        priority=2
    )

    print(f"Created task: {task_id}")

    # Execute the task
    success = controller.execute_task(task_id)

    if success:
        print("Task completed successfully!")
    else:
        print("Task failed or was cancelled.")

    # Show status
    status = controller.get_task_status(task_id)
    if status:
        print(f"Task status: {status['status']}")

if __name__ == "__main__":
    main()