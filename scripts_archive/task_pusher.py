import sqlite3
import os
import subprocess
import time
import random

TODO_DB_PATH = "/home/ubuntu/human-ai/todo.db"

def get_next_task():
    if not os.path.exists(TODO_DB_PATH):
        return None
    try:
        conn = sqlite3.connect(TODO_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, text FROM entries WHERE status = 'pending' ORDER BY id ASC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return row # (id, text)
    except Exception as e:
        print(f"Error: {e}")
        return None

def mark_in_progress(task_id):
    conn = sqlite3.connect(TODO_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE entries SET status = 'in_progress' WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def mark_done(task_id):
    conn = sqlite3.connect(TODO_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE entries SET status = 'done' WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def push_task():
    task = get_next_task()
    if not task:
        print("💤 No pending tasks. Standing by.")
        return

    tid, ttext = task
    print(f"🚀 Pushing Task {tid}: {ttext}")
    
    # Mark as in progress
    mark_in_progress(tid)
    
    # Trigger OpenClaw Agent
    prompt = f"TASK_EXECUTION_REQUIRED: {ttext}. Once completed, please respond with 'TASK_COMPLETE_{tid}'."
    subprocess.run(['openclaw', 'agent', '--agent', 'main', '--message', prompt])
    
    # Wait for the agent to finish (simplified)
    # In a real scenario, we'd poll the logs for 'TASK_COMPLETE'
    print(f"✅ Task {tid} pushed to agent. Monitoring for completion...")

if __name__ == "__main__":
    push_task()
