import os
from typing import Dict, Any

class AdaptiveRouter:
    def __init__(self):
        # Define tasks that MUST go through the browser
        self.browser_triggers = [
            'login', 'dashboard', 'auth', 'scrape', 'dynamic', 
            'authenticated', 'private', 'interactive', 'visual'
        ]
        # Define tasks that are BETTER via API
        self.api_triggers = [
            'status', 'version', 'simple query', 'ping', 'fast check'
        ]

    def route_task(self, task_description: str) -> str:
        desc = task_description.lower()
        
        # 1. Force Browser for sensitive/complex tasks
        if any(trigger in desc for trigger in self.browser_triggers):
            return "browser"
            
        # 2. Use API for simple tasks
        if any(trigger in desc for trigger in self.api_triggers):
            return "api"
            
        # 3. Default to Browser for safety and cost (current v1.7 philosophy)
        return "browser"

# Example Usage
if __name__ == "__main__":
    router = AdaptiveRouter()
    print(f"Task 'Login to portal' -> {router.route_task('Login to portal')}")
    print(f"Task 'Check API status' -> {router.route_task('Check API status')}")
    print(f"Task 'Research new trends' -> {router.route_task('Research new trends')}")
