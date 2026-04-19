import sqlite3
import os

# The database is created in the current working directory of the script execution
# In our case, it's at the root of the human-ai folder.
TODO_DB_PATH = "/home/ubuntu/human-ai/todo.db"

def get_pending_tasks():
    """Directly queries the todo database for pending tasks."""
    if not os.path.exists(TODO_DB_PATH):
        print(f"Error: {TODO_DB_PATH} not found.")
        return []
    
    try:
        conn = sqlite3.connect(TODO_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, text, group_id FROM entries WHERE status = 'pending' ORDER BY id ASC")
        tasks = cursor.fetchall()
        conn.close()
        return [{"id": t[0], "task": t[1], "group": t[2]} for t in tasks]
    except Exception as e:
        print(f"Error querying todo DB: {e}")
        return []

def mark_task_done(task_id):
    """Marks a task as done."""
    if not os.path.exists(TODO_DB_PATH):
        return False
    try:
        conn = sqlite3.connect(TODO_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE entries SET status = 'done' WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating todo DB: {e}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print(get_pending_tasks())
    elif len(sys.argv) > 2 and sys.argv[1] == "done":
        print(mark_task_done(sys.argv[2]))
