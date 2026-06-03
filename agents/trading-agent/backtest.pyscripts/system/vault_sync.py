import os
import shutil
from pathlib import Path

# Configuration
REPO_ROOT = Path("/home/yahwehatwork/human-ai/")
VAULT_ROOT = Path("/home/yahwehatwork/Documents/Obsidian Vault")

# Mapping: {Source Folder/File -> Vault Destination Folder}
SYNC_MAP = {
    "docs/": "HumanAI/Docs",
    "memory/": "Memory",
    "agents/trading-agent/high_fidelity_log.md": "HumanAI/Trading/high_fidelity_log.md",
    "agents/trading-agent/README.md": "HumanAI/Trading/README.md",
    "infrastructure/configs/todo.json": "Configs/todo.json",
    "docs/ROADMAP.md": "HumanAI/ROADMAP.md",
    "docs/unified_plan.md": "HumanAI/unified_plan.md",
    "agents/trading-agent/results/": "HumanAI/Trading/Results",
}

def sync_to_vault():
    print("🧠 Synchronizing Human-AI Repo to Obsidian Second Brain...")
    
    for src_path, dst_folder in SYNC_MAP.items():
        full_src = REPO_ROOT / src_path
        
        if not full_src.exists():
            print(f"⚠️ Source not found: {full_src}")
            continue
            
        # Create destination directory
        dest_dir = VAULT_ROOT / dst_folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        if full_src.is_dir():
            # Sync directory contents
            for item in full_src.rglob("*"):
                if item.is_file() and not ".git" in str(item):
                    # Maintain subfolder structure
                    rel_path = item.relative_to(full_src)
                    target_file = dest_dir / rel_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Only copy if file is .md, .txt, .json, .csv or .yaml
                    if item.suffix in ['.md', '.txt', '.json', '.csv', '.yaml']:
                        shutil.copy2(item, target_file)
        else:
            # Sync single file
            shutil.copy2(full_src, dest_dir / full_src.name)
            
    print("✅ Sync Complete. Obsidian Vault updated with latest repo intelligence.")

if __name__ == "__main__":
    sync_to_vault()
