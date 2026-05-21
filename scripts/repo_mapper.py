import os
import json
import subprocess
from datetime import datetime

REPO_ROOT = "/home/yahwehatwork/human-ai"
OUTPUT_FILE = "/home/yahwehatwork/human-ai/REPO_TREE.md"
METADATA_FILE = "/home/yahwehatwork/human-ai/REPO_METADATA.json"

def generate_tree(path, indent=""):
    tree = ""
    try:
        entries = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
        for i, entry in enumerate(entries):
            if entry.startswith(('.git', '__pycache__', 'node_modules', '.next')):
                continue
            
            full_path = os.path.join(path, entry)
            is_last = (i == len(entries) - 1)
            marker = "└── " if is_last else "├── "
            
            tree += f"{indent}{marker}{entry}\n"
            
            if os.path.isdir(full_path):
                new_indent = indent + ("    " if is_last else "│   ")
                tree += generate_tree(full_path, new_indent)
    except PermissionError:
        tree += f"{indent}└── [Permission Denied]\n"
    return tree

def main():
    print(f"Mapping repository: {REPO_ROOT}")
    tree_content = generate_tree(REPO_ROOT)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# Human-AI Repository Tree\n\n")
        f.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("```text\n")
        f.write(f".\n{tree_content}")
        f.write("```\n")
    
    metadata = {
        "last_update": datetime.now().isoformat(),
        "root": REPO_ROOT,
        "status": "synced"
    }
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Successfully updated {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
