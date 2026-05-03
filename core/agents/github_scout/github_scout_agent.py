#!/usr/bin/env python3
import os
from pathlib import Path
from playwright.async_api import async_playwright

class GitHubScoutAgent:
    def __init__(self, token=None):
        # Token is kept for compatibility but not used in browser-based search
        self.token = token
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None

    async def start_browser(self):
        if self.pw is not None:
            return
        print("🌐 Initializing browser for GitHub search...")
        self.pw = await async_playwright().start()
        # Use a persistent context? We'll use a temporary one for now.
        user_data_dir = os.path.join(os.getenv("WORK_DIR", "/home/yahwehatwork/human-ai"), "session", "github_profile")
        os.makedirs(user_data_dir, exist_ok=True)
        headless = os.getenv("BROWSER_HEADLESS", "True").lower() == "true"
        self.context = await self.pw.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--disable-blink-features=AutomationControlled'],
        )
        self.page = await self.context.new_page()
        print("✅ Browser for GitHub search initialized")

    async def close(self):
        if self.context:
            await self.context.close()
        if self.pw:
            await self.pw.stop()
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        print("🌐 Browser for GitHub search closed")

    async def search_repositories(self, query):
        """
        Search for repositories on GitHub using the web interface.
        Returns a list of repository dictionaries (name, description, url, etc.)
        """
        print(f"🔍 Searching GitHub for: {query} via browser...")
        try:
            await self.start_browser()
            
            # Navigate to GitHub
            await self.page.goto("https://github.com", wait_until="domcontentloaded")
            await self.page.wait_for_timeout(2000)
            
            # Click the search button or go directly to search
            # We'll fill the search input
            search_input = self.page.get_by_label("Search GitHub")
            await search_input.click()
            await search_input.fill(query)
            await self.page.keyboard.press("Enter")
            
            # Wait for search results to load
            await self.page.wait_for_selector('[data-testid="results-list"]', timeout=10000)
            await self.page.wait_for_timeout(2000)  # Additional wait for results to render
            
            # Extract repository information
            repos = []
            # We'll look for repository items in the search results
            # Each repo is in an element with class 'repo-list-item' or similar
            # We'll use a more generic selector: the div that contains the repo info
            repo_items = await self.page.locator('[data-testid="results-list"] .repo-list-item').all()
            
            for item in repo_items[:10]:  # Limit to first 10 results
                try:
                    # Extract repo name and URL
                    name_element = item.locator('a[data-testid="result-repo-link"]')
                    if await name_element.count() == 0:
                        # Fallback selector
                        name_element = item.locator('h3 a')
                    
                    repo_name = await name_element.inner_text()
                    repo_url = await name_element.get_attribute('href')
                    if repo_url and not repo_url.startswith('http'):
                        repo_url = f"https://github.com{repo_url}"
                    
                    # Extract description
                    desc_element = item.locator('p[data-testid="result-repo-description"]')
                    repo_desc = await desc_element.inner_text() if await desc_element.count() > 0 else ""
                    
                    # Extract language and stars if available
                    lang_element = item.locator('[data-testid="result-repo-language"]')
                    repo_lang = await lang_element.inner_text() if await lang_element.count() > 0 else ""
                    
                    stars_element = item.locator('[data-testid="result-repo-stars"]')
                    repo_stars = await stars_element.inner_text() if await stars_element.count() > 0 else ""
                    
                    repos.append({
                        "name": repo_name.strip(),
                        "description": repo_desc.strip(),
                        "url": repo_url,
                        "language": repo_lang.strip(),
                        "stars": repo_stars.strip()
                    })
                except Exception as e:
                    print(f"⚠️ Error parsing repo item: {e}")
                    continue
            
            print(f"✅ Found {len(repos)} repositories via browser search")
            return repos
        except Exception as e:
            print(f"❌ GitHub search error: {e}")
            return []
        finally:
            # We'll keep the browser open for potential reuse
            # Uncomment the following line if you want to close after each search
            # await self.close()
            pass

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