---
name: fix-wrapper-script-paths
description: Systematic approach to fixing shell wrapper scripts that reference incorrect interpreter paths or target file locations
category: software-development
version: 1.0.0
---

# Fix Wrapper Script Paths

## Overview
This skill provides a systematic approach to fixing shell wrapper scripts that reference incorrect interpreter paths or target file locations. Common when migrating environments or when dependencies change locations.

## When to Use
- Wrapper scripts fail with "command not found" or "no such file or directory" errors
- Error messages point to missing interpreters or scripts that you know exist elsewhere
- After migrating projects between systems with different directory structures
- When wrapper scripts reference virtual environments that don't exist or have changed

## Steps

### 1. Identify the Wrapper Script and Error
```bash
# Run the failing script to see the exact error
./wrapper.sh arg1 arg2
# or
bash wrapper.sh arg1 arg2
```

### 2. Examine the Wrapper Script
```bash
cat wrapper.sh
```
Look for:
- Interpreter path (#! /path/to/interpreter)
- Commands being called with absolute paths
- References to other scripts or binaries

### 3. Locate the Actual Files
For each path referenced in the wrapper:
```bash
# Check if interpreter exists
which python3
# or
ls -la /path/to/referenced/interpreter

# Check if target script exists
find /home/ubuntu -name "target_script.py" 2>/dev/null
find /home/ubuntu -name "target_script.sh" 2>/dev/null
# or search more broadly
sudo find / -name "target_script*" 2>/dev/null | grep -v "Permission denied"
```

### 4. Common Fix Patterns
#### Fix Incorrect Interpreter Path
If wrapper has: `#! /home/ubuntu/old-venv/bin/python3`
But actual is: `/usr/bin/python3`
Edit: `sed -i 's|#! /home/ubuntu/old-venv/bin/python3|#! /usr/bin/python3|' wrapper.sh`

#### Fix Incorrect Script Path
If wrapper has: `/home/ubuntu/old-project/scripts/target.py`
But actual is: `/home/ubuntu/new-project/archive/scripts/target.py`
Edit: `sed -i 's|/home/ubuntu/old-project/scripts/|/home/ubuntu/new-project/archive/scripts/|' wrapper.sh`

#### Fix Missing Virtual Environment References
If wrapper references a venv that doesn't exist:
- Option 1: Update to use system interpreter: `sed -i 's|/home/ubuntu/old-venv/bin/||g' wrapper.sh`
- Option 2: Recreate the virtual environment in the expected location
- Option 3: Update path to current venv location

### 5. Verify the Fix
```bash
# Test the wrapper script
./wrapper.sh arg1 arg2
# Should now work without "command not found" errors
```

### 6. Test with Actual Arguments
Run with real parameters to ensure it works end-to-end:
```bash
./wrapper.sh --help
# or whatever normal usage is
```

## Pitfalls & Troubleshooting

### Pitfall: Multiple Path Issues
Wrapper scripts often have more than one incorrect path. Fix one error, then run again to see if another appears.

**Solution:** Iterate through fixes - fix one issue, test, fix next issue, test, etc.

### Pitfall: Relative vs Absolute Paths
Some wrappers use relative paths that break when called from different directories.

**Solution:** Convert to absolute paths based on script location:
```bash
# Instead of: ./target_script.py
# Use: "$(dirname "$0")/target_script.py"
```

### Pitfall: Permission Issues
Fixed paths might point to files without execute permissions.

**Solution:** After fixing paths, ensure target files are executable:
```bash
chmod +x /path/to/target_script.sh
```

### Pitfall: Environment Variables
Some scripts depend on environment variables set in the wrapper.

**Solution:** Check if wrapper sets PATH, PYTHONPATH, etc. that are needed but missing.

## Verification
After fixing:
1. Script runs without "command not found" errors
2. Script performs its intended function
3. No errors in execution (check exit code: `echo $?` should be 0)
4. Expected outputs or side effects occur

## Example Fix
From the human-ai project:
- **Problem:** `todo.sh` failed with "/home/ubuntu/human-ai/venv/bin/python3: No such file or directory"
- **Found:** 
  - Wrong Python path (venv didn't exist)
  - Wrong script path (referenced `scripts_archive/` instead of `archive/scripts_archive/`)
- **Fixes:**
  ```bash
  sed -i 's|/home/ubuntu/human-ai/venv/bin/python3|/usr/bin/python3|' scripts/todo.sh
  sed -i 's|scripts_archive/todo_bridge.py|archive/scripts_archive/todo_bridge.py|' scripts/todo.sh
  ```
- **Result:** `bash scripts/todo.sh list` now returns pending tasks correctly

## Related Skills
- `missing-file-forensics`: For locating missing files when you're not sure where they might be
- `systematic-debugging`: General debugging approach that this skill complements
- `llm-shell-script-indentation-fix`: For fixing indentation issues in shell scripts
