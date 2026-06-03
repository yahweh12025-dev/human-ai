#!/usr/bin/env python3
"""
Test script for BridgeRouter audit.
Tests:
1. Routing latency benchmark
2. Failover mechanism verification
"""

import time
import json
import sys
sys.path.insert(0, '/home/yahwehatwork/human-ai/core')

from integrations.bridge_router import BridgeRouter
from integrations.base_bridge import BridgeInterface

# Mock bridge implementations for testing
class MockBridge(BridgeInterface):
    def __init__(self, name, failure_delay=None):
        self.name = name
        self.failure_delay = failure_delay
        self.call_count = 0
    
    def initialize(self, query_params):
        pass
    
    def query(self, data_source, params):
        self.call_count += 1
        if self.failure_delay:
            time.sleep(self.failure_delay)
        # Simulate bridge response
        return {'bridge': self.name, 'data': f'response from {self.name}', 'success': True}
    
    def retrieve_data(self, results):
        return results
    
    def handle_error(self, error):
        return {'error': str(error)}
    
    def close(self):
        pass

class FailingBridge(BridgeInterface):
    """Bridge that always fails to test failover."""
    def __init__(self, name):
        self.name = name
        self.call_count = 0
    
    def initialize(self, query_params):
        pass
    
    def query(self, data_source, params):
        self.call_count += 1
        raise Exception(f"{self.name} simulated failure")
    
    def retrieve_data(self, results):
        return results
    
    def handle_error(self, error):
        return {'error': str(error)}
    
    def close(self):
        pass

def benchmark_routing_latency():
    """Benchmark routing latency across different task types."""
    print("=== Routing Latency Benchmark ===\n")
    
    bridges = [MockBridge('BridgeA'), MockBridge('BridgeB'), MockBridge('BridgeC')]
    router = BridgeRouter(bridges)
    
    task_types = ['nlp_analysis', 'api_integration', 'data_processing']
    results = []
    
    for task_type in task_types:
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            response = router.route_query({
                'task_type': task_type,
                'data_source': 'test',
                'params': {}
            })
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # ms
        
        avg_latency = sum(latencies) / len(latencies)
        results.append({
            'task_type': task_type,
            'avg_latency_ms': round(avg_latency, 3),
            'min_latency_ms': round(min(latencies), 3),
            'max_latency_ms': round(max(latencies), 3),
            'success': True
        })
        print(f"  {task_type}: avg={avg_latency:.3f}ms, min={min(latencies):.3f}ms, max={max(latencies):.3f}ms")
    
    return results

def test_failover():
    """Test failover mechanism by simulating bridge failures."""
    print("\n=== Failover Mechanism Test ===\n")
    
    # Create bridges: first fails, second works
    failing_bridge = FailingBridge('FailingBridge')
    working_bridge = MockBridge('WorkingBridge')
    third_bridge = MockBridge('ThirdBridge')
    
    router = BridgeRouter([failing_bridge, working_bridge, third_bridge])
    
    # Test routing with task that maps to failing bridge first
    response = router.route_query({
        'task_type': 'nlp_analysis',  # maps to bridges[0] which is failing
        'data_source': 'test',
        'params': {}
    })
    
    failover_success = response.get('bridge') == 'WorkingBridge'
    print(f"  Initial bridge (FailingBridge) call count: {failing_bridge.call_count}")
    print(f"  Failover to WorkingBridge call count: {working_bridge.call_count}")
    print(f"  Response: {response}")
    print(f"  Failover successful: {failover_success}")
    
    return {
        'initial_bridge_failures': failing_bridge.call_count,
        'failover_success': failover_success,
        'response_bridge': response.get('bridge'),
        'test_passed': failover_success
    }

def main():
    latency_results = benchmark_routing_latency()
    failover_results = test_failover()
    
    # Compile final report
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'latency_benchmark': latency_results,
        'failover_test': failover_results,
        'overall_status': 'PASS' if failover_results['test_passed'] else 'FAIL'
    }
    
    # Save report
    with open('/home/yahwehatwork/human-ai/research/router_performance.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n=== Report saved to /home/yahwehatwork/human-ai/research/router_performance.json ===")
    return report

if __name__ == '__main__':
    main()