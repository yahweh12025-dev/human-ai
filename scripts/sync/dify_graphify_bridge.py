#!/usr/bin/env python3
"""
Sync Pipeline between Outcome Journal, Dify RAG, and Graphify KG
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
import hashlib

# Import the DifyBrain if available
try:
    from core.utils.dify_brain import DifyBrain
    DIFY_AVAILABLE = True
except ImportError:
    DIFY_AVAILABLE = False
    print("Warning: DifyBrain not available, running in limited mode")

class OutcomeJournalReader:
    """Reads and parses the Outcome Journal"""
    
    def __init__(self, journal_path):
        self.journal_path = Path(journal_path)
        self.state_file = self.journal_path.parent / ".outcome_sync_state"
        self.last_processed = self._load_state()
    
    def _load_state(self):
        """Load the last processed timestamp"""
        if self.state_file.exists():
            try:
                return float(self.state_file.read_text().strip())
            except:
                return 0.0
        return 0.0
    
    def _save_state(self, timestamp):
        """Save the last processed timestamp"""
        self.state_file.write_text(str(timestamp))
    
    def get_new_entries(self):
        """Get new SUCCESS entries from the outcome journal"""
        if not self.journal_path.exists():
            return []
        
        content = self.journal_path.read_text()
        # Split by SUCCESS entries
        import re
        entries = re.split(r'(?=^## ✅ SUCCESS:)', content, flags=re.MULTILINE)
        
        new_entries = []
        for entry in entries:
            if entry.strip().startswith('## ✅ SUCCESS:'):
                # Extract timestamp
                timestamp_match = re.search(r'\*\*Timestamp\*\*: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)', entry)
                if timestamp_match:
                    try:
                        dt = datetime.fromisoformat(timestamp_match.group(1))
                        timestamp = dt.timestamp()
                        if timestamp > self.last_processed:
                            new_entries.append((timestamp, entry.strip()))
                    except:
                        pass
        
        # Sort by timestamp
        new_entries.sort(key=lambda x: x[0])
        return new_entries

class GraphifyKGWriter:
    """Writes to Graphify Knowledge Graph"""
    
    def __init__(self, graphify_path):
        self.graphify_path = Path(graphify_path)
        self.kb_path = self.graphify_path / "graphify-out"
        self.kb_path.mkdir(exist_ok=True)
    
    def add_finding(self, title, content, source="outcome_journal"):
        """Add a finding to the Graphify knowledge graph"""
        # Create a simple markdown file for the finding
        # In a real implementation, this would use Graphify's API
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')
        if not safe_title:
            safe_title = f"finding_{int(time.time())}"
        
        # Add to wiki or create a simple note
        wiki_dir = self.kb_path / "wiki"
        wiki_dir.mkdir(exist_ok=True)
        
        # Create a simple note file
        note_file = wiki_dir / f"{safe_title}.md"
        note_content = f"""# {title}

**Source**: {source}
**Timestamp**: {datetime.now().isoformat()}
**Content**:
{content}

---
*Auto-synced from Outcome Journal via dify-graphify-bridge*
"""
        note_file.write_text(note_content)
        return str(note_file)

class DifyBrainEnricher:
    """Enriches content using Dify Brain (RAG)"""
    
    def __init__(self):
        if DIFY_AVAILABLE:
            self.brain = DifyBrain()
        else:
            self.brain = None
    
    def enrich(self, query):
        """Query Dify Brain for enrichment"""
        if not self.brain:
            return f"[Dify not available] Query: {query}"
        
        try:
            result = self.brain.query(query)
            return result
        except Exception as e:
            return f"[Dify error] {str(e)}"

def main():
    print("Starting dify-graphify-bridge sync pipeline...")
    
    # Initialize components
    journal_path = "/home/yahwehatwork/human-ai/docs/misc/outcome_log.md"
    graphify_path = "/home/yahwehatwork/human-ai/infrastructure/tools/graphify"
    
    journal_reader = OutcomeJournalReader(journal_path)
    graphify_writer = GraphifyKGWriter(graphify_path)
    dify_enricher = DifyBrainEnricher()
    
    # Get new entries
    new_entries = journal_reader.get_new_entries()
    
    if not new_entries:
        print("No new entries to process.")
        return 0
    
    print(f"Found {len(new_entries)} new entry(ies) to process.")
    
    processed_count = 0
    for timestamp, entry in new_entries:
        print(f"\nProcessing entry from {datetime.fromtimestamp(timestamp)}:")
        
        # Extract the success title and content
        lines = entry.split('\n')
        title_line = lines[0] if lines else ""
        title = title_line.replace('## ✅ SUCCESS:', '').strip()
        
        # Get the result/content (look for lines after "Result:" or the substantive content)
        content_lines = []
        in_content = False
        for line in lines[1:]:
            if line.strip().startswith('Result:'):
                in_content = True
                content_lines.append(line.replace('Result:', '').strip())
            elif in_content and line.strip() and not line.startswith('##') and not line.startswith('Note:'):
                content_lines.append(line.strip())
            elif line.startswith('Note:'):
                # Include the note as well
                content_lines.append(line.replace('Note:', '').strip())
        
        content = ' '.join(content_lines) if content_lines else entry
        
        if not content.strip():
            content = entry  # Fallback to full entry
        
        print(f"  Title: {title}")
        print(f"  Content preview: {content[:100]}...")
        
        # Enrich with Dify Brain (optional)
        enriched = dify_enricher.enrich(f"What is the significance of: {title}")
        if enriched and not enriched.startswith('['):
            print(f"  Dify enrichment: {enriched[:100]}...")
        
        # Write to Graphify KG
        try:
            wiki_path = graphify_writer.add_finding(title, content, "outcome_journal")
            print(f"  ✓ Added to Graphify: {wiki_path}")
            processed_count += 1
        except Exception as e:
            print(f"  ✗ Failed to add to Graphify: {e}")
    
    # Update state if we processed anything
    if processed_count > 0:
        latest_timestamp = new_entries[-1][0]
        journal_reader._save_state(latest_timestamp)
        print(f"\n✓ Sync completed. Processed {processed_count} entries.")
        print(f"  Last processed timestamp: {datetime.fromtimestamp(latest_timestamp)}")
    else:
        print("\n✓ No entries were successfully processed.")
    
    return 0

if __name__ == "__main__":
    exit(main())
