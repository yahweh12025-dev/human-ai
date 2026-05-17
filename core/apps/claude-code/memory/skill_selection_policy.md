---
name: Skill Selection Policy
description: How Claude Code automatically selects relevant skills
type: project
---

Claude Code automatically selects relevant skills from the combined library (Superpowers, everything-claude-code, and custom additions) based on:

- **Keywords** in the request that match skill names or purposes
- **Task type**: debugging, testing, planning, refactoring, review, deployment, research, etc.
- **Workflow phase**: initial design (brainstorming, writing-plans), implementation (test-driven-development, executing-plans), completion (finishing-a-development-branch)

Selected skills guide the approach, ensuring best practices (TDD, systematic debugging, evidence-based decisions, etc.). Claude Code will mention the applied skills in its responses when they influence the method.

This auto-selection occurs without explicit user direction; the most suitable workflow is inferred from the task.
