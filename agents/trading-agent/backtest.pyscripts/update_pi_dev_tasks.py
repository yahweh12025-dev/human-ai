import json

# Load the stqueue.json
with open('/home/yahwehatwork/human-ai/infrastructure/configs/stqueue.json', 'r') as f:
    data = json.load(f)

queue = data['queue']

# Map of task IDs to update (mark as completed)
updates = {
    'T22': {'status': 'completed'},
    'T25': {'status': 'completed'},
    'T28': {'status': 'completed'},
    'T32': {'status': 'completed'},
    'T37': {'status': 'completed'},
    'T40': {'status': 'completed'}
}

# Update each task in the queue
for task in queue:
    tid = task.get('id')
    if tid in updates:
        task.update(updates[tid])
        print(f'Updated {tid} to completed')

# Save the updated stqueue.json
with open('/home/yahwehatwork/human-ai/infrastructure/configs/stqueue.json', 'w') as f:
    json.dump(data, f, indent=2)

print('Stqueue.json updated successfully.')