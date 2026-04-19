#!/usr/bin/env python3
"""
Agent Error Queue & Auto-Triage
Analyzes /home/ubuntu/human-ai/errors/ and creates a prioritized queue of issues to solve.
"""
import os
from pathlib import Path
from datetime import datetime
from collections import Counter

def triage_errors():
    errors_dir = Path('/home/ubuntu/human-ai/errors')
    if not errors_dir.exists():
        print("No errors directory found.")
        return

    error_files = sorted(errors_dir.glob('*.log'), reverse=True)
    if not error_files:
        print("No error logs found. Everything looks clean! ✅")
        return

    print(f"🔍 Found {len(error_files)} error logs. Triaging...")
    
    issue_counts = Counter()
    unique_issues = {}

    for file in error_files:
        content = file.read_text()
        # Simple heuristic to group by the last line of the traceback/error message
        lines = content.splitlines()
        error_msg = lines[-1] if lines else "Unknown Error"
        # If the last line is just a print statement, look for the actual Exception
        if "Error logged to" in error_msg:
            # Look back for the Exception line
            for line in reversed(lines):
                if "Exception" in line or "Error:" in line:
                    error_msg = line
                    break
        
        issue_counts[error_msg] += 1
        unique_issues[error_msg] = file

    # Create the Queue
    queue_file = Path('/home/ubuntu/human-ai/error_queue.md')
    with open(queue_file, 'w') as f:
        f.write("# 🚨 Agent Error Queue\n")
        f.write(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Prioritized Issues\n")
        
        # Sort by frequency
        for issue, count in issue_counts.most_common():
            example_log = unique_issues[issue]
            f.write(f"### [PRIORITY {'HIGH' if count > 5 else 'MED'}] {issue}\n")
            f.write(f"- **Occurrences:** {count}\n")
            f.write(f"- **Latest Log:** `{example_log}`\n")
            f.write("- **Status:** ⏳ Pending Solution\n\n")

    print(f"✅ Error queue generated at {queue_file}")

if __name__ == "__main__":
    triage_errors()
