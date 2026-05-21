#!/usr/bin/env python3
"""
Simple Predictive Task Queue Optimizer
"""

import json
import os
from pathlib import Path
from datetime import datetime

def main():
    print("Predictive Task Queue Optimizer")
    print("Loading task data...")
    
    # Load stqueue.json
    stqueue_path = Path("/home/yahwehatwork/human-ai/infrastructure/configs/stqueue.json")
    if stqueue_path.exists():
        with open(stqueue_path, 'r') as f:
            data = json.load(f)
        
        queue = data.get("queue", [])
        completed = [t for t in queue if t.get("status") == "completed"]
        pending = [t for t in queue if t.get("status") == "pending"]
        
        print(f"Total tasks: {len(queue)}")
        print(f"Completed: {len(completed)}")
        print(f"Pending: {len(pending)}")
        
        # Show some pending tasks
        if pending:
            print("\nFirst 5 pending tasks:")
            for task in pending[:5]:
                print(f"  {task.get('id')}: {task.get('task')[:50]}... [{task.get('agent')}]")
    else:
        print("stqueue.json not found")

if __name__ == "__main__":
    main()
