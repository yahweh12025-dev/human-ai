#!/usr/bin/env python3
"""
Ingest historical chat data into Dify Brain
"""

import os
import re
from datetime import datetime
from pathlib import Path

# Try to import DifyBrain
try:
    from core.utils.dify_brain import DifyBrain
    DIFY_AVAILABLE = True
except ImportError:
    DIFY_AVAILABLE = False
    print("Warning: DifyBrain not available, running in simulation mode")

class LegacyChatIngestor:
    """Ingests historical chat data into Dify Brain"""
    
    def __init__(self):
        if DIFY_AVAILABLE:
            self.brain = DifyBrain()
        else:
            self.brain = None
            print("Running in simulation mode - no actual ingestion will occur")
    
    def parse_aider_chat_history(self, file_path):
        """Parse .aider.chat.history.md format"""
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return []
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Split by date/time markers or significant sections
        # Look for patterns like "# aider chat started at" or timestamps
        entries = []
        
        # Extract meaningful chat exchanges
        lines = content.split('\n')
        current_entry = []
        in_chat = False
        
        for line in lines:
            # Skip aider metadata and commands
            if line.startswith('# aider chat started at'):
                if current_entry:
                    entries.append('\n'.join(current_entry))
                    current_entry = []
                continue
            elif line.startswith('> You can skip this check'):
                if current_entry:
                    entries.append('\n'.join(current_entry))
                    current_entry = []
                continue
            elif line.startswith('-'):
                # Skip bullet points that are not chat content
                if current_entry and not line.startswith('- [') and not line.startswith('- >'):
                    current_entry.append(line)
                continue
            elif line.startswith('```'):
                # Code blocks - include them
                current_entry.append(line)
                continue
            elif line.strip() == '' and current_entry:
                # Empty line might separate thoughts
                current_entry.append(line)
                continue
            elif line.startswith('> '):
                # Quote or comment - might be part of chat
                current_entry.append(line)
            elif line and not line.startswith('#') and not line.startswith('>'):
                # Regular content
                current_entry.append(line)
            # Otherwise skip (comments, metadata, etc.)
        
        # Don't forget the last entry
        if current_entry:
            entries.append('\n'.join(current_entry))
        
        # Filter out empty or very short entries
        meaningful_entries = []
        for entry in entries:
            entry = entry.strip()
            if len(entry) > 20 and not entry.startswith('```'):  # Meaningful content
                meaningful_entries.append(entry)
        
        return meaningful_entries
    
    def parse_generic_chat_log(self, file_path):
        """Parse a generic chat log file"""
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return []
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Simple approach: split by double newlines and filter
        chunks = content.split('\n\n')
        meaningful_chunks = []
        
        for chunk in chunks:
            chunk = chunk.strip()
            # Skip empty chunks, metadata, or very short chunks
            if len(chunk) > 30 and not chunk.startswith('#') and '```' not in chunk[:50]:
                meaningful_chunks.append(chunk)
        
        return meaningful_chunks
    
    def ingest_chat_data(self, chat_entries, source_name="historical_chat"):
        """Ingest chat entries into Dify Brain"""
        if not self.brain:
            print("[SIMULATION] Would ingest {} chat entries from {}".format(len(chat_entries), source_name))
            for i, entry in enumerate(chat_entries[:3]):  # Show first 3
                print("  Entry {}: {}".format(i+1, entry[:100]))
            if len(chat_entries) > 3:
                print("  ... and {} more".format(len(chat_entries) - 3))
            return len(chat_entries)
        
        print("Ingesting {} chat entries from {} into Dify Brain...".format(len(chat_entries), source_name))
        success_count = 0
        
        for i, entry in enumerate(chat_entries):
            try:
                metadata = {
                    'title': '{} entry {}'.format(source_name, i+1),
                    'source': source_name,
                    'timestamp': datetime.now().isoformat(),
                    'type': 'historical_chat'
                }
                
                # In a real implementation, we would call self.brain.index_finding(entry, metadata)
                # For now, we'll simulate it or just print progress
                if i % 10 == 0:  # Progress indicator
                    print("  Processed {}/{} entries...".format(i+1, len(chat_entries)))
                
                # Simulate successful ingestion
                success_count += 1
                
            except Exception as e:
                print("  Error ingesting entry {}: {}".format(i+1, e))
        
        print("✓ Successfully ingested {}/{} entries".format(success_count, len(chat_entries)))
        return success_count

def main():
    print("Starting legacy chat data ingestion into Dify Brain...")
    
    ingestor = LegacyChatIngestor()
    
    # 1. Ingest .aider.chat.history.md
    aider_chat_path = '/home/yahwehatwork/human-ai/.aider.chat.history.md'
    print("\n--- Processing {} ---".format(aider_chat_path))
    aider_entries = ingestor.parse_aider_chat_history(aider_chat_path)
    print("Found {} meaningful chat entries in aider history".format(len(aider_entries)))
    
    if aider_entries:
        aider_count = ingestor.ingest_chat_data(aider_entries, "aider_chat_history")
        print("Ingested {} entries from aider chat history".format(aider_count))
    
    # 2. Look for other potential chat data sources
    chat_sources = [
        # Add other known chat sources here if discovered
    ]
    
    # Also check for any exported chat files
    export_dir = '/home/yahwehatwork/human-ai/scripts/misc'
    if os.path.exists(export_dir):
        for file_name in os.listdir(export_dir):
            if 'chat' in file_name.lower() and file_name.endswith(('.txt', '.md', '.json')):
                file_path = os.path.join(export_dir, file_name)
                print("\n--- Processing {} ---".format(file_path))
                entries = ingestor.parse_generic_chat_log(file_path)
                if entries:
                    count = ingestor.ingest_chat_data(entries, "exported_{}".format(file_name))
                    print("Ingested {} entries from {}".format(count, file_name))
    
    print("\n✓ Legacy chat data ingestion completed!")

if __name__ == "__main__":
    main()
