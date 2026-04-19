#!/usr/bin/env python3
"""
Outcome Scribe: Automatically updates ROADMAP.md and README.md 
when new SUCCESS entries are added to OUTCOME_LOG.md
"""
import os
import re
import time
from datetime import datetime
from pathlib import Path

class OutcomeScribe:
    def __init__(self):
        self.base_path = Path("/home/ubuntu/human-ai")
        self.outcome_log = self.base_path / "OUTCOME_LOG.md"
        self.roadmap_file = self.base_path / "ROADMAP.md"
        self.readme_file = self.base_path / "README.md"
        self.last_check = self._get_last_timestamp()
        
    def _get_last_timestamp(self) -> float:
        """Get the timestamp of the last SUCCESS entry we've processed."""
        # Try to read from a state file
        state_file = self.base_path / ".outcome_scribe_state"
        if state_file.exists():
            try:
                return float(state_file.read_text().strip())
            except:
                pass
        # If no state file, return 0 to process all entries on first run
        return 0
    
    def _save_last_timestamp(self, timestamp: float):
        """Save the timestamp of the last SUCCESS entry we've processed."""
        state_file = self.base_path / ".outcome_scribe_state"
        state_file.write_text(str(timestamp))
    
    def _extract_timestamp_from_entry(self, entry: str) -> float:
        """Extract timestamp from a SUCCESS entry."""
        timestamp_match = re.search(r'\*\*Timestamp\*\*: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?)', entry)
        if timestamp_match:
            try:
                dt = datetime.fromisoformat(timestamp_match.group(1))
                return dt.timestamp()
            except:
                pass
        return 0
    
    def _get_new_success_entries(self) -> list:
        """Get all SUCCESS entries newer than our last check."""
        if not self.outcome_log.exists():
            return []
        
        content = self.outcome_log.read_text()
        # Split by SUCCESS entries
        entries = re.split(r'(?=^## ✅ SUCCESS:)', content, flags=re.MULTILINE)
        
        new_entries = []
        for entry in entries:
            if entry.strip().startswith('## ✅ SUCCESS:'):
                timestamp = self._extract_timestamp_from_entry(entry)
                if timestamp > self.last_check:
                    new_entries.append((timestamp, entry))
        
        # Sort by timestamp
        new_entries.sort(key=lambda x: x[0])
        return new_entries
    
    def _extract_task_id_from_entry(self, entry: str) -> str:
        """Extract task ID from a SUCCESS entry if available."""
        # Look for patterns like "Task ID: xxx-1" or "Task ID xxx-1"
        task_id_match = re.search(r'Task\s+ID[\s:]+([^\n]+)', entry, re.IGNORECASE)
        if task_id_match:
            return task_id_match.group(1).strip()
        return ""
    
    def _update_roadmap(self, entry: str):
        """Update ROADMAP.md based on the SUCCESS entry."""
        # Extract what was completed from the entry
        title_match = re.search(r'## ✅ SUCCESS: (.+)', entry)
        if not title_match:
            return
            
        success_title = title_match.group(1).strip()
        
        # Map common success titles to roadmap items
        roadmap_mappings = {
            "Omni-Model LLM Router Expansion Completed": "**- [x] Omni-Model Router Expansion**: Extend Hybrid Router to include Perplexity (Search) and Claude (Reasoning) via browser-first automation.",
            "Outcome Journal Skill": "**- [x] Outcome Journal Skill**: Create a skill that logs the outcomes of tasks and features to OUTCOME_LOG.md for transparency and human-AI collaboration.",
            "Memory Bridge Implementation": "**- [x] Memory Bridge Implementation**: Create a synchronization pipeline to distill \"wisdom\" and key decisions from Hermes' daily memory into the Swarm's global MEMORY.md",
            "ConverterAgent": "**- [x] ConverterAgent**: Develop `ConverterAgent` for multi-format transformation (PDF, Word, PPTX, JSON $\\leftrightarrow$ TXT, MD).",
            "OCRAgent": "**- [x] OCRAgent**: Develop `OCRAgent` for visual text extraction and layout analysis.",
            "Documentation-Scribe Agent": "**- [x] Documentation-Scribe Agent**: Automatically updates README/ROADMAP and generates technical docs for new features.",
            "Perplexity Browser Agent implemented": "**- [x] Perplexity Browser Agent implemented**: Integrated browser-based Perplexity (Search) with rate-limit handling.",
            "Claude Browser Agent implemented": "**- [x] Claude Browser Agent implemented**: Integrated browser-based Claude (Reasoning) with rate-limit handling.",
            "Omni-Model LLM Router expanded to 4 models": "**- [x] Omni-Model LLM Router expanded to 4 models**: Expanded HybridLLMRouter to route between Gemini, DeepSeek, Perplexity, and Claude",
            "Update HybridLLMRouter to handle Omni-Model routing": "**- [x] Update HybridLLMRouter to handle Omni-Model routing**: Updated HybridLLMRouter to handle Omni-Model routing (DeepSeek, Gemini, Perplexity, Claude)",
            "Integrate Omni-Router into core Agent Swarm loop": "**- [x] Integrate Omni-Router into core Agent Swarm loop**: Integrated Omni-Router into the core Agent Swarm loop (AntFarm Orchestrator)"
        }
        
        # Check if this success maps to a roadmap item
        for key, roadmap_item in roadmap_mappings.items():
            if key.lower() in success_title.lower():
                self._mark_roadmap_item_complete(roadmap_item)
                return
    
    def _mark_roadmap_item_complete(self, roadmap_item: str):
        """Mark a specific roadmap item as complete."""
        if not self.roadmap_file.exists():
            return
            
        content = self.roadmap_file.read_text()
        
        # Look for the item in the roadmap (both completed and pending sections)
        patterns = [
            rf'- \[ \] {re.escape(roadmap_item)}',  # Pending item
            rf'- \[\s\] {re.escape(roadmap_item)}',  # Pending item with space
        ]
        
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                # Replace pending with completed
                content = re.sub(
                    pattern, 
                    f'- [x] {roadmap_item}', 
                    content, 
                    flags=re.IGNORECASE
                )
                self.roadmap_file.write_text(content)
                print(f"✅ Marked roadmap item complete: {roadmap_item[:50]}...")
                return
        
        # If not found in pending, check if it's already completed
        completed_pattern = rf'- \[x\] {re.escape(roadmap_item)}'
        if not re.search(completed_pattern, content, re.IGNORECASE):
            # If not found anywhere, add it to the completed section
            # Find the completed section and add it there
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if '## Phase' in line and 'COMPLETED' in line:
                    # Insert after this section header
                    lines.insert(i+1, f'- [x] {roadmap_item}')
                    self.roadmap_file.write_text('\n'.join(lines))
                    print(f"✅ Added completed roadmap item: {roadmap_item[:50]}...")
                    return
    
    def _update_readme(self, entry: str):
        """Update README.md based on the SUCCESS entry."""
        # Extract what was completed from the entry
        title_match = re.search(r'## ✅ SUCCESS: (.+)', entry)
        if not title_match:
            return
            
        success_title = title_match.group(1).strip()
        timestamp_match = re.search(r'\*\*Timestamp\*\*: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?)', entry)
        timestamp_str = timestamp_match.group(1) if timestamp_match else datetime.now().isoformat()
        
        # Format date for README
        try:
            dt = datetime.fromisoformat(timestamp_str)
            formatted_date = dt.strftime('%Y-%m-%d')
        except:
            formatted_date = datetime.now().strftime('%Y-%m-%d')
        
        # Create the update entry
        update_entry = f"- **{formatted_date}**: {success_title}"
        
        # Add to README under Recent Updates
        if self.readme_file.exists():
            content = self.readme_file.read_text()
            
            # Find the Recent Updates section
            if '## Recent Updates' in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() == '## Recent Updates':
                        # Insert after the header
                        lines.insert(i+2, update_entry)
                        self.readme_file.write_text('\n'.join(lines))
                        print(f"✅ Updated README with: {update_entry}")
                        return
            else:
                # If no Recent Updates section, add it
                with open(self.readme_file, 'a') as f:
                    f.write(f'\n## Recent Updates\n{update_entry}\n')
                print(f"✅ Added Recent Updates section to README with: {update_entry}")
    
    def run(self):
        """Check for new SUCCESS entries and update documents."""
        print("🔍 Checking for new SUCCESS entries...")
        new_entries = self._get_new_success_entries()
        
        if not new_entries:
            print("✅ No new SUCCESS entries found.")
            return
        
        print(f"📋 Found {len(new_entries)} new SUCCESS entry(ies) to process.")
        
        for timestamp, entry in new_entries:
            print(f"\n📝 Processing entry from {datetime.fromtimestamp(timestamp)}:")
            print(f"   {entry[:100]}...")
            
            # Update roadmap and readme
            self._update_roadmap(entry)
            self._update_readme(entry)
            
            # Update our last check timestamp
            self._save_last_timestamp(timestamp)
        
        print("\n✅ Outcome Scribe completed!")

if __name__ == "__main__":
    scribe = OutcomeScribe()
    scribe.run()