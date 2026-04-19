#!/usr/bin/env python3
"""
ObsidianAgent: A skill for interacting with a linked Markdown vault (Obsidian style).
Allows agents to store and retrieve structured, linked knowledge.
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

class ObsidianAgent:
    def __init__(self, vault_path: str = "/home/ubuntu/human-ai/swarm_vault"):
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(parents=True, exist_ok=True)

    def write_note(self, title: str, content: str) -> str:
        """Create or update a note in the vault."""
        file_path = self.vault_path / f"{title}.md"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Note '{title}' written to vault."

    def read_note(self, title: str) -> str:
        """Read a note from the vault."""
        file_path = self.vault_path / f"{title}.md"
        if not file_path.exists():
            return f"Note '{title}' not found in vault."
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def find_links(self, title: str) -> List[str]:
        """Find all wiki-links [[Link]] in a note."""
        content = self.read_note(title)
        if "not found" in content:
            return []
        
        # Regex for [[Link]] or [[Link|Alias]]
        links = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)
        return links

    def get_backlinks(self, title: str) -> List[str]:
        """Find all notes that link to this note."""
        backlinks = []
        for file in self.vault_path.glob("*.md"):
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                if f"[[{title}" in content:
                    backlinks.append(file.stem)
        return backlinks

    def query_vault(self, keyword: str) -> List[Dict[str, str]]:
        """Simple keyword search across all notes."""
        results = []
        for file in self.vault_path.glob("*.md"):
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                if keyword.lower() in content.lower():
                    results.append({
                        "title": file.stem,
                        "snippet": content[:100] + "..."
                    })
        return results

if __name__ == "__main__":
    # Basic test
    obs = ObsidianAgent()
    obs.write_note("Swarm-Plan", "The plan is to integrate [[ObsidianAgent]] into the core.")
    obs.write_note("ObsidianAgent", "This is the agent that handles [[Swarm-Plan]] and other notes.")
    
    print("Testing links...")
    print(f"Links in Swarm-Plan: {obs.find_links('Swarm-Plan')}")
    print(f"Backlinks to ObsidianAgent: {obs.get_backlinks('ObsidianAgent')}")
