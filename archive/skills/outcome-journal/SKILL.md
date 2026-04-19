---
name: outcome-journal
description: Logs the outcome of tasks, features, and experiments to OUTCOME_LOG.md for swarm transparency and learning.
category: productivity
---

# Outcome Journal Skill

This skill provides a structured way for swarm agents to record the results of their actions. By maintaining a historical record of what worked and what failed, the swarm can avoid repeating mistakes and accelerate its evolution.

## 🛠️ Usage

The skill should be called after a significant task is completed, a feature is implemented, or an experiment is concluded.

### Required Parameters:
- `task_name`: The name of the task or feature.
- `outcome`: 'SUCCESS', 'PARTIAL_SUCCESS', or 'FAILURE'.
- `details`: A brief description of what happened and why.
- `lesson`: The key takeaway or "wisdom" gained from this outcome.

## 📝 Implementation Logic

1. Open `OUTCOME_LOG.md` in the root of the swarm repository.
2. Append a new entry with the current timestamp.
3. Use the following format:
   `### [YYYY-MM-DD HH:MM] {outcome} - {task_name}`
   `- **Details**: {details}`
   `- **Lesson**: {lesson}`
   `---`

## ⚠️ Pitfalls
- **Vagueness**: Avoid "It worked." Instead, use "Implemented X using Y, verified by Z."
- **Ignoring Failures**: Failures are more valuable for learning than successes. Ensure all failures are logged with a root-cause analysis.

## ✅ Verification
- Check if `OUTCOME_LOG.md` exists and contains the entry.
- Ensure the format is consistent for future programmatic parsing.
