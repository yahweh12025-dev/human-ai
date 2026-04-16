import requests
import os
from pathlib import Path

class GitHubScoutAgent:
    def __init__(self, token=None):
        self.token = token

    def search_repositories(self, query):
        url = f"https://api.github.com/search/repositories?q={query}"
        headers = {"Authorization": f"token {self.token}"} if self.token else {}
        res = requests.get(url, headers=headers)
        return res.json().get('items', [])

    def analyze_local_repo(self, path: str):
        """Scans the local repo for common smells, missing docs, or inconsistencies."""
        report = []
        root = Path(path)
        
        # 1. Check for .env.example
        if not (root / '.env.example').exists():
            report.append("⚠️ MISSING: .env.example not found. New developers will struggle to setup.")
            
        # 2. Check for README completeness
        readme = root / 'README.md'
        if not readme.exists():
            report.append("⚠️ MISSING: README.md not found.")
        else:
            content = readme.read_text()
            if 'ROADMAP' not in content and 'Installation' not in content:
                report.append("⚠️ WEAK: README.md is missing installation or roadmap sections.")

        # 3. Check for consistency in agent naming
        agents_dir = root / 'agents'
        if agents_dir.exists():
            for agent_dir in agents_dir.iterdir():
                if agent_dir.is_dir():
                    # Check if the agent has a __init__.py or a main agent file
                    files = list(agent_dir.glob('*.py'))
                    if not files:
                        report.append(f"⚠️ EMPTY: {agent_dir.name} has no python files.")
        
        return report if report else ["✅ Repo looks healthy!"]

async def main():
    agent = GitHubScoutAgent()
    print("GitHub Scout Agent active.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
