#!/usr/bin/env python3

import time
from human_ai.core.integrations.bridge_router import BridgeRouter
from human_ai.core.integrations.anything_llm_bridge import AnythingLLMBridge
from human_ai.core.integrations.dify_bridge import DifyBridge
from human_ai.core.integrations.memory_bridge import MemoryBridge

# Initialize router with all bridges
bridges = [AnythingLLMBridge(), DifyBridge(), MemoryBridge()]
router = BridgeRouter(bridges)

# Benchmark task types
task_types = ['nlp_analysis', 'api_integration', 'data_processing']

results = []

for task_type in task_types:
    start_time = time.time()
    # Simulate query
    query_data = {'task_type': task_type, 'data_source': 'benchmark', 'params': {}}
    response = router.route_query(query_data)
    end_time = time.time()
    latency = end_time - start_time
    results.append({
        'task_type': task_type,
        'latency_ms': latency * 1000,
        'success': 'error' not in response
    })

# Save results
with open('/home/yahwehatwork/human-ai/research/router_performance.json', 'w') as f:
    import json
    json.dump(results, f, indent=2)