#!/usr/bin/env python3
"""
Plan Aggregator for Hermes Autonomous Mode
Reviews roadmap and todo list, provides summary for autonomous cycles
"""

import json
import os
from datetime import datetime

def review_roadmap_and_todo():
    """Review roadmap and todo list, return summary"""
    summary = []
    
    # Check todo.json
    todo_path = '/home/ubuntu/human-ai/infrastructure/configs/todo.json'
    if os.path.exists(todo_path):
        try:
            with open(todo_path, 'r') as f:
                todo_data = json.load(f)
            
            completed_count = len(todo_data.get('completed', []))
            in_progress_count = len(todo_data.get('in_progress', []))
            pending_count = len(todo_data.get('pending', []))
            
            summary.append(f"Todo Status: {completed_count} completed, {in_progress_count} in progress, {pending_count} pending")
            
            # Show recent pending tasks
            pending_tasks = todo_data.get('pending', [])
            if pending_tasks:
                summary.append("Recent pending tasks:")
                for task in pending_tasks[:3]:  # Show first 3
                    summary.append(f"  - {task.get('id', 'unknown')}: {task.get('content', 'No content')[:50]}...")
        except Exception as e:
            summary.append(f"Error reading todo.json: {e}")
    else:
        summary.append("todo.json not found")
    
    # Check if roadmap exists
    roadmap_path = '/home/ubuntu/human-ai/ROADMAP.md'
    if os.path.exists(roadmap_path):
        summary.append("Roadmap: Found")
    else:
        summary.append("Roadmap: Not found")
    
    return "\n".join(summary)

if __name__ == "__main__":
    print(review_roadmap_and_todo())