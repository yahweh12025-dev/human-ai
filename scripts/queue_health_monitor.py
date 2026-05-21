#!/usr/bin/env python3
"""
Automated Task Queue Health Monitor
Detects stalled tasks and sends alerts
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
STQUEUE_PATH = Path("/home/yahwehatwork/human-ai/infrastructure/configs/stqueue.json")
ALERT_THRESHOLD_HOURS = 24  # Alert if task stalled longer than this
CHECK_INTERVAL_MINUTES = 60  # How often to run this check
LAST_RUN_FILE = Path("/home/yahwehatwork/human-ai/data/logs/queue_health_last_run.txt")
ALERT_LOG_FILE = Path("/home/yahwehatwork/human-ai/data/logs/queue_health_alerts.log")

def load_stqueue():
    """Load the stqueue.json file"""
    try:
        with open(STQUEUE_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        log_error(f"Failed to load stqueue.json: {e}")
        return {"queue": []}

def save_stqueue(data):
    """Save the stqueue.json file"""
    try:
        with open(STQUEUE_PATH, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log_error(f"Failed to save stqueue.json: {e}")

def log_error(message):
    """Log error message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] ERROR: {message}\n"
    try:
        with open(ALERT_LOG_FILE, 'a') as f:
            f.write(log_entry)
    except:
        pass  # If we can't log, we can't log
    print(log_entry.strip())

def log_info(message):
    """Log info message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] INFO: {message}\n"
    try:
        with open(ALERT_LOG_FILE, 'a') as f:
            f.write(log_entry)
    except:
        pass
    print(log_entry.strip())

def get_last_run_time():
    """Get the last time this script ran"""
    try:
        if LAST_RUN_FILE.exists():
            with open(LAST_RUN_FILE, 'r') as f:
                timestamp_str = f.read().strip()
                return datetime.fromisoformat(timestamp_str)
    except:
        pass
    return datetime.min

def save_last_run_time():
    """Save the current time as last run"""
    try:
        LAST_RUN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LAST_RUN_FILE, 'w') as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        log_error(f"Failed to save last run time: {e}")

def check_stalled_tasks():
    """Check for stalled tasks in the queue"""
    data = load_stqueue()
    stalled_tasks = []
    
    now = datetime.now()
    threshold_time = now - timedelta(hours=ALERT_THRESHOLD_HOURS)
    
    for task in data.get('queue', []):
        task_id = task.get('id', 'Unknown')
        task_name = task.get('task', 'Unknown Task')
        agent = task.get('agent', 'Unknown Agent')
        status = task.get('status', 'unknown')
        priority = task.get('priority', 999)
        
        # We're interested in tasks that have been pending for too long
        if status == 'pending':
            # Since stqueue doesn't store timestamps, we'll report on all pending high-priority tasks
            # In a production system, we would track when tasks were added/updated
            
            if priority <= 2:  # High priority tasks
                stalled_tasks.append({
                    'id': task_id,
                    'name': task_name,
                    'agent': agent,
                    'priority': priority,
                    'status': status
                })
    
    return stalled_tasks

def generate_health_report():
    """Generate a health report of the task queue"""
    data = load_stqueue()
    
    total_tasks = len(data.get('queue', []))
    pending_tasks = [t for t in data.get('queue', []) if t.get('status') == 'pending']
    completed_tasks = [t for t in data.get('queue', []) if t.get('status') == 'completed']
    in_progress_tasks = [t for t in data.get('queue', []) if t.get('status') == 'in_progress']
    
    # Count by agent
    agent_counts = {}
    for task in data.get('queue', []):
        agent = task.get('agent', 'Unknown')
        agent_counts[agent] = agent_counts.get(agent, 0) + 1
    
    # Count by priority
    priority_counts = {}
    for task in data.get('queue', []):
        priority = task.get('priority', 999)
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_tasks': total_tasks,
        'pending_count': len(pending_tasks),
        'completed_count': len(completed_tasks),
        'in_progress_count': len(in_progress_tasks),
        'agent_distribution': agent_counts,
        'priority_distribution': priority_counts,
        'stalled_tasks': []  # Will be populated below
    }
    
    # Add stalled tasks
    stalled = check_stalled_tasks()
    report['stalled_tasks'] = stalled
    
    return report

def main():
    """Main function"""
    log_info("Starting Task Queue Health Monitor")
    
    # Generate health report
    report = generate_health_report()
    
    # Log summary
    log_info(f"Task Queue Health Report:")
    log_info(f"  Total Tasks: {report['total_tasks']}")
    log_info(f"  Pending: {report['pending_count']}")
    log_info(f"  Completed: {report['completed_count']}")
    log_info(f"  In Progress: {report['in_progress_count']}")
    
    if report['stalled_tasks']:
        log_info(f"  Stalled High Priority Tasks: {len(report['stalled_tasks'])}")
        for task in report['stalled_tasks']:
            log_info(f"    - {task['id']}: {task['name']} ({task['agent']})")
        
        # In a real implementation, we would send email/slack alerts here
        # For now, we'll just log that we would send an alert
        log_info(f"  ALERT: Would send notification for {len(report['stalled_tasks'])} stalled high-priority tasks")
    else:
        log_info("  No stalled high-priority tasks detected")
    
    # Save last run time
    save_last_run_time()
    
    log_info("Task Queue Health Monitor completed")

if __name__ == "__main__":
    main()