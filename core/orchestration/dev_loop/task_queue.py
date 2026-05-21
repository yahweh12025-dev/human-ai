#!/usr/bin/env python3
"""
Task Queue Manager for Autonomous Development Loop
Parses roadmap, todo lists, and outcome logs to extract actionable tasks
"""
import json
import re
import os
import fcntl
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

@dataclass
class DevelopmentTask:
    id: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    source: str  # roadmap, todo, outcome_log, etc.
    created_at: str
    updated_at: str
    dependencies: List[str] = None
    estimated_effort: str = ""  # e.g., "2h", "1d"
    actual_effort: str = ""
    notes: str = ""
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
    
    def to_dict(self):
        """Convert to dictionary with serializable values"""
        data = asdict(self)
        data['priority'] = self.priority.name  # Convert enum to string
        data['status'] = self.status.name      # Convert enum to string
        return data

class TaskQueueManager:
    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.tasks: List[DevelopmentTask] = []
        self.task_counter = 0
        
    def parse_todo_json(self) -> List[DevelopmentTask]:
        """Parse infrastructure/configs/todo.json"""
        tasks = []
        todo_path = os.path.join(self.repo_root, "infrastructure", "configs", "todo.json")
        
        try:
            with open(todo_path, 'r') as f:
                data = json.load(f)
            
            # Parse pending tasks
            for item in data.get("pending", []):
                task_id = item.get("id", f"todo-{self.task_counter}")
                self.task_counter += 1
                
                # Determine priority based on ID or content
                priority = TaskPriority.MEDIUM
                if "security" in item["id"].lower() or "audit" in item["id"].lower():
                    priority = TaskPriority.HIGH
                elif "memory" in item["id"].lower() or "vector" in item["id"].lower():
                    priority = TaskPriority.HIGH
                
                task = DevelopmentTask(
                    id=task_id,
                    title=item["content"][:100] + ("..." if len(item["content"]) > 100 else ""),
                    description=item["content"],
                    priority=priority,
                    status=TaskStatus.PENDING,
                    source="todo.json",
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat()
                )
                tasks.append(task)
                
        except Exception as e:
            print(f"Error parsing todo.json: {e}")
            
        return tasks
    
    def parse_unified_plan(self) -> List[DevelopmentTask]:
        """Parse docs/unified_plan.md for in-progress and upcoming tasks"""
        tasks = []
        plan_path = os.path.join(self.repo_root, "docs", "unified_plan.md")
        
        try:
            with open(plan_path, 'r') as f:
                content = f.read()
            
            # Extract items from Phase 3 (IN PROGRESS) and Phase 5 (UPCOMING)
            # Look for unchecked checkboxes
            pattern = r'- \[ \] (.+?)(?:\n|$)'
            matches = re.findall(pattern, content)
            
            for i, match in enumerate(matches):
                task_id = f"plan-{self.task_counter}"
                self.task_counter += 1
                
                # Determine priority based on phase and keywords
                priority = TaskPriority.MEDIUM
                if any(keyword in match.lower() for keyword in ["security", "audit", "critical", "fix"]):
                    priority = TaskPriority.HIGH
                elif any(keyword in match.lower() for keyword in ["telegram", "bot", "integration"]):
                    priority = TaskPriority.MEDIUM
                
                task = DevelopmentTask(
                    id=task_id,
                    title=match[:100] + ("..." if len(match) > 100 else ""),
                    description=match,
                    priority=priority,
                    status=TaskStatus.PENDING,
                    source="unified_plan.md",
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat()
                )
                tasks.append(task)
                
        except Exception as e:
            print(f"Error parsing unified_plan.md: {e}")
            
        return tasks
    
    def parse_outcome_log(self) -> List[DevelopmentTask]:
        """Parse outcome_log.md for failed cycles and issues to fix"""
        tasks = []
        log_path = os.path.join(self.repo_root, "docs", "outcome_log.md")
        
        try:
            with open(log_path, 'r') as f:
                content = f.read()
            
            # Look for failed test cycles and errors
            if "Test cycle: FAILED" in content:
                # Extract failure reasons
                failure_pattern = r'Test cycle: FAILED - (.+?)(?:\n|$)'
                failures = re.findall(failure_pattern, content)
                
                for i, failure in enumerate(failures[-5:]):  # Last 5 failures
                    task_id = f"outcome-{self.task_counter}"
                    self.task_counter += 1
                    
                    task = DevelopmentTask(
                        id=task_id,
                        title=f"Fix: {failure[:80]}" + ("..." if len(failure) > 80 else ""),
                        description=f"Resolve failure from outcome log: {failure}",
                        priority=TaskPriority.HIGH,  # Failures are high priority
                        status=TaskStatus.PENDING,
                        source="outcome_log.md",
                        created_at=datetime.now().isoformat(),
                        updated_at=datetime.now().isoformat()
                    )
                    tasks.append(task)
                    
        except Exception as e:
            print(f"Error parsing outcome_log.md: {e}")
            
        return tasks
    
    def load_all_tasks(self) -> List[DevelopmentTask]:
        """Load tasks from all sources"""
        self.tasks = []
        self.tasks.extend(self.parse_todo_json())
        self.tasks.extend(self.parse_unified_plan())
        self.tasks.extend(self.parse_outcome_log())
        
        # Remove duplicates based on description similarity
        unique_tasks = []
        seen_descriptions = set()
        
        for task in self.tasks:
            # Simple deduplication based on first 50 chars of description
            desc_key = task.description[:50].lower()
            if desc_key not in seen_descriptions:
                seen_descriptions.add(desc_key)
                unique_tasks.append(task)
        
        self.tasks = unique_tasks
        return self.tasks
    
    def get_next_tasks(self, count: int = 5) -> List[DevelopmentTask]:
        """Get the next highest priority tasks"""
        # Sort by priority (highest first) then by creation date
        sorted_tasks = sorted(
            self.tasks, 
            key=lambda t: (-t.priority.value, t.created_at)
        )
        
        # Filter for pending tasks only
        pending_tasks = [t for t in sorted_tasks if t.status == TaskStatus.PENDING]
        
        return pending_tasks[:count]
    
    def update_task_status(self, task_id: str, status: TaskStatus, notes: str = ""):
        """Update a task's status"""
        for task in self.tasks:
            if task.id == task_id:
                task.status = status
                task.updated_at = datetime.now().isoformat()
                if notes:
                    task.notes = notes
                break
    
    def save_queue(self, filepath: str):
        """Save the task queue to a JSON file"""
        queue_data = {
            "tasks": [task.to_dict() for task in self.tasks],
            "last_updated": datetime.now().isoformat(),
            "total_tasks": len(self.tasks),
            "pending_count": len([t for t in self.tasks if t.status == TaskStatus.PENDING]),
            "completed_count": len([t for t in self.tasks if t.status == TaskStatus.COMPLETED])
        }
        
        with open(filepath, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(queue_data, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    
    def load_queue(self, filepath: str):
        """Load the task queue from a JSON file"""
        try:
            with open(filepath, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            self.tasks = []
            for task_data in data.get("tasks", []):
                # Convert string values back to enums
                task_data["priority"] = TaskPriority[task_data["priority"]]
                task_data["status"] = TaskStatus[task_data["status"]]
                task = DevelopmentTask(**task_data)
                self.tasks.append(task)
                
        except Exception as e:
            print(f"Error loading task queue: {e}")

def main():
    """Demo the task queue manager"""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    manager = TaskQueueManager(repo_root)
    tasks = manager.load_all_tasks()
    
    print(f"📋 Loaded {len(tasks)} development tasks")
    print("=" * 60)
    
    # Show next 5 tasks
    next_tasks = manager.get_next_tasks(5)
    for i, task in enumerate(next_tasks, 1):
        print(f"{i}. [{task.priority.name}] {task.title}")
        print(f"   ID: {task.id}")
        print(f"   Source: {task.source}")
        print(f"   Status: {task.status.value}")
        print()
    
    # Save the queue
    manager.save_queue(os.path.join(repo_root, "autonomous_dev", "task_queue.json"))
    print(f"💾 Task queue saved to autonomous_dev/task_queue.json")

if __name__ == "__main__":
    main()