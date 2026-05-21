import json
import os

TODO_PATH = "/home/yahwehatwork/human-ai/infrastructure/configs/todo.json"
SWARM_PATH = "/home/yahwehatwork/human-ai/infrastructure/configs/stqueue.json"

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def main():
    todo = load_json(TODO_PATH)
    swarm = load_json(SWARM_PATH)
    
    if todo is None or swarm is None:
        print("Error: Missing todo.json or stqueue.json")
        return

    # 1. Cleanup Swarm Queue: Remove completed tasks from 'completed' and 'failed' 
    # (or move them to a history file if desired, but user said "remove all that have been completed")
    swarm['completed'] = []
    swarm['failed'] = []
    
    # 2. Import Pending from Todo
    # Filter out duplicates by task content
    existing_tasks = {t['task'] for t in swarm['queue']}
    
    # Handle 'pending' list (strings)
    for item in todo.get('pending', []):
        if isinstance(item, str) and item not in existing_tasks:
            swarm['queue'].append({
                "id": f"T{len(swarm['queue']) + 100}",
                "task": item,
                "agent": "Researcher", # Default, will be refined by researcher logic
                "priority": 3,
                "status": "pending",
                "pow_file": "pending_verification"
            })

    # Handle 'in_progress' list (objects)
    for item in todo.get('in_progress', []):
        content = item.get('content', '')
        if content and content not in existing_tasks:
            swarm['queue'].append({
                "id": item.get('id', f"T{len(swarm['queue']) + 200}"),
                "task": content,
                "agent": item.get('assigned_to', 'Researcher'),
                "priority": 2,
                "status": "pending",
                "pow_file": "pending_verification"
            })

    save_json(SWARM_PATH, swarm)
    print(f"Synced todo.json to stqueue.json. Total queue: {len(swarm['queue'])}")

if __name__ == "__main__":
    main()
