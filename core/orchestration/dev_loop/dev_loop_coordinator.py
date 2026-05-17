#!/usr/bin/env python3
"""
Autonomous Development Loop Coordinator
Orchestrates task execution using OpenClaw as subagent
"""
import json
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import asdict

from task_queue import TaskQueueManager, DevelopmentTask, TaskPriority, TaskStatus
from openclaw_controller import OpenClawController, OpenClawTask, OpenClawTaskType

class AutonomousDevLoop:
    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.dev_dir = os.path.join(repo_root, "autonomous_dev")
        
        # Initialize components
        self.task_queue = TaskQueueManager(repo_root)
        self.openclaw_controller = OpenClawController(repo_root)
        
        # Loop control
        self.running = False
        self.loop_thread = None
        self.check_interval = 30  # seconds between loop iterations
        
        # Statistics
        self.stats = {
            "tasks_processed": 0,
            "openclaw_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "start_time": None,
            "last_activity": None
        }
        
        # Load existing task queue
        self._load_state()
    
    def _load_state(self):
        """Load saved state from disk"""
        # Load task queue
        queue_file = os.path.join(self.dev_dir, "task_queue.json")
        if os.path.exists(queue_file):
            self.task_queue.load_queue(queue_file)
            print(f"📂 Loaded task queue from {queue_file}")
        
        # Load stats if available
        stats_file = os.path.join(self.dev_dir, "dev_loop_stats.json")
        if os.path.exists(stats_file):
            try:
                with open(stats_file, 'r') as f:
                    self.stats.update(json.load(f))
                print(f"📊 Loaded stats from {stats_file}")
            except Exception as e:
                print(f"⚠️  Could not load stats: {e}")
    
    def _save_state(self):
        """Save current state to disk"""
        # Save task queue
        queue_file = os.path.join(self.dev_dir, "task_queue.json")
        self.task_queue.save_queue(queue_file)
        
        # Save stats
        stats_file = os.path.join(self.dev_dir, "dev_loop_stats.json")
        self.stats["last_activity"] = datetime.now().isoformat()
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def _assign_task_to_controller(self, task: DevelopmentTask) -> tuple:
        """Determine which controller should handle a task and create appropriate sub-task
        Now only uses OpenClaw for all tasks.
        """
        # Determine OpenClaw task type based on description/title
        desc_lower = task.description.lower()
        title_lower = task.title.lower()
        
        if "research" in desc_lower or "research" in title_lower:
            task_type = OpenClawTaskType.RESEARCH
        elif "review" in desc_lower or "review" in title_lower:
            task_type = OpenClawTaskType.CODE_REVIEW
        elif "fix" in desc_lower or "bug" in desc_lower or "fix" in title_lower or "bug" in title_lower:
            task_type = OpenClawTaskType.BUG_FIX
        elif "document" in desc_lower or "document" in title_lower:
            task_type = OpenClawTaskType.DOCUMENTATION
        elif "test" in desc_lower or "test" in title_lower:
            task_type = OpenClawTaskType.TESTING
        else:
            task_type = OpenClawTaskType.FEATURE_IMPL
        
        openclaw_task = self.openclaw_controller.create_task(
            task_type=task_type,
            description=task.description,
            prompt=f"""Please work on the following development task:

Task ID: {task.id}
Description: {task.description}

Please provide a clear, actionable solution. If coding is required, provide working code with comments. If analysis is required, provide detailed findings and recommendations.""",
            context={
                "task_id": task.id,
                "source": task.source,
                "repo_root": self.repo_root,
                "priority": task.priority.name
            },
            priority=task.priority.value
        )
        return ("openclaw", openclaw_task)
    
    def _process_completed_task(self, controller_name: str, task_id: str, original_task: DevelopmentTask):
        """Handle completion of a sub-task"""
        # Get the result from the OpenClaw controller
        result = self.openclaw_controller.get_task_status(task_id)
        controller_stats = "openclaw_tasks"
        
        if result and result["status"] == "completed":
            # Mark original task as completed
            self.task_queue.update_task_status(
                original_task.id, 
                TaskStatus.COMPLETED, 
                f"Completed via {controller_name} task {task_id}"
            )
            
            # Update stats
            self.stats["successful_tasks"] += 1
            self.stats[controller_stats] += 1
            print(f"✅ Task {original_task.id} completed successfully via {controller_name}")
        else:
            # Mark as failed
            error_msg = result.get("error", "Unknown error") if result else "No result"
            self.task_queue.update_task_status(
                original_task.id, 
                TaskStatus.CANCELLED, 
                f"Failed via {controller_name}: {error_msg}"
            )
            
            # Update stats
            self.stats["failed_tasks"] += 1
            print(f"❌ Task {original_task.id} failed via {controller_name}: {error_msg}")
        
        self.stats["tasks_processed"] += 1
    
    def _development_loop_iteration(self):
        """Single iteration of the development loop"""
        print(f"\n🔄 Development loop iteration - {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 50)
        
        # Load latest task queue
        self.task_queue.load_queue(os.path.join(self.dev_dir, "task_queue.json"))
        
        # Get next pending tasks
        pending_tasks = self.task_queue.get_next_tasks(count=3)
        
        if not pending_tasks:
            print("📭 No pending tasks found")
            return
        
        print(f"📋 Found {len(pending_tasks)} pending tasks")
        
        # Process each task
        for task in pending_tasks:
            print(f"\n🎯 Processing task: {task.id}")
            print(f"   Title: {task.title}")
            print(f"   Priority: {task.priority.name}")
            print(f"   Source: {task.source}")
            
            # Mark task as in progress
            self.task_queue.update_task_status(task.id, TaskStatus.IN_PROGRESS)
            
            # Assign to OpenClaw controller
            controller_name, sub_task_id = self._assign_task_to_controller(task)
            print(f"   🤖 Assigned to {controller_name.upper()} as task {sub_task_id}")
            
            # Execute the sub-task
            success = self.openclaw_controller.execute_task(sub_task_id)
            
            # Poll for completion with timeout
            max_wait_time = 300  # 5 minutes
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                result = self.openclaw_controller.get_task_status(sub_task_id)
                
                if result and result["status"] == "completed":
                    self._process_completed_task(controller_name, sub_task_id, task)
                    break
                elif result and result["status"] == "failed":
                    # Handle failure
                    error_msg = result.get("error", "Unknown error")
                    self.task_queue.update_task_status(
                        task.id, 
                        TaskStatus.CANCELLED, 
                        f"Failed via {controller_name}: {error_msg}"
                    )
                    self.stats["failed_tasks"] += 1
                    print(f"❌ Task {task.id} failed via {controller_name}: {error_msg}")
                    break
                else:
                    # Still running, wait and check again
                    time.sleep(5)
            else:
                # Timeout reached
                print(f"   ⏰ Timeout waiting for task {sub_task_id} to complete. Resetting to PENDING.")
                # Reset task to PENDING so it can be retried
                self.task_queue.update_task_status(task.id, TaskStatus.PENDING, f"Timeout on sub-task {sub_task_id}, resetting to PENDING")
        
        # Save state after iteration
        self._save_state()
        
        # Print current stats
        print(f"\n📊 Loop Stats: {self.stats['tasks_processed']} processed, "
              f"{self.stats['successful_tasks']} successful, {self.stats['failed_tasks']} failed")
    
    def start_loop(self):
        """Start the autonomous development loop in a background thread"""
        if self.running:
            print("⚠️  Autonomous loop is already running")
            return
        
        self.running = True
        self.stats["start_time"] = datetime.now().isoformat()
        self.loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.loop_thread.start()
        print("🚀 Autonomous development loop started")
    
    def stop_loop(self):
        """Stop the autonomous development loop"""
        if not self.running:
            print("⚠️  Autonomous loop is not running")
            return
        
        self.running = False
        if self.loop_thread:
            self.loop_thread.join(timeout=10)
        print("🛑 Autonomous development loop stopped")
        self._save_state()
    
    def _run_loop(self):
        """Main loop execution"""
        print("🔄 Autonomous development loop running...")
        while self.running:
            try:
                self._development_loop_iteration()
                
                # Wait for next iteration
                for i in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                print(f"💥 Error in development loop: {e}")
                time.sleep(10)  # Wait before retrying after error
        
        print("🔄 Autonomous development loop terminated")

def main():
    """Main entry point for the autonomous development loop"""
    import sys
    
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print("🤖 Autonomous Development Loop System")
    print("=" * 50)
    print(f"Repository root: {repo_root}")
    print(f"Development directory: {os.path.join(repo_root, 'autonomous_dev')}")
    
    # Initialize the loop system
    dev_loop = AutonomousDevLoop(repo_root)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Run a single iteration
        print("\n🔄 Running single development loop iteration...")
        dev_loop._development_loop_iteration()
        print("\n✅ Single iteration complete")
    else:
        # Start continuous loop
        try:
            dev_loop.start_loop()
            print("\n💡 Press Ctrl+C to stop the autonomous loop")
            
            # Keep main thread alive
            while dev_loop.running:
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n🛑 Received interrupt signal...")
        finally:
            dev_loop.stop_loop()
            print("\n👋 Autonomous development loop shut down")

if __name__ == "__main__":
    main()