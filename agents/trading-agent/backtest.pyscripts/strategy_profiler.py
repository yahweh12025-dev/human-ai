import time
import psutil
import numpy as np
import pandas as pd
from typing import Dict, Any

class StrategyProfiler:
    """
    Profiles the execution performance of trading strategies, 
    identifying bottlenecks in latency and resource usage.
    """
    def __init__(self, strategy_fn):
        self.strategy_fn = strategy_fn

    def profile_execution(self, data: pd.Series, iterations: int = 10) -> Dict[str, Any]:
        latencies = []
        cpu_usages = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            self.strategy_fn(data)
            end_time = time.perf_counter()
            
            latencies.append(end_time - start_time)
            cpu_usages.append(psutil.cpu_percent())
            
        return {
            "avg_latency": np.mean(latencies),
            "p95_latency": np.percentile(latencies, 95),
            "avg_cpu": np.mean(cpu_usages),
            "max_latency": np.max(latencies)
        }

if __name__ == "__main__":
    # Mock strategy
    def mock_strategy(data):
        time.sleep(0.001) # Simulate work
        return "BUY"
        
    data = pd.Series(np.random.randn(1000))
    profiler = StrategyProfiler(mock_strategy)
    metrics = profiler.profile_execution(data)
    print(f"Strategy Profiling Results: {metrics}")
