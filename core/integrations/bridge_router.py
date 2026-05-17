# bridge_router.py

from typing import Dict, Any, List
from .base_bridge import BridgeInterface

class BridgeRouter:
    def __init__(self, bridges: List[BridgeInterface]):
        self.bridges = bridges

    def select_bridge(self, task_type: str) -> BridgeInterface:
        # Task type mapping
        route_map = {
            'nlp_analysis': self.bridges[0],  # AnythingLLM
            'api_integration': self.bridges[1],  # Dify
            'data_processing': self.bridges[2]   # Example for another bridge
        }
        return route_map.get(task_type, self.bridges[0])

    def route_query(self, task_info: Dict) -> Dict:
        bridge = self.select_bridge(task_info['task_type'])
        try:
            return bridge.query(task_info['data_source'], task_info['params'])
        except Exception as e:
            # Failover to next bridge
            for next_bridge in self.bridges[1:] + [self.bridges[0]]:  # Circular failover
                try:
                    return next_bridge.query(task_info['data_source'], task_info['params'])
                except:
                    continue
            return {'error': str(e)}

# Example usage:
# router = BridgeRouter([AnythingLLMBridge(), DifyBridge(), MemoryBridge()])
# response = router.route_query({'task_type': 'nlp_analysis', 'data_source': 'AnythingLLM', 'params': {...}})