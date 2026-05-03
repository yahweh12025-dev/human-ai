# Migrating to Swarm Logger

This guide explains how to migrate existing agents to use the new standardized `SwarmLogger` utility.

## Why Migrate?

- **Consistent Format**: All logs follow the same JSON structure, making them easily parseable by log analysis tools
- **Rich Context**: Logs include timestamp, source, level, message, and optional structured data
- **Machine Readable**: JSON lines can be directly ingested by log aggregation systems (ELK, Splunk, etc.)
- **Backward Compatible**: Still human-readable when needed

## Current Logging Patterns to Replace

### Pattern 1: Print Statements
```python
# BEFORE
print(f"[{agent_name}] Starting task {task_id}")

# AFTER
logger = get_logger(agent_name)
logger.info("Starting task", task_id=task_id)
```

### Pattern 2: Basic Logging (if any)
```python
# BEFORE
logging.info("Agent initialized")

# AFTER
logger = get_logger(__class__.__name__)
logger.info("Agent initialized")
```

### Pattern 3: Error Handling
```python
# BEFORE
try:
    # ... some operation ...
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()

# AFTER
try:
    # ... some operation ...
except Exception as e:
    logger.error("Operation failed", error=str(e), traceback=traceback.format_exc())
```

## Migration Steps

1. **Import the Logger**
   ```python
   from core.utils.swarm_logger import get_logger
   ```

2. **Create a Logger Instance**
   Add this in your agent's `__init__` method or at the module level:
   ```python
   self.logger = get_logger(self.__class__.__name__)
   # OR for module-level logger:
   # logger = get_logger("agent_name")
   ```

3. **Replace Print Statements**
   Convert `print()` calls to appropriate logger methods:
   - `print("info message")` → `logger.info("info message")`
   - `print("WARNING: ...")` → `logger.warning("...")`
   - `print("ERROR: ...")` → `logger.error("...")`

4. **Enhance with Structured Data**
   Take advantage of the ability to add context:
   ```python
   # BEFORE
   logger.info(f"Processing file {filename}")
   
   # AFTER
   logger.info("Processing file", filename=filename, size_kb=file_size)
   ```

## Example: Converting Health Bot

### Before Migration
```python
# In bot.py
print(f"[{self.name}] Health check started")
# ...
except Exception as e:
    print(f"[{self.name}] Health check failed: {e}")
```

### After Migration
```python
# In bot.py
from core.utils.swarm_logger import get_logger

class HealthBotAgent:
    def __init__(self, name="health_bot"):
        self.name = name
        self.logger = get_logger(name)
        
    def run_health_check(self):
        self.logger.info("Health check started")
        try:
            # ... health check logic ...
            self.logger.info("Health check passed", checks_passed=5)
        except Exception as e:
            self.logger.error(
                "Health check failed", 
                error=str(e),
                traceback=traceback.format_exc()
            )
            raise
```

## Verification

After migration, verify that:
1. Logs appear as valid JSON lines (one per line)
2. Each log entry contains: timestamp, source, level, message
3. Optional data fields appear in the "data" object when provided
4. No print statements remain in the code (except for debugging)

## Benefits After Migration

- The Swarm Optimizer skill can now parse logs automatically using `json.loads()` per line
- Error pattern recognition becomes more accurate and less prone to false positives
- Log aggregation tools can filter by source, level, or extract data fields
- Audit trails become machine-actionable for compliance and debugging