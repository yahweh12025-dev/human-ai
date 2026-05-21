import json

def update_tasks(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # The file is actually a list at the top level, not a dict with 'queue' key
    queue = data if isinstance(data, list) else data.get('queue', [])
    
    updates = {
        "T223": {"status": "completed", "pow_file": "core/decision_extractor.py"},
        "T269": {"status": "completed", "pow_file": "scripts/security_scanner.py"},
        "T271": {"status": "completed", "pow_file": "tests/framework/test_framework.py"},
        "T278": {"status": "completed", "pow_file": "tests/property_based_trading_strategies.py"},
        "T279": {"status": "completed", "pow_file": "tests/formal_verification_trading.py"},
        "T285": {"status": "completed", "pow_file": "scripts/strategy_profiler.py"},
    }
    
    for task in queue:
        tid = task.get('id')
        if tid in updates:
            task.update(updates[tid])
            
    if isinstance(data, list):
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        data['queue'] = queue
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

if __name__ == "__main__":
    update_tasks('infrastructure/configs/stqueue.json')
