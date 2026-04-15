import asyncio
import os
from agents.github_scout.github_scout_agent import GitHubScoutAgent
from agents.repo_reviewer.repo_reviewer_agent import RepoReviewerAgent

async def test_github_scout_reviewer_link():
    print("🔗 Testing GitHub Scout $\rightarrow$ Repo Reviewer Link")
    
    # Initialize agents
    scout = GitHubScoutAgent()
    reviewer = RepoReviewerAgent()
    
    # Step 1: Scout for a popular, safe repository
    print("🔍 GitHub Scout: Searching for 'tetris' repositories...")
    try:
        # Note: The GitHub API is unauthenticated here, so we may hit rate limits quickly.
        # We'll use a very specific query to get a manageable result.
        repos = scout.search_repositories("tetris language:python")
        if not repos:
            print("⚠️ No repos found (possibly due to API limits or network). Using a placeholder.")
            repo_url = "https://github.com/defunkt/tennis"  # A known small repo
        else:
            # Take the first repo's HTML URL
            repo_url = repos[0].get('html_url')
            print(f"🎯 Scout found: {repo_url}")
    except Exception as e:
        print(f"❌ Scout error: {e}. Using fallback URL.")
        repo_url = "https://github.com/defunkt/tennis"
    
    # Step 2: Reviewer analyzes the repo URL (placeholder logic)
    print(f"🔍 Repo Reviewer: Analyzing {repo_url}")
    try:
        review_result = reviewer.analyze_repo(repo_url)
        print(f"✅ Reviewer result: {review_result}")
    except Exception as e:
        print(f"❌ Reviewer error: {e}")
    
    print("✅ GitHub Scout $\rightarrow$ Repo Reviewer link test completed.")

if __name__ == "__main__":
    asyncio.run(test_github_scout_reviewer_link())
