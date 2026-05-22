#!/usr/bin/env python3
"""
Cross-Agent Collaboration Optimization System
Suggests optimal task assignments based on historical performance and current workload
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import statistics
import math

class CollaborationOptimizer:
    def __init__(self, data_dir: str = "/home/yahwehatwork/human-ai"):
        self.data_dir = data_dir
        self.stqueue_path = os.path.join(data_dir, "infrastructure/configs/stqueue.json")
        self.agent_performance_path = os.path.join(data_dir, "core/agent_performance.json")
        self.workload_path = os.path.join(data_dir, "core/agent_workload.json")
        self.optimization_history_path = os.path.join(data_dir, "core/collaboration_optimization_history.json")
        self._ensure_data_files()
    
    def _ensure_data_files(self):
        """Ensure data files exist"""
        os.makedirs(os.path.dirname(self.agent_performance_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.workload_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.optimization_history_path), exist_ok=True)
        
        if not os.path.exists(self.agent_performance_path):
            with open(self.agent_performance_path, 'w') as f:
                json.dump({}, f, indent=2)
        
        if not os.path.exists(self.workload_path):
            with open(self.workload_path, 'w') as f:
                json.dump({}, f, indent=2)
        
        if not os.path.exists(self.optimization_history_path):
            with open(self.optimization_history_path, 'w') as f:
                json.dump({"optimizations": []}, f, indent=2)
    
    def load_stqueue(self) -> Dict[str, Any]:
        if os.path.exists(self.stqueue_path):
            with open(self.stqueue_path, 'r') as f:
                return json.load(f)
        return {"queue": [], "active_batch": [], "completed": [], "failed": []}
    
    def save_stqueue(self, queue_data: Dict[str, Any]):
        with open(self.stqueue_path, 'w') as f:
            json.dump(queue_data, f, indent=2)
    
    def load_agent_performance(self) -> Dict[str, Any]:
        if os.path.exists(self.agent_performance_path):
            with open(self.agent_performance_path, 'r') as f:
                return json.load(f)
        return {}
    
    def save_agent_performance(self, performance_data: Dict[str, Any]):
        with open(self.agent_performance_path, 'w') as f:
            json.dump(performance_data, f, indent=2)
    
    def load_agent_workload(self) -> Dict[str, Any]:
        if os.path.exists(self.workload_path):
            with open(self.workload_path, 'r') as f:
                return json.load(f)
        return {}
    
    def save_agent_workload(self, workload_data: Dict[str, Any]):
        with open(self.workload_path, 'w') as f:
            json.dump(workload_data, f, indent=2)
    
    def calculate_agent_capacity(self, agent_id: str) -> Dict[str, Any]:
        """Calculate an agent's current capacity based on performance and workload"""
        performance = self.load_agent_performance().get(agent_id, {
            'avg_completion_time': 4.0,  # hours
            'success_rate': 0.8,
            'task_count': 0,
            'specialties': []
        })
        
        workload = self.load_agent_workload().get(agent_id, {
            'current_tasks': 0,
            'estimated_workload_hours': 0,
            'max_capacity_hours': 8.0  # Standard workday
        })
        
        # Calculate available capacity
        max_capacity = workload.get('max_capacity_hours', 8.0)
        current_workload = workload.get('estimated_workload_hours', 0)
        available_hours = max(0, max_capacity - current_workload)
        
        # Calculate efficiency score based on performance
        success_rate = performance.get('success_rate', 0.8)
        task_count = performance.get('task_count', 0)
        # More tasks = more reliable performance metric
        reliability_factor = min(1.0, task_count / 20.0)  # 20 tasks for full reliability
        efficiency_score = success_rate * (0.5 + 0.5 * reliability_factor)  # Range 0.4-0.8
        
        # Speed factor (inverse of completion time, normalized)
        avg_time = performance.get('avg_completion_time', 4.0)
        speed_factor = min(1.0, 4.0 / max(avg_time, 0.5))  # Faster than 4h gets bonus
        
        # Overall capacity score
        capacity_score = efficiency_speed = (efficiency_score + speed_factor) / 2
        capacity_score = min(1.0, capacity_score * (available_hours / max_capacity) if max_capacity > 0 else 0)
        
        return {
            'agent_id': agent_id,
            'available_hours': available_hours,
            'max_capacity_hours': max_capacity,
            'current_workload_hours': current_workload,
            'utilization_rate': current_workload / max_capacity if max_capacity > 0 else 0,
            'performance': performance,
            'workload': workload,
            'efficiency_score': efficiency_score,
            'speed_factor': speed_factor,
            'capacity_score': capacity_score,
            'can_accept_task': available_hours > 1.0  # At least 1 hour available
        }
    
    def estimate_task_effort(self, task: Dict) -> Dict[str, Any]:
        """Estimate the effort required for a task based on its characteristics"""
        # Base effort estimation from priority and description
        priority = task.get('priority', 3)  # 1-4 scale
        description = task.get('task', '')
        
        # Base hours by priority (rough estimates)
        priority_base_hours = {
            1: 8.0,   # High priority - 1 day
            2: 6.0,   # Medium-high - 6 hours
            3: 4.0,   # Medium - 4 hours
            4: 2.0    # Low - 2 hours
        }
        
        base_hours = priority_base_hours.get(priority, 4.0)
        
        # Adjust based on task description keywords
        description_lower = description.lower()
        
        # Complexity indicators
        complexity_keywords = [
            'implement', 'develop', 'create', 'build', 'design', 'architecture',
            'system', 'framework', 'optimize', 'analyze', 'research', 'investigate',
            'comprehensive', 'detailed', 'thorough', 'complete', 'full'
        ]
        complexity_count = sum(1 for kw in complexity_keywords if kw in description_lower)
        complexity_factor = 1.0 + (complexity_count * 0.15)  # Up to 2.5x for high complexity
        
        # Urgency indicators (might reduce time due to focus)
        urgency_keywords = ['urgent', 'critical', 'asap', 'immediately', 'blocking']
        urgency_count = sum(1 for kw in urgency_keywords if kw in description_lower)
        urgency_factor = max(0.7, 1.0 - (urgency_count * 0.1))  # Down to 0.7x for urgent
        
        # Agent specialization bonus/penalty
        agent = task.get('agent', 'Unknown')
        # This would be enhanced with actual agent specialty data
        specialization_factor = 1.0  # Neutral for now
        
        # Calculate estimated hours
        estimated_hours = base_hours * complexity_factor * urgency_factor * specialization_factor
        estimated_hours = max(0.5, min(estimated_hours, 40.0))  # Clamp between 0.5h and 40h
        
        return {
            'base_hours': base_hours,
            'complexity_factor': complexity_factor,
            'urgency_factor': urgency_factor,
            'specialization_factor': specialization_factor,
            'estimated_hours': estimated_hours,
            'estimated_days': estimated_hours / 8.0
        }
    
    def score_task_agent_match(self, task: Dict, agent_id: str) -> Dict[str, Any]:
        """Score how well a task matches an agent based on performance, workload, and effort"""
        agent_capacity = self.calculate_agent_capacity(agent_id)
        task_effort = self.estimate_task_effort(task)
        
        # If agent can't accept the task (no capacity), score is 0
        if not agent_capacity['can_accept_task']:
            return {
                'agent_id': agent_id,
                'task_id': task.get('id', 'unknown'),
                'match_score': 0.0,
                'reason': 'Insufficient capacity',
                'agent_capacity': agent_capacity,
                'task_effort': task_effort,
                'recommendation': 'Agent at full capacity'
            }
        
        # Calculate various scoring components
        scores = {}
        
        # 1. Capacity fit (how well the task fits in available time)
        required_hours = task_effort['estimated_hours']
        available_hours = agent_capacity['available_hours']
        if required_hours <= available_hours:
            capacity_fit = 1.0  # Perfect fit
        else:
            capacity_fit = max(0.0, 1.0 - ((required_hours - available_hours) / required_hours))
        scores['capacity_fit'] = capacity_fit
        
        # 2. Performance score (based on agent's historical performance)
        performance = agent_capacity['performance']
        success_rate = performance.get('success_rate', 0.8)
        task_count = performance.get('task_count', 0)
        reliability = min(1.0, task_count / 15.0)  # Full reliability at 15 tasks
        performance_score = success_rate * (0.5 + 0.5 * reliability)  # 0.4-0.8 range
        scores['performance'] = performance_score
        
        # 3. Workload balance (prefer agents with lower utilization)
        utilization = agent_capacity['utilization_rate']
        # Lower utilization is better for new tasks (invert and normalize)
        workload_score = max(0.0, 1.0 - utilization)
        scores['workload_balance'] = workload_score
        
        # 4. Specialty match (simplified - would be enhanced with actual specialty data)
        # For now, give a small bonus to all agents
        scores['specialty_match'] = 0.8
        
        # 5. Priority alignment (hriority tasks might benefit from better performers)
        priority = task.get('priority', 3)
        # Normalize priority to 0-1 scale (1=highest priority=1.0, 4=lowest=0.0)
        priority_normalized = (5 - priority) / 4.0
        # Higher priority tasks should go to better performing agents
        priority_align = 1.0 - abs(priority_normalized - performance_score)
        scores['priority_alignment'] = max(0.0, priority_align)
        
        # Calculate weighted final score
        weights = {
            'capacity_fit': 0.30,
            'performance': 0.25,
            'workload_balance': 0.20,
            'specialty_match': 0.15,
            'priority_alignment': 0.10
        }
        
        final_score = sum(scores[key] * weights[key] for key in weights)
        
        # Generate recommendation
        if final_score >= 0.8:
            recommendation = "Excellent match"
        elif final_score >= 0.6:
            recommendation = "Good match"
        elif final_score >= 0.4:
            recommendation = "Fair match"
        else:
            recommendation = "Poor match - consider other agents or wait for capacity"
        
        return {
            'agent_id': agent_id,
            'task_id': task.get('id', 'unknown'),
            'match_score': final_score,
            'scores': scores,
            'weights': weights,
            'agent_capacity': agent_capacity,
            'task_effort': task_effort,
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat()
        }
    
    def optimize_task_assignment(self, task_id: str = None) -> Dict[str, Any]:
        """Find the optimal agent assignment for a task or all pending tasks"""
        queue_data = self.load_stqueue()
        pending_tasks = [t for t in queue_data.get('queue', []) if t.get('status') == 'pending']
        
        if task_id:
            # Optimize for specific task
            task = next((t for t in pending_tasks if t.get('id') == task_id), None)
            if not task:
                return {'error': f'Task {task_id} not found or not pending'}
            tasks_to_optimize = [task]
        else:
            # Optimize for all pending tasks
            tasks_to_optimize = pending_tasks
        
        if not tasks_to_optimize:
            return {'message': 'No pending tasks to optimize'}
        
        # Get all known agents (from performance data, workload, and stqueue)
        agent_performance = self.load_agent_performance()
        agent_workload = self.load_agent_workload()
        stqueue_agents = set(t.get('agent') for t in pending_tasks if t.get('agent'))
        all_agents = set(list(agent_performance.keys()) + list(agent_workload.keys()) + list(stqueue_agents))
        # Remove empty/None agents
        all_agents = {agent for agent in all_agents if agent and agent.strip()}
        
        if not all_agents:
            # Default to known agents if no data
            all_agents = {'Hermes', 'OpenCode', 'Researcher'}
        
        optimizations = []
        for task in tasks_to_optimize:
            task_optimizations = []
            for agent_id in all_agents:
                match_score = self.score_task_agent_match(task, agent_id)
                task_optimizations.append(match_score)
            
            # Sort by match score (descending)
            task_optimizations.sort(key=lambda x: x['match_score'], reverse=True)
            
            optimizations.append({
                'task': task,
                'agent_matches': task_optimizations,
                'recommended_agent': task_optimizations[0]['agent_id'] if task_optimizations else None,
                'confidence': task_optimizations[0]['match_score'] if task_optimizations else 0.0
            })
        
        # Save optimization history
        self._save_optimization_history(optimizations)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'tasks_analyzed': len(tasks_to_optimize),
            'agents_considered': list(all_agents),
            'optimizations': optimizations,
            'summary': self._generate_optimization_summary(optimizations)
        }
    
    def _save_optimization_history(self, optimizations: List[Dict]):
        """Save optimization results to history"""
        history = {"optimizations": []}
        if os.path.exists(self.optimization_history_path):
            try:
                with open(self.optimization_history_path, 'r') as f:
                    history = json.load(f)
            except:
                history = {"optimizations": []}
        
        # Add current optimization run
        history_run = {
            'timestamp': datetime.now().isoformat(),
            'optimizations_count': len(optimizations),
            'optimizations': optimizations
        }
        
        history['optimizations'].append(history_run)
        
        # Keep last 50 runs
        if len(history['optimizations']) > 50:
            history['optimizations'] = history['optimizations'][-50:]
        
        with open(self.optimization_history_path, 'w') as f:
            json.dump(history, f, indent=2)
    
    def _generate_optimization_summary(self, optimizations: List[Dict]) -> Dict[str, Any]:
        """Generate a summary of the optimization results"""
        if not optimizations:
            return {'message': 'No optimizations generated'}
        
        # Count recommendations by agent
        agent_recommendations = {}
        confidence_scores = []
        
        for opt in optimizations:
            recommended = opt.get('recommended_agent')
            confidence = opt.get('confidence', 0)
            if recommended:
                agent_recommendations[recommended] = agent_recommendations.get(recommended, 0) + 1
                confidence_scores.append(confidence)
        
        # Calculate average confidence
        avg_confidence = statistics.mean(confidence_scores) if confidence_scores else 0
        
        # Find tasks with low confidence (may need manual review)
        low_confidence_tasks = [
            opt for opt in optimizations 
            if opt.get('confidence', 0) < 0.5
        ]
        
        return {
            'total_tasks_optimized': len(optimizations),
            'agent_recommendations': agent_recommendations,
            'average_confidence': avg_confidence,
            'low_confidence_count': len(low_confidence_tasks),
            'high_confidence_count': len([opt for opt in optimizations if opt.get('confidence', 0) >= 0.7]),
            'recommendations': [
                f"Optimized {len(optimizations)} tasks for agent assignment",
                f"Average confidence: {avg_confidence:.2%}",
                f"Most recommended agent: {max(agent_recommendations, key=agent_recommendations.get) if agent_recommendations else 'None'}",
                f"{len(low_confidence_tasks)} tasks have low confidence and may need manual review"
            ]
        }

def main():
    """Main entry point for the Collaboration Optimizer"""
    optimizer = CollaborationOptimizer()
    result = optimizer.optimize_task_assignment()
    
    print(f"Cross-Agent Collaboration Optimization - {result['timestamp']}")
    print(f"Tasks analyzed: {result['tasks_analyzed']}")
    print(f"Agents considered: {len(result['agents_considered'])}")
    
    if 'summary' in result:
        summary = result['summary']
        print(f"\nOptimization Summary:")
        for rec in summary.get('recommendations', []):
            print(f"  - {rec}")
    
    print(f"\nTop Task Assignments:")
    for opt in result['optimizations'][:5]:  # Show top 5
        task = opt['task']
        recommended = opt['recommended_agent']
        confidence = opt['confidence']
        print(f"  {task.get('id', 'unknown')}: {task.get('task', '')[:50]}...")
        print(f"    → Recommended Agent: {recommended} (confidence: {confidence:.2%})")
        if opt['agent_matches']:
            alt_agent = opt['agent_matches'][1]['agent_id'] if len(opt['agent_matches']) > 1 else None
            alt_conf = opt['agent_matches'][1]['match_score'] if len(opt['agent_matches']) > 1 else 0
            if alt_agent:
                print(f"    → Alternative: {alt_agent} (confidence: {alt_conf:.2%})")
    
    # Save results
    results_file = os.path.join(optimizer.data_dir, "core/collaboration_optimization_results.json")
    with open(results_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")
    return True

if __name__ == "__main__":
    main()