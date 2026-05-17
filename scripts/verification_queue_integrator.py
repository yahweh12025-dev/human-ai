#!/usr/bin/env python3
"""
Verification Queue Integrator
Integrates verification results with task queue to adjust priorities
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

class VerificationQueueIntegrator:
    def __init__(self, data_dir: str = "/home/yahwehatwork/human-ai"):
        self.data_dir = data_dir
        self.stqueue_path = os.path.join(data_dir, "infrastructure/configs/stqueue.json")
        self.verification_dir = os.path.join(data_dir, "docs/verification")
        self.integration_log_path = os.path.join(data_dir, "scripts/queue_integration_log.json")
        self._ensure_directories()
    
    def _ensure_directories(self):
        os.makedirs(os.path.dirname(self.integration_log_path), exist_ok=True)
    
    def load_task_queue(self) -> Dict[str, Any]:
        if os.path.exists(self.stqueue_path):
            with open(self.stqueue_path, 'r') as f:
                return json.load(f)
        return {"queue": [], "active_batch": [], "completed": [], "failed": []}
    
    def save_task_queue(self, queue_data: Dict[str, Any]):
        with open(self.stqueue_path, 'w') as f:
            json.dump(queue_data, f, indent=2)
    
    def load_verification_results(self, days: int = 7) -> List[Dict]:
        """Load verification results from the last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        verification_results = []
        
        # Look for verification audit files
        if os.path.exists(self.verification_dir):
            for root, dirs, files in os.walk(self.verification_dir):
                for file in files:
                    if file.endswith('.md') or file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        try:
                            # Check file modification time
                            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            if mod_time >= cutoff_date:
                                # Try to extract verification info
                                if file.endswith('.json'):
                                    with open(file_path, 'r') as f:
                                        data = json.load(f)
                                        if isinstance(data, dict):
                                            verification_results.append({
                                                'file': file_path,
                                                'timestamp': mod_time.isoformat(),
                                                'data': data
                                            })
                                else:
                                    # For markdown files, just note they exist
                                    verification_results.append({
                                        'file': file_path,
                                        'timestamp': mod_time.isoformat(),
                                        'type': 'markdown_report'
                                    })
                        except:
                            pass  # Skip files we can't read
        
        return verification_results
    
    def analyze_verification_trends(self, verification_results: List[Dict]) -> Dict[str, Any]:
        """Analyze verification results to identify trends"""
        if not verification_results:
            return {"trend": "insufficient_data", "recommendations": []}
        
        # Count failures vs successes (simplified)
        # In a real implementation, we'd parse the actual verification results
        total_verifications = len(verification_results)
        
        # Simple heuristic: look for failure indicators in filenames or content
        failure_indicators = ['fail', 'error', 'problem', 'issue', 'broken']
        potential_failures = 0
        
        for result in verification_results:
            file_name = os.path.basename(result['file']).lower()
            if any(indicator in file_name for indicator in failure_indicators):
                potential_failures += 1
        
        failure_rate = potential_failures / total_verifications if total_verifications > 0 else 0
        
        # Determine trend
        if failure_rate > 0.3:
            trend = "degrading"
            priority_adjustment = -1  # Increase priority (lower number) to address issues
        elif failure_rate > 0.1:
            trend = "warning"
            priority_adjustment = 0   # Keep same priority
        else:
            trend = "improving"
            priority_adjustment = 1   # Decrease priority (higher number) as things are working well
        
        return {
            "trend": trend,
            "failure_rate": failure_rate,
            "total_verifications": total_verifications,
            "potential_failures": potential_failures,
            "priority_adjustment": priority_adjustment,
            "recommendations": [
                f"Verification failure rate: {failure_rate*100:.1f}%",
                f"Trend: {trend}",
                f"Suggested priority adjustment: {priority_adjustment}"
            ]
        }
    
    def adjust_task_priorities(self, queue_data: Dict[str, Any], 
                              verification_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust task priorities based on verification analysis"""
        adjustment = verification_analysis.get("priority_adjustment", 0)
        
        # Apply adjustment to pending tasks
        adjusted_queue = queue_data.copy()
        if 'queue' in adjusted_queue:
            for task in adjusted_queue['queue']:
                if task.get('status') == 'pending':
                    old_priority = task.get('priority', 3)
                    # Apply adjustment but keep within bounds 1-4
                    new_priority = max(1, min(4, old_priority + adjustment))
                    task['priority'] = new_priority
                    task['priority_adjustment'] = adjustment
                    task['priority_adjustment_reason'] = verification_analysis.get('trend', 'unknown')
                    task['priority_adjustment_timestamp'] = datetime.now().isoformat()
        
        return adjusted_queue
    
    def run_integration(self) -> Dict[str, Any]:
        """Run the verification queue integration process"""
        # Load current task queue
        queue_data = self.load_task_queue()
        
        # Load recent verification results
        verification_results = self.load_verification_results(days=7)
        
        # Analyze verification trends
        verification_analysis = self.analyze_verification_trends(verification_results)
        
        # Adjust task priorities based on verification results
        adjusted_queue = self.adjust_task_priorities(queue_data, verification_analysis)
        
        # Save the adjusted queue
        self.save_task_queue(adjusted_queue)
        
        # Log the integration
        integration_log = {
            'timestamp': datetime.now().isoformat(),
            'verification_results_analyzed': len(verification_results),
            'verification_analysis': verification_analysis,
            'tasks_adjusted': len([
                t for t in adjusted_queue.get('queue', []) 
                if t.get('status') == 'pending' and 'priority_adjustment' in t
            ]),
            'queue_summary': {
                'pending': len([t for t in adjusted_queue.get('queue', []) if t.get('status') == 'pending']),
                'completed': len(adjusted_queue.get('completed', [])),
                'failed': len(adjusted_queue.get('failed', []))
            }
        }
        
        # Load existing log
        log_history = []
        if os.path.exists(self.integration_log_path):
            try:
                with open(self.integration_log_path, 'r') as f:
                    log_history = json.load(f)
            except:
                log_history = []
        
        log_history.append(integration_log)
        
        # Keep last 100 entries
        if len(log_history) > 100:
            log_history = log_history[-100:]
        
        with open(self.integration_log_path, 'w') as f:
            json.dump(log_history, f, indent=2)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'integration_log': integration_log,
            'verification_results_count': len(verification_results),
            'queue_updated': True
        }

if __name__ == "__main__":
    integrator = VerificationQueueIntegrator()
    result = integrator.run_integration()
    
    print(f"Verification Queue Integration - {result['timestamp']}")
    print(f"Verification results analyzed: {result['verification_results_count']}")
    
    log = result['integration_log']
    print(f"Tasks adjusted: {log['tasks_adjusted']}")
    print(f"Verification trend: {log['verification_analysis'].get('trend', 'unknown')}")
    print(f"Failure rate: {log['verification_analysis'].get('failure_rate', 0)*100:.1f}%")
    
    print("\nQueue Summary:")
    summary = log['queue_summary']
    for status, count in summary.items():
        print(f"  {status}: {count}")