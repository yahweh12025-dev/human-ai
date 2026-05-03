
import os
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

class DocumentationScribe:
    """
    DocumentationScribe: Automatically updates swarm documentation.
    Maintains ROADMAP.md and README.md to reflect current system state.
    """
    def __init__(self, repo_root: str = None):
        if repo_root is None:
            from pathlib import Path
            import os
            PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
            WORK_DIR = os.getenv("WORK_DIR", str(PROJECT_ROOT))
            repo_root = WORK_DIR
        self.repo_root = Path(repo_root)
        self.roadmap_path = self.repo_root / "ROADMAP.md"
        self.readme_path = self.repo_root / "README.md"

    async def update_roadmap(self, completed_tasks: List[str], new_tasks: List[str] = None):
        """
        Marks tasks as completed in ROADMAP.md and adds new ones.
        """
        print("📝 [Scribe] Updating ROADMAP.md...")
        try:
            if not self.roadmap_path.exists():
                return {"status": "error", "error": "ROADMAP.md not found"}
                
            with open(self.roadmap_path, 'r') as f:
                content = f.read()
                
            lines = content.split('\n')
            
            # Mark completed tasks
            for i, line in enumerate(lines):
                for task in completed_tasks:
                    if task.lower() in line.lower() and "- [ ]" in line:
                        lines[i] = line.replace("- [ ]", "- [x]")
            
            # Add new tasks (simplified append to Phase 3)
            if new_tasks:
                for i, line in enumerate(lines):
                    if "Phase 3" in line:
                        insert_pos = i + 1
                        for nt in new_tasks:
                            lines.insert(insert_pos, f"- [ ] **{nt}**")
                            insert_pos += 1
                        break
            
            with open(self.roadmap_path, 'w') as f:
                f.write("\n".join(lines))
                
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
            if not self.readme_path.exists():
                # Create a basic README if it doesn't exist
                with open(self.readme_path, 'w') as f:
                    f.write("# Human-AI Swarm\n\n")
                
            with open(self.readme_path, 'r') as f:
                content = f.read()
                
            timestamp = datetime.now().strftime("%Y-%m-%d")
            entry = f"- **{timestamp}**: {achievement}"
            
            if "## Recent Updates" in content:
                parts = content.split("## Recent Updates")
                updated_content = parts[0] + "## Recent Updates\n" + entry + "\n" + parts[1]
            else:
                updated_content = content + "\n\n## Recent Updates\n" + entry
                
            with open(self.readme_path, 'w') as f:
                f.write(updated_content)
                
            return {"status": "success"}
        except Exception as e:
            print(f"❌ [Scribe] README update failed: {e}")
            return {"status": "error", "error": str(e)}

    async def close(self):
        pass
