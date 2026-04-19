import sqlite3
import os

ROADMAP_PATH = "/home/ubuntu/human-ai/ROADMAP.md"
TODO_DB_PATH = "/home/ubuntu/human-ai/todo.db"
OUTPUT_PATH = "/home/ubuntu/human-ai/unified_plan.md"

def get_todo_tasks():
    if not os.path.exists(TODO_DB_PATH):
        return []
    try:
        conn = sqlite3.connect(TODO_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT text FROM entries WHERE status = 'pending'")
        tasks = [t[0] for t in cursor.fetchall()]
        conn.close()
        return tasks
    except Exception as e:
        print(f"Error reading todo DB: {e}")
        return []

def aggregate():
    print("🔄 Aggregating Roadmap and Todo list...")
    
    # Read Roadmap
    roadmap_content = ""
    if os.path.exists(ROADMAP_PATH):
        with open(ROADMAP_PATH, 'r') as f:
            roadmap_content = f.read()
            
    # Get Todo Tasks
    todos = get_todo_tasks()
    todo_section = "\n## 📝 Current Todo Queue\n"
    for task in todos:
        todo_section += f"- [ ] {task}\n"
    
    # Merge
    unified_content = f"{roadmap_content}\n\n{todo_section}"
    
    with open(OUTPUT_PATH, 'w') as f:
        f.write(unified_content)
    
    print(f"✅ Unified plan written to {OUTPUT_PATH}")

if __name__ == "__main__":
    aggregate()
