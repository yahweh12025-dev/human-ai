import os
import subprocess
from datetime import datetime, timedelta

def get_git_summary():
    # Get commits from the last 7 days
    since_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    try:
        cmd = f"git log --since={since_date} --pretty=format:'- %s (%an)'"
        output = subprocess.check_output(cmd, shell=True, cwd="/home/ubuntu/human-ai").decode('utf-8')
        return output if output else "No significant activity this week."
    except Exception as e:
        return f"Error fetching git logs: {e}"

def create_github_issue(summary):
    # We use the GitHubScoutAgent's logic or a direct API call via curl
    title = f"Weekly Swarm Summary: {datetime.now().strftime('%Y-%m-%d')}"
    body = f"## Activity Report\n\n{summary}\n\n---\n*Generated automatically by Human-AI Swarm*"
    
    print(f"Creating GitHub Issue: {title}...")
    # Note: In a real environment, we'd use the GH API. 
    # Here we'll write it to a file for the GitHubScoutAgent to push.
    with open("/home/ubuntu/human-ai/weekly_summary.md", "w") as f:
        f.write(f"# {title}\n\n{body}")
    
    print("✅ Summary staged in weekly_summary.md. Ready for GitHubScoutAgent to upload.")

if __name__ == "__main__":
    summary = get_git_summary()
    create_github_issue(summary)
