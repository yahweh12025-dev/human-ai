# Claude Code Integration

This directory contains Claude Code-related files for the Human-AI Project.

## Contents

- **identity.json** - Information about Claude Code model, capabilities, and version
- **soul.md** - Claude Code's principles, approach, and role-specific notes
- **CLAUDE.md** - Copy of the project's main development guide (primary located at repository root)
- **README.md** - This file
- **config.json** - Claude Code configuration and preferences
- **memory/** - Project-specific memory files following the Claude Memory format
  - `MEMORY.md` - Index of all memory files
  - Individual memory files (project, reference, feedback types)
- **skills/** - Skill definitions (Superpowers library and custom skill modules)

## Purpose

This folder serves as a dedicated location for Claude Code integration within the Human-AI Project ecosystem. It allows:

1. Quick access to Claude Code's identity and capabilities
2. Central storage of project-specific memories that persist across sessions
3. A local copy of the project's development guide
4. Configuration for Claude Code behavior
5. Access to a library of reusable skills (Superpowers) for consistent development workflows (TDD, debugging, planning, code review, etc.)

## Relationship to Global Memory

Claude Code also maintains a persistent memory system at `~/.claude/projects/`. The memories in `memory/` here provide a project-local snapshot that can be referenced, synced, or used for documentation. The persistent memory is automatically used by Claude Code across conversations.

## Usage

When working on this project, Claude Code will:
- Read this directory's CLAUDE.md and memory files for context
- Update the persistent memory system as new information is learned
- Follow the development workflow documented in `soul.md` and `CLAUDE.md`

## Sync Note

This directory can be committed to version control to share Claude Code context with other collaborators. The persistent memory at `~/.claude/` remains user-specific and local.
