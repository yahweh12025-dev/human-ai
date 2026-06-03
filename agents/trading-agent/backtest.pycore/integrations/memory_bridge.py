import os
import re
from datetime import datetime

# Configuration - Strictly mapped to human-ai root
from pathlib import Path
import os
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORK_DIR = os.getenv("WORK_DIR", str(PROJECT_ROOT))
MEMORY_DIR = Path(WORK_DIR) / "memory"
GLOBAL_MEMORY_PATH = Path(WORK_DIR) / "MEMORY.md"

def distill_wisdom_offline(content):
    """
    Distills wisdom from raw logs using semantic pattern matching.
    STRICTLY NO API CALLS.
    """
    # High-signal patterns for wisdom extraction
    patterns = {
        "DECISION": [r"(?i)I decided to\s*(.*)", r"(?i)Decision:\s*(.*)", r"(?i)resolved to\s*(.*)"],
        "LESSON": [r"(?i)learned that\s*(.*)", r"(?i)Lesson:\s*(.*)", r"(?i)discovered that\s*(.*)", r"(?i)avoid\s*(.*)"],
        "FACT": [r"(?i)Fact:\s*(.*)", r"(?i)it is confirmed that\s*(.*)", r"(?i)verified that\s*(.*)"],
        "INSIGHT": [r"(?i)Insight:\s*(.*)", r"(?i)realized that\s*(.*)", r"(?i)observation:\s*(.*)"]
    }
    
    wisdom_atoms = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        for category, regexes in patterns.items():
            for regex in regexes:
                match = re.search(regex, line)
                if match:
                    # Capture the extracted part or the whole line if it's a marker
                    detail = match.group(1) if match.groups() else line
                    wisdom_atoms.append(f"[{category}] {detail.strip()}")
                    break 
                    
    return wisdom_atoms

def sync_to_global_memory(atoms):
    """
    Merges distilled atoms into GLOBAL MEMORY.md.
    Ensures zero duplicates.
    """
    if not atoms:
        return False

    # Ensure global memory exists
    if not os.path.exists(GLOBAL_MEMORY_PATH):
        with open(GLOBAL_MEMORY_PATH, 'w') as f:
            f.write("# 🧠 SWARM GLOBAL MEMORY\n\nThis file contains distilled wisdom and key decisions.\n\n")

    with open(GLOBAL_MEMORY_PATH, 'r') as f:
        current_content = f.read()

    unique_atoms = []
    for atom in atoms:
        # Deduplication check: only add if the core text isn't already present
        if atom not in current_content:
            unique_atoms.append(atom)

    if unique_atoms:
        with open(GLOBAL_MEMORY_PATH, 'a') as f:
            f.write(f"\n## Sync Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            for atom in unique_atoms:
                f.write(f"- {atom}\n")
        return True
    return False

def run_memory_bridge():
    """
    Executes the offline synchronization pipeline.
    """
    print("🚀 Initializing Offline Memory Bridge...")
    
    if not os.path.exists(MEMORY_DIR):
        print(f"❌ Error: Memory directory {MEMORY_DIR} not found.")
        return

    files = sorted([f for f in os.listdir(MEMORY_DIR) if f.endswith('.md')])
    print(f"📂 Scanning {len(files)} daily logs for wisdom...")
    
    total_synced = 0
    for file in files:
        path = os.path.join(MEMORY_DIR, file)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            wisdom = distill_wisdom_offline(content)
            if wisdom:
                if sync_to_global_memory(wisdom):
                    print(f"✅ {file}: Synced {len(wisdom)} atoms.")
                    total_synced += len(wisdom)
                else:
                    print(f"⚪ {file}: No new unique wisdom.")
            else:
                print(f"❌ {file}: No wisdom patterns found.")
        except Exception as e:
            print(f"⚠️ Error processing {file}: {e}")

    print(f"\n✨ Sync Complete. Total unique atoms added: {total_synced}")

if __name__ == "__main__":
    run_memory_bridge()
