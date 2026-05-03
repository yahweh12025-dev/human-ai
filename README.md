# Human-AI Directory

[View the Human-AI Source Code on GitHub](https://github.com/yahweh12025-dev/human-ai)

This directory serves as the interface between human operations and AI agent systems in the repository. It contains minimal loose files to maintain clarity while supporting the automated workflows.

## Contents

- `.env` - Environment variables (not tracked by Git for security)
- `.gitignore` - Git ignore rules to prevent tracking of unnecessary files
- `README.md` - This documentation file
- `repo_tree.txt` - Continuously updated directory tree view of the repository

## Purpose

This directory maintains a clean separation between:
- **Human-operated files**: Configuration, documentation, and manual overrides
- **AI-agent operated files**: Code, scripts, data, and automated outputs stored in appropriate subdirectories

## Tree File

The `repo_tree.txt` file is automatically updated to reflect the current repository structure, excluding:
- Dependency directories (`node_modules`, `__pycache__`, `.venv*`, etc.)
- Configuration and cache directories (`.git`, `.hermes`, `.browser-profile`, etc.)
- Output and temporary directories (`output`, `test_scripts`, `downloads`, etc.)
- Large data and media directories

This provides a clear, navigable view of the active project structure for both humans and agents.

## Maintenance

To update the tree view manually:
```bash
~/update_tree.sh
```

The script generates an ASCII tree view filtered to show only relevant project directories and files.

## Subdirectory Organization

Files in the repository should generally be placed in these locations:
- `agents/` - AI agent implementations
- `core/` - Shared utilities and core systems
- `scripts/` - Automation and utility scripts
- `tests/` - Test files
- `docs/` - Documentation
- `obsidian/` - Knowledge base and notes
- `memory/` - Long-term memory and logs
- `infrastructure/configs/` - Configuration files
- `projects/` - Project-specific work
- `misc/` - Miscellaneous files that don't fit other categories

Loose files in the repository root should be avoided except for the four specified in this directory.