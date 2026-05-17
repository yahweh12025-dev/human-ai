---
name: Obsidian Integration
description: Second brain connectivity via obsidian-vault
type: project
---

The Claude Code instance is connected to the user's Obsidian vault at:

`/home/yahwehatwork/obsidian-vault/`

This vault serves as a persistent, linked knowledge base. Claude can:
- Write notes directly to the vault directory
- Read existing notes for context retrieval
- Query by keyword by scanning markdown files
- Create backlinks by referencing note titles in `[[...]]` syntax

The vault contains existing notes in directories like Memory/, Hermes/, HumanAI/, etc., providing rich context for the Human-AI project.

Integration configured in `apps/claude-code/config.json`. The vault is used as a second brain for storing research findings, project decisions, agent outputs, and long-term knowledge.
