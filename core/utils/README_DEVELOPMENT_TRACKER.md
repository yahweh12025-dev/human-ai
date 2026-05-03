# Development Tracker Utility

This utility provides structured logging for swarm development activities and progress tracking. It builds upon the existing SwarmLogger to provide specialized methods for logging development-specific activities.

## Features

- **Activity Logging**: Log various types of development activities with structured data
- **Progress Tracking**: Integrate with existing todo.json system to track task progress
- **Velocity Metrics**: Calculate and log development velocity metrics (placeholder implementation)
- **JSON Output**: All logs are output as JSON lines for easy parsing and analysis

## Activity Types

The tracker supports logging the following activity types:
- `task_start`: Start of a development task
- `task_complete`: Completion of a development task
- `task_progress`: Progress updates on a task
- `code_commit`: Code commits related to tasks
- `design_decision`: Design decisions made during development
- `bug_fix`: Bug fixes implemented
- `refactor`: Refactoring activities
- `review`: Code or design reviews
- `meeting`: Development meetings
- `research`: Research activities
- `experiment`: Experiments conducted
- `deployment`: Deployments to various environments
- `integration`: Integrations between components
- `testing`: Testing activities
- `documentation`: Documentation work
- `other`: Miscellaneous activities

## Usage

```python
from core.utils.development_tracker import get_development_tracker, ActivityType

# Get a tracker instance
tracker = get_development_tracker("my_agent")

# Log task start
tracker.log_task_start("task-001", "Implement new feature")

# Log progress
tracker.log_task_progress("task-001", "Working on core logic", progress_percent=50)

# Log code commit
tracker.log_code_commit("task-001", "abc123def", "Added core functionality")

# Log design decision
tracker.log_design_decision("task-001", "Use microservices architecture", 
                          "Better scalability and team autonomy")

# Log testing
tracker.log_testing("unit", coverage=85.0, passed=True)

# Log task completion
tracker.log_task_complete("task-001", "Implement new feature")

# Update task status in todo.json
tracker.update_task_status_in_todo("task-001", "completed", 
                                 "Feature implemented and tested")

# Get current todo progress
progress = tracker.get_todo_progress()
print(f"Progress: {progress}")

# Log velocity metrics
tracker.log_velocity_metrics(days=7)
```

## Integration with Existing Systems

This utility is designed to work seamlessly with:
- **SwarmLogger**: Uses the existing swarm_logger.py for consistent logging format
- **todo.json**: Integrates with the existing task tracking system in infrastructure/configs/todo.json
- **Agent Swarm**: Can be used by any agent in the swarm to log their development activities

## Log Format

All activities are logged as JSON lines with the following structure:
```json
{
  "timestamp": "2026-05-02T12:29:24.615841Z",
  "source": "my_agent",
  "level": "INFO",
  "message": "Starting task: Implement new feature",
  "activity_type": "task_start",
  "task_id": "task-001"
}
```

Additional data specific to each activity type is included in the `data` field.

## Files

- `development_tracker.py`: Main implementation
- `README_DEVELOPMENT_TRACKER.md`: This file

## Example Output

When used, the tracker will output JSON lines to stdout (or configured output stream) that can be collected and analyzed by log aggregation systems.