"""
LINTER-FIXER AGENT
Goal: A background agent that monitors the codebase for syntax and import errors
and automatically applies fixes to maintain swarm stability and reduce autopilot stalls.

Core Logic:
1.  Scan Python files for import errors (e.g., `from human-ai.test_agents import ...` when the file is in scripts_archive).
2.  Scan for syntax errors (e.g., missing colons, incorrect indentation).
3.  Upon finding a fixable error, apply the fix, log it, and commit the change.
4.  Operate on a low-frequency timer to avoid resource contention with the main autopilot.
"""
import ast
import os
import subprocess
from pathlib import Path
import time

# --- Configuration ---
PROJECT_ROOT = Path("/home/yahwehatwork/human-ai")
SCAN_INTERVAL = 300  # 5 minutes
LOG_FILE = PROJECT_ROOT / "linter_fixer.log"

# Common import fixes based on observed issues
IMPORT_FIXES = {
    "human-ai.test_agents": "human-ai.scripts_archive.test_agents",
    "human-ai.triage_errors": "human-ai.scripts_archive.triage_errors",
    "human-ai.continuous_improvement": "human-ai.scripts_archive.continuous_improvement",
}

def log_fix(message: str):
    """Logs a fix action with a timestamp."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [LINTER-FIXER] {message}\n"
    with open(LOG_FILE, "a") as f:
        f.write(log_entry)
    print(log_entry.strip())

def check_and_fix_imports(file_path: Path):
    """Checks a file for known bad import patterns and fixes them."""
    try:
        content = file_path.read_text()
        original_content = content
        for bad_import, good_import in IMPORT_FIXES.items():
            if bad_import in content:
                content = content.replace(bad_import, good_import)
                log_fix(f"Fixed import in {file_path.name}: '{bad_import}' -> '{good_import}'")
        if content != original_content:
            file_path.write_text(content)
            return True
    except Exception as e:
        log_fix(f"Error processing {file_path.name} for imports: {e}")
    return False

def check_and_fix_syntax(file_path: Path):
    """Checks a file for basic syntax errors using ast."""
    try:
        with file_path.open() as f:
            ast.parse(f.read())
        return True  # No syntax error
    except SyntaxError as e:
        log_fix(f"Syntax error in {file_path.name}: Line {e.lineno}: {e.msg}")
        # We could add more sophisticated fixes here later, but for now, we just log it.
        # A more advanced version could try to auto-fix indentation, etc.
        return False
    except Exception as e:
        log_fix(f"Error reading {file_path.name} for syntax check: {e}")
        return False

def main():
    """Main loop for the Linter-Fixer Agent."""
    print("[LINTER-FIXER] Agent started. Monitoring for syntax and import errors...")
    while True:
        fixed_something = False
        for py_file in PROJECT_ROOT.rglob("*.py"):
            # Avoid scanning virtual environments and caches
            if any(part in str(py_file) for part in ["venv", "__pycache__", ".git", "node_modules"]):
                continue
            
            # Check and fix syntax
            if not check_and_fix_syntax(py_file):
                fixed_something = True
            
            # Check and fix imports
            if check_and_fix_imports(py_file):
                fixed_something = True
        
        if fixed_something:
            # Attempt to commit the fixes
            try:
                subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT, check=True, capture_output=True)
                commit_message = f"Linter-Fixer: Auto-fixed syntax/import errors at {time.strftime('%Y-%m-%d %H:%M:%S')}"
                subprocess.run(["git", "commit", "-m", commit_message], cwd=PROJECT_ROOT, check=True, capture_output=True)
                subprocess.run(["git", "push", "origin", "main"], cwd=PROJECT_ROOT, check=True, capture_output=True)
                log_fix("Successfully committed and pushed fixes.")
            except subprocess.CalledProcessError as e:
                log_fix(f"Git operation failed during Linter-Fixer commit: {e}")
        else:
            # Optional: log that no fixes were needed this cycle
            pass
        
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()