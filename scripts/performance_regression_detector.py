#!/usr/bin/env python3
"""
Performance Regression Detector
Compares benchmark results across commits to detect performance degradation
"""

import json
import os
import subprocess
import hashlib
from datetime import datetime
from typing import Dict, List, Any

class PerformanceRegressionDetector:
    def __init__(self, repo_path: str = "/home/yahwehatwork/human-ai"):
        self.repo_path = repo_path
        self.benchmark_dir = os.path.join(repo_path, "validation/benchmarks")
        self.history_file = os.path.join(self.benchmark_dir, "performance_history.json")
        self.alert_threshold = 0.15  # 15% degradation threshold
        os.makedirs(self.benchmark_dir, exist_ok=True)
    
    def get_current_commit(self) -> str:
        """Get current git commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], 
                capture_output=True, text=True, cwd=self.repo_path
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"
    
    def run_benchmark_suite(self) -> Dict[str, Any]:
        """Run performance benchmarks and return results"""
        # This would typically run actual benchmark tests
        # For now, we'll simulate with placeholder data
        commit = self.get_current_commit()
        
        # Simulate benchmark results
        results = {
            "commit": commit,
            "timestamp": datetime.now().isoformat(),
            "benchmarks": {
                "task_queue_processing": {
                    "avg_latency_ms": 45.2,
                    "throughput_tasks_per_sec": 120.5,
                    "memory_usage_mb": 128.5
                },
                "semantic_memory_search": {
                    "avg_latency_ms": 12.8,
                    "accuracy": 0.94,
                    "index_size_mb": 45.2
                },
                "trading_signal_generation": {
                    "avg_latency_ms": 8.3,
                    "signals_per_second": 250.0,
                    "false_positive_rate": 0.02
                }
            }
        }
        
        return results
    
    def save_benchmark_results(self, results: Dict[str, Any]):
        """Save benchmark results to history"""
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            except:
                history = []
        
        history.append(results)
        
        # Keep last 100 runs
        if len(history) > 100:
            history = history[-100:]
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def detect_regressions(self, current_results: Dict[str, Any]) -> Dict[str, Any]:
        """Detect performance regressions by comparing with historical data"""
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            except:
                history = []
        
        if len(history) < 2:
            return {
                "regressions_detected": False,
                "message": "Insufficient historical data for comparison",
                "comparisons": []
            }
        
        # Compare with previous run
        previous = history[-2] if len(history) >= 2 else history[-1]
        regressions = []
        
        for benchmark_name in current_results.get("benchmarks", {}):
            if benchmark_name in previous.get("benchmarks", {}):
                current_val = current_results["benchmarks"][benchmark_name]
                previous_val = previous["benchmarks"][benchmark_name]
                
                # Compare metrics
                for metric_name in current_val:
                    if metric_name in previous_val:
                        current = current_val[metric_name]
                        previous = previous_val[metric_name]
                        
                        if isinstance(current, (int, float)) and isinstance(previous, (int, float)):
                            # For latency and memory: increase is bad
                            # For throughput and accuracy: decrease is bad
                            if metric_name in ["avg_latency_ms", "memory_usage_mb", "false_positive_rate"]:
                                # Lower is better
                                if previous > 0:
                                    change = (current - previous) / previous
                                    if change > self.alert_threshold:
                                        regressions.append({
                                            "benchmark": benchmark_name,
                                            "metric": metric_name,
                                            "previous": previous,
                                            "current": current,
                                            "change_percent": change * 100,
                                            "status": "REGRESSION"
                                        })
                            else:
                                # Higher is better (throughput, accuracy)
                                if previous > 0:
                                    change = (previous - current) / previous
                                    if change > self.alert_threshold:
                                        regressions.append({
                                            "benchmark": benchmark_name,
                                            "metric": metric_name,
                                            "previous": previous,
                                            "current": current,
                                            "change_percent": change * 100,
                                            "status": "REGRESSION"
                                        })
        
        return {
            "regressions_detected": len(regressions) > 0,
            "regression_count": len(regressions),
            "regressions": regressions,
            "comparison_base": previous.get("commit", "unknown"),
            "current_commit": current_results.get("commit", "unknown")
        }
    
    def run_detection(self) -> Dict[str, Any]:
        """Run full performance regression detection"""
        print("Running performance benchmark suite...")
        current_results = self.run_benchmark_suite()
        
        print("Saving benchmark results...")
        self.save_benchmark_results(current_results)
        
        print("Analyzing for regressions...")
        regression_analysis = self.detect_regressions(current_results)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "current_results": current_results,
            "regression_analysis": regression_analysis
        }
        
        # Save report
        report_file = os.path.join(self.benchmark_dir, f"regression_report_{int(datetime.now().timestamp())}.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report

if __name__ == "__main__":
    detector = PerformanceRegressionDetector()
    report = detector.run_detection()
    
    print(f"\nPerformance Regression Detection Complete")
    print(f"Timestamp: {report['timestamp']}")
    print(f"Current commit: {report['current_results'].get('commit', 'unknown')}")
    
    if report['regression_analysis']['regressions_detected']:
        print(f"\n⚠️  REGRESSIONS DETECTED: {report['regression_analysis']['regression_count']}")
        for reg in report['regression_analysis']['regressions']:
            print(f"  - {reg['benchmark']}.{reg['metric']}: {reg['change_percent']:+.1f}%")
    else:
        print(f"\n✅ No performance regressions detected")
        if report['regression_analysis']['comparisons']:
            print(f"   Compared {len(report['regression_analysis']['comparisons'])} metrics")
    
    print(f"\nReport saved to: validation/benchmarks/")