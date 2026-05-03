import json
f = open('task_queue.json')
data = json.load(f)
f.close()
pending = [t for t in data['tasks'] if t['status'] == 'pending']
in_progress = [t for t in data['tasks'] if t['status'] == 'in_progress']
completed = [t for t in data['tasks'] if t['status'] == 'completed']
print(f'Pending: {len(pending)}, In Progress: {len(in_progress)}, Completed: {len(completed)}')
print('\nRecent In Progress:')
for t in in_progress[:5]:
    print(f'  - {t["id"]}: {t["title"][:50]}...')