import json
import os

def remove_completed_pi_dev_tasks(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    original_count = len(data['queue'])
    new_queue = []
    removed_tasks = []

    for task in data['queue']:
        # Criteria: Pi.dev, completed, and POW file exists
        if task.get('agent') == 'Pi.dev' and task.get('status') == 'completed':
            pow_file = task.get('pow_file')
            # Check if pow_file is defined and exists on disk
            # We check relative to the repo root
            if pow_file and os.path.exists(pow_file):
                removed_tasks.append(task['id'])
                continue # Skip adding to new_queue (remove)
        
        new_queue.append(task)
    
    data['queue'] = new_queue
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    return original_count, len(new_queue), removed_tasks

if __name__ == "__main__":
    path = 'infrastructure/configs/stqueue.json'
    orig, final, removed = remove_completed_pi_dev_tasks(path)
    print(f"Original tasks: {orig}")
    print(f"Final tasks: {final}")
    print(f"Removed {len(removed)} tasks: {', '.join(removed)}")
