#!/usr/bin/env python3
"""
Obsidian Sync Script for Human-AI Swarm
Syncs completed tasks and session logs to Obsidian vault for local knowledge management.
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path

# Configuration
# NOTE: memory/bus/completed and memory/misc do not exist — the memory/ dir was never created.
# Correct source paths as of 2026-05-15:
#   - Completed task JSON files: data/obsidian/sync_status.json (single sync record)
#   - Session log markdowns: data/logs/ (agent log files)
#   - Trade summaries: data/obsidian/trades/ (daily session summaries)
#   - Obsidian vault root: data/obsidian/ (the real vault, not obsidian-vault/)
HUMAN_AI_ROOT = Path("/home/yahwehatwork/human-ai")
COMPLETED_TASKS_DIR = HUMAN_AI_ROOT / "workspace"           # workspace/*.json task files
SESSION_LOGS_DIR = HUMAN_AI_ROOT / "data" / "logs"          # agent log files (*.log, *.md)
OBSIDIAN_VAULT_ROOT = HUMAN_AI_ROOT / "data" / "obsidian"   # real vault (was: obsidian-vault/)
OBSIDIAN_COMPLETED_DIR = OBSIDIAN_VAULT_ROOT / "System_State"
OBSIDIAN_SESSION_DIR = OBSIDIAN_VAULT_ROOT / "sessions"

def ensure_directories():
    """Ensure Obsidian vault directories exist."""
    OBSIDIAN_COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
    OBSIDIAN_SESSION_DIR.mkdir(parents=True, exist_ok=True)

def sync_completed_tasks():
    """Sync completed tasks to Obsidian vault."""
    print(f"Syncing completed tasks from {COMPLETED_TASKS_DIR}...")
    
    if not COMPLETED_TASKS_DIR.exists():
        print(f"Completed tasks directory not found: {COMPLETED_TASKS_DIR}")
        return
    
    completed_files = list(COMPLETED_TASKS_DIR.glob("*.json"))
    print(f"Found {len(completed_files)} completed task files.")
    
    for json_file in completed_files:
        try:
            with open(json_file, 'r') as f:
                task_data = json.load(f)
            
            # Create markdown content
            md_content = f"""---
id: {task_data.get('id', 'unknown')}
timestamp: {task_data.get('timestamp', 'unknown')}
sender: {task_data.get('sender', 'unknown')}
type: {task_data.get('type', 'unknown')}
subject: {task_data.get('subject', 'No Subject')}
status: {task_data.get('status', 'unknown')}
timestamp_finished: {task_data.get('timestamp_finished', 'unknown')}
---

# {task_data.get('subject', 'No Subject')}

## Task Details
- **ID**: {task_data.get('id', 'unknown')}
- **Timestamp**: {task_data.get('timestamp', 'unknown')}
- **Sender**: {task_data.get('sender', 'unknown')}
- **Type**: {task_data.get('type', 'unknown')}
- **Status**: {task_data.get('status', 'unknown')}
- **Finished**: {task_data.get('timestamp_finished', 'unknown')}

## Payload
```json
{json.dumps(task_data.get('payload', {}), indent=2)}
```
"""
            
            # Create filename based on timestamp and subject for readability
            timestamp_str = task_data.get('timestamp', 'unknown')
            if timestamp_str != 'unknown':
                try:
                    # Parse timestamp and format for filename
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d')
                except:
                    date_str = 'unknown-date'
            else:
                date_str = 'unknown-date'
            
            # Clean subject for filename
            subject = task_data.get('subject', 'no-subject')
            # Remove or replace invalid filename characters
            safe_subject = "".join(c for c in subject if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_subject = safe_subject.replace(' ', '_')
            if not safe_subject:
                safe_subject = 'task'
            
            filename = f"{date_str}_{safe_subject}_{task_data.get('id', 'unknown')[:8]}.md"
            output_path = OBSIDIAN_COMPLETED_DIR / filename
            
            # Write markdown file
            with open(output_path, 'w') as f:
                f.write(md_content)
            
            print(f"  Synced: {json_file.name} -> {filename}")
            
        except Exception as e:
            print(f"  Error processing {json_file.name}: {e}")

def sync_session_logs():
    """Sync session logs to Obsidian vault."""
    print(f"Syncing session logs from {SESSION_LOGS_DIR}...")
    
    if not SESSION_LOGS_DIR.exists():
        print(f"Session logs directory not found: {SESSION_LOGS_DIR}")
        return
    
    log_files = list(SESSION_LOGS_DIR.glob("*.md"))
    print(f"Found {len(log_files)} session log files.")
    
    for md_file in log_files:
        try:
            # Simply copy the file to the session logs directory
            # We'll keep the original filename but could rename if desired
            output_path = OBSIDIAN_SESSION_DIR / md_file.name
            
            # Copy file
            shutil.copy2(md_file, output_path)
            print(f"  Synced: {md_file.name}")
            
        except Exception as e:
            print(f"  Error processing {md_file.name}: {e}")

def create_vault_index():
    """Create a simple index file for the Obsidian vault."""
    index_content = f"""# Human-AI Swarm Obsidian Vault

This vault contains synchronized knowledge from the Human-AI Swarm system.

## Sections
- [[Completed Tasks]] - Synced completed task records
- [[Session Logs]] - Raw session logs from agent interactions

## Last Updated
{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

## Statistics
- Completed Tasks: {len(list(OBSIDIAN_COMPLETED_DIR.glob('*.md'))) if OBSIDIAN_COMPLETED_DIR.exists() else 0}
- Session Logs: {len(list(OBSIDIAN_SESSION_DIR.glob('*.md'))) if OBSIDIAN_SESSION_DIR.exists() else 0}

## Usage
This vault is designed to be opened directly in Obsidian for local knowledge management and memory enhancement.
Use Obsidian's graph view to explore connections between tasks and sessions.
"""
    
    index_path = OBSIDIAN_VAULT_ROOT / "index.md"
    with open(index_path, 'w') as f:
        f.write(index_content)
    print(f"Created vault index: {index_path}")

def main():
    """Main sync function."""
    print("Starting Obsidian synchronization...")
    print(f"Human AI Root: {HUMAN_AI_ROOT}")
    print(f"Obsidian Vault: {OBSIDIAN_VAULT_ROOT}")
    print("-" * 50)
    
    ensure_directories()
    sync_completed_tasks()
    sync_session_logs()
    create_vault_index()
    
    print("-" * 50)
    print("Obsidian synchronization completed!")

if __name__ == "__main__":
    main()