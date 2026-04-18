
import os
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
from hermes_tools import read_file, write_file

class DocumentationScribe:
    """
    DocumentationScribe: Automatically updates swarm documentation.
    Maintains ROADMAP.md and README.md to reflect current system state.
    """
    def __init__(self, repo_root: str = "/home/ubuntu/human-ai"):
        self.repo_root = Path(repo_root)
        self.roadmap_path = self.repo_root / "ROADMAP.md"
        self.readme_path = self.repo_root / "README.md"

    async def update_roadmap(self, completed_tasks: List[str], new_tasks: List[str] = None):
        """
        Marks tasks as completed in ROADMAP.md and adds new ones.
        """
        print("📝 [Scribe] Updating ROADMAP.md...")
        try:
            content = read_file(str(self.roadmap_path))['content']
            lines = content.split('\n')
            
            # Mark completed tasks
            for i, line in enumerate(lines):
                for task in completed_tasks:
                    if task.lower() in line.lower() and "- [ ]" in line:
                        lines[i] = line.replace("- [ ]", "- [x]")
            
            # Add new tasks (simplified append to Phase 3)
            if new_tasks:
                # Find Phase 3 section
                for i, line in enumerate(lines):
                    if "Phase 3" in line:
                        insert_pos = i + 1
                        for nt in new_tasks:
                            lines.insert(insert_pos, f"- [ ] **{nt}**")
                            insert_pos += 1
                        break
            
            write_file(str(self.roadmap_path), "\n".join(lines))
            return {"status": "success", "updated": True}
        except Exception as e:
            print(f"❌ [Scribe] Roadmap update failed: {e}")
            return {"status": "error", "error": str(e)}

    async def log_achievement(self, achievement: str):
        """
        Adds a recent achievement to the README.md.
        """
        print("📝 [Scribe] Logging achievement to README.md...")
        try:
            content = read_file(str(self.readme_path))['content']
            timestamp = datetime.now().strftime("%Y-%m-%d")
            entry = f"- **{timestamp}**: {achievement}"
            
            # Find a 'Recent Updates' or 'Achievements' section
            if "## Recent Updates" in content:
                parts = content.split("## Recent Updates")
                updated_content = parts[0] + "## Recent Updates\n" + entry + "\n" + parts[1]
            else:
                updated_content = content + "\n\n## Recent Updates\n" + entry
                
            write_file(str(self.readme_path), updated_content)
            return {"status": "success"}
        except Exception as e:
            print(f"❌ [Scribe] README update failed: {e}")
            return {"status": "error", "error": str(e)}

    async def close(self):
        pass
