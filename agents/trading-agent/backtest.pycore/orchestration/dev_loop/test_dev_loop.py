#!/usr/bin/env python3
"""
Comprehensive Test Suite for Dev Loop Components
Tests task_queue and coordinator reliability under load
"""

import unittest
import sys
import os
import time
import threading
import json
import tempfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from task_queue import TaskQueueManager, DevelopmentTask, TaskPriority, TaskStatus
from openclaw_controller import OpenClawController, OpenClawTask, OpenClawTaskType


class TestDevelopmentTask(unittest.TestCase):
    """Test the DevelopmentTask dataclass"""
    
    def test_task_creation(self):
        """Test basic task creation"""
        task = DevelopmentTask(
            id="test-001",
            title="Test Task",
            description="A test task",
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING,
            source="test",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        self.assertEqual(task.id, "test-001")
        self.assertEqual(task.priority, TaskPriority.HIGH)
        self.assertEqual(task.status, TaskStatus.PENDING)
    
    def test_task_to_dict(self):
        """Test task serialization"""
        task = DevelopmentTask(
            id="test-002",
            title="Serialize Test",
            description="Testing serialization",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.IN_PROGRESS,
            source="test",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00"
        )
        task_dict = task.to_dict()
        self.assertEqual(task_dict['id'], "test-002")
        self.assertEqual(task_dict['priority'], "MEDIUM")
        self.assertEqual(task_dict['status'], "IN_PROGRESS")
    
    def test_task_post_init(self):
        """Test post initialization defaults"""
        task = DevelopmentTask(
            id="test-003",
            title="Defaults Test",
            description="Testing defaults",
            priority=TaskPriority.LOW,
            status=TaskStatus.PENDING,
            source="test",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        self.assertEqual(task.dependencies, [])
        self.assertEqual(task.estimated_effort, "")
        self.assertEqual(task.actual_effort, "")


class TestTaskQueueManager(unittest.TestCase):
    """Test the TaskQueueManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = TaskQueueManager(self.temp_dir)
    
    def tearDown(self):
        """Clean up after tests"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_task_queue_initialization(self):
        """Test TaskQueueManager initialization"""
        self.assertEqual(self.manager.repo_root, self.temp_dir)
        self.assertEqual(len(self.manager.tasks), 0)
        self.assertEqual(self.manager.task_counter, 0)
    
    def test_load_save_queue(self):
        """Test saving and loading task queue"""
        # Create some tasks
        task1 = DevelopmentTask(
            id="save-001",
            title="Save Test 1",
            description="Testing save/load",
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING,
            source="test",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        task2 = DevelopmentTask(
            id="save-002",
            title="Save Test 2",
            description="Testing save/load 2",
            priority=TaskPriority.LOW,
            status=TaskStatus.COMPLETED,
            source="test",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        self.manager.tasks = [task1, task2]
        
        # Save queue
        queue_file = os.path.join(self.temp_dir, "test_queue.json")
        self.manager.save_queue(queue_file)
        self.assertTrue(os.path.exists(queue_file))
        
        # Load into new manager
        new_manager = TaskQueueManager(self.temp_dir)
        new_manager.load_queue(queue_file)
        
        self.assertEqual(len(new_manager.tasks), 2)
        self.assertEqual(new_manager.tasks[0].id, "save-001")
        self.assertEqual(new_manager.tasks[1].id, "save-002")
        self.assertEqual(new_manager.tasks[0].priority, TaskPriority.HIGH)
    
    def test_get_next_tasks(self):
        """Test getting next tasks by priority"""
        # Create tasks with different priorities
        tasks = [
            DevelopmentTask(
                id=f"priority-{i}",
                title=f"Priority Test {i}",
                description=f"Task {i}",
                priority=TaskPriority(p) if p <= 4 else TaskPriority.LOW,
                status=TaskStatus.PENDING,
                source="test",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            for i, p in enumerate([1, 4, 2, 3, 1, 4], 1)
        ]
        
        self.manager.tasks = tasks
        next_tasks = self.manager.get_next_tasks(count=3)
        
        self.assertEqual(len(next_tasks), 3)
        # Should be sorted by priority (highest first)
        self.assertEqual(next_tasks[0].priority.value, 4)
        self.assertEqual(next_tasks[1].priority.value, 4)
        self.assertEqual(next_tasks[2].priority.value, 3)
    
    def test_get_next_tasks_filters_pending(self):
        """Test that get_next_tasks only returns pending tasks"""
        tasks = [
            DevelopmentTask(
                id="pending-001",
                title="Pending Task",
                description="Should appear",
                priority=TaskPriority.HIGH,
                status=TaskStatus.PENDING,
                source="test",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            DevelopmentTask(
                id="completed-001",
                title="Completed Task",
                description="Should not appear",
                priority=TaskPriority.HIGH,
                status=TaskStatus.COMPLETED,
                source="test",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
        ]
        
        self.manager.tasks = tasks
        next_tasks = self.manager.get_next_tasks(count=10)
        
        self.assertEqual(len(next_tasks), 1)
        self.assertEqual(next_tasks[0].id, "pending-001")
    
    def test_update_task_status(self):
        """Test updating task status"""
        task = DevelopmentTask(
            id="update-001",
            title="Update Test",
            description="Testing status update",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            source="test",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        self.manager.tasks = [task]
        self.manager.update_task_status("update-001", TaskStatus.COMPLETED, "Done!")
        
        self.assertEqual(self.manager.tasks[0].status, TaskStatus.COMPLETED)
        self.assertEqual(self.manager.tasks[0].notes, "Done!")
    
    def test_concurrent_queue_access(self):
        """Test thread safety of queue operations"""
        manager = TaskQueueManager(self.temp_dir)
        
        def add_tasks(thread_id, count):
            for i in range(count):
                task = DevelopmentTask(
                    id=f"concurrent-{thread_id}-{i}",
                    title=f"Concurrent Task {thread_id}-{i}",
                    description=f"From thread {thread_id}",
                    priority=TaskPriority.MEDIUM,
                    status=TaskStatus.PENDING,
                    source="test",
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat()
                )
                manager.tasks.append(task)
        
        # Run multiple threads adding tasks
        threads = []
        for t in range(5):
            thread = threading.Thread(target=add_tasks, args=(t, 20))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have 100 tasks total
        self.assertEqual(len(manager.tasks), 100)


class TestOpenClawController(unittest.TestCase):
    """Test the OpenClawController class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        # Mock the controller to avoid actual CLI calls
        self.controller = OpenClawController(self.temp_dir)
        # Clear any tasks from initialization
        self.controller.active_tasks = {}
        self.controller.completed_tasks = []
        self.controller.task_counter = 0
    
    def tearDown(self):
        """Clean up after tests"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_controller_initialization(self):
        """Test OpenClawController initialization"""
        self.assertEqual(self.controller.workspace_root, self.temp_dir)
        self.assertEqual(len(self.controller.active_tasks), 0)
        self.assertEqual(self.controller.task_counter, 0)
    
    def test_create_task(self):
        """Test task creation"""
        task_id = self.controller.create_task(
            task_type=OpenClawTaskType.CODE_GENERATION,
            description="Generate a function",
            prompt="Create a hello world function",
            priority=2
        )
        
        self.assertTrue(task_id.startswith("openclaw-"))
        self.assertIn(task_id, self.controller.active_tasks)
        
        task = self.controller.active_tasks[task_id]
        self.assertEqual(task.task_type, OpenClawTaskType.CODE_GENERATION)
        self.assertEqual(task.description, "Generate a function")
        self.assertEqual(task.priority, 2)
        self.assertEqual(task.status, "pending")
    
    def test_get_task_status(self):
        """Test getting task status"""
        task_id = self.controller.create_task(
            task_type=OpenClawTaskType.RESEARCH,
            description="Research task",
            prompt="Research something",
        )
        
        status = self.controller.get_task_status(task_id)
        self.assertIsNotNone(status)
        self.assertEqual(status['id'], task_id)
        self.assertEqual(status['status'], "pending")
        
        # Test non-existent task
        status = self.controller.get_task_status("nonexistent")
        self.assertIsNone(status)
    
    def test_list_tasks(self):
        """Test listing tasks"""
        # Create multiple tasks
        for i in range(3):
            self.controller.create_task(
                task_type=OpenClawTaskType.TESTING,
                description=f"Test task {i}",
                prompt=f"Execute test {i}",
            )
        
        active = self.controller.list_active_tasks()
        self.assertEqual(len(active), 3)
        
        completed = self.controller.list_completed_tasks()
        self.assertEqual(len(completed), 0)
    
    def test_cancel_task(self):
        """Test cancelling a task"""
        task_id = self.controller.create_task(
            task_type=OpenClawTaskType.BUG_FIX,
            description="Fix a bug",
            prompt="Fix the bug",
        )
        
        result = self.controller.cancel_task(task_id)
        self.assertTrue(result)
        
        # Task should be moved to completed with cancelled status
        self.assertNotIn(task_id, self.controller.active_tasks)
        completed = self.controller.list_completed_tasks()
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]['status'], "cancelled")
    
    def test_cancel_running_task(self):
        """Test that running tasks cannot be cancelled"""
        task_id = self.controller.create_task(
            task_type=OpenClawTaskType.FEATURE_IMPL,
            description="Implement feature",
            prompt="Implement it",
        )
        
        # Manually set status to running
        self.controller.active_tasks[task_id].status = "running"
        
        result = self.controller.cancel_task(task_id)
        self.assertFalse(result)  # Should not be able to cancel running task


class TestLoadTesting(unittest.TestCase):
    """Load tests for task queue and coordinator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = TaskQueueManager(self.temp_dir)
        self.controller = OpenClawController(self.temp_dir)
        self.controller.active_tasks = {}
        self.controller.completed_tasks = []
        self.controller.task_counter = 0
    
    def tearDown(self):
        """Clean up after tests"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_task_queue_load_1000_tasks(self):
        """Test task queue with 1000 tasks"""
        print("\n  Loading 1000 tasks into queue...")
        
        start_time = time.time()
        for i in range(1000):
            task = DevelopmentTask(
                id=f"load-{i:04d}",
                title=f"Load Test Task {i}",
                description=f"Task number {i} for load testing",
                priority=TaskPriority(i % 4 + 1),
                status=TaskStatus.PENDING,
                source="load_test",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            self.manager.tasks.append(task)
        
        load_time = time.time() - start_time
        print(f"  Loaded 1000 tasks in {load_time:.3f}s")
        
        # Test retrieval performance
        start_time = time.time()
        next_tasks = self.manager.get_next_tasks(count=10)
        retrieval_time = time.time() - start_time
        print(f"  Retrieved 10 tasks in {retrieval_time:.3f}s")
        
        self.assertEqual(len(self.manager.tasks), 1000)
        self.assertEqual(len(next_tasks), 10)
        
        # Save and load performance
        queue_file = os.path.join(self.temp_dir, "load_test_queue.json")
        
        start_time = time.time()
        self.manager.save_queue(queue_file)
        save_time = time.time() - start_time
        print(f"  Saved 1000 tasks in {save_time:.3f}s")
        
        new_manager = TaskQueueManager(self.temp_dir)
        start_time = time.time()
        new_manager.load_queue(queue_file)
        load_time = time.time() - start_time
        print(f"  Loaded 1000 tasks from disk in {load_time:.3f}s")
        
        self.assertEqual(len(new_manager.tasks), 1000)
    
    def test_concurrent_task_creation(self):
        """Test concurrent task creation in controller"""
        print("\n  Testing concurrent task creation...")
        
        def create_tasks(thread_id, count):
            task_ids = []
            for i in range(count):
                task_id = self.controller.create_task(
                    task_type=OpenClawTaskType.CODE_GENERATION,
                    description=f"Concurrent task {thread_id}-{i}",
                    prompt=f"Execute task from thread {thread_id}, iteration {i}",
                )
                task_ids.append(task_id)
            return task_ids
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for t in range(10):
                future = executor.submit(create_tasks, t, 50)
                futures.append(future)
            
            all_task_ids = []
            for future in as_completed(futures):
                task_ids = future.result()
                all_task_ids.extend(task_ids)
        
        total_time = time.time() - start_time
        print(f"  Created {len(all_task_ids)} tasks concurrently in {total_time:.3f}s")
        
        self.assertEqual(len(all_task_ids), 500)
        self.assertEqual(len(self.controller.active_tasks), 500)
    
    def test_task_queue_save_load_stress(self):
        """Test repeated save/load cycles"""
        print("\n  Testing save/load stress...")
        
        queue_file = os.path.join(self.temp_dir, "stress_queue.json")
        
        for cycle in range(50):
            # Add some tasks
            for i in range(10):
                task = DevelopmentTask(
                    id=f"stress-{cycle}-{i}",
                    title=f"Stress Task {cycle}-{i}",
                    description=f"Cycle {cycle}, task {i}",
                    priority=TaskPriority.MEDIUM,
                    status=TaskStatus.PENDING,
                    source="stress_test",
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat()
                )
                self.manager.tasks.append(task)
            
            # Save
            self.manager.save_queue(queue_file)
            
            # Load into new manager
            new_manager = TaskQueueManager(self.temp_dir)
            new_manager.load_queue(queue_file)
            
            # Verify
            self.assertEqual