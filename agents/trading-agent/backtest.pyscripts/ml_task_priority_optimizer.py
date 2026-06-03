#!/usr/bin/env python3
"""
ML Task Priority Optimizer
Machine learning-based task priority optimizer using historical completion data
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import statistics
import math

class MLTaskPriorityOptimizer:
    def __init__(self, data_dir: str = "/home/yahwehatwork/human-ai"):
        self.data_dir = data_dir
        self.stqueue_path = os.path.join(data_dir, "infrastructure/configs/stqueue.json")
        self.model_path = os.path.join(data_dir, "scripts/ml_priority_model.json")
        self.feature_weights = {
            'agent_experience': 0.25,
            'task_complexity': 0.20,
            'historical_priority': 0.20,
            'dependency_count': 0.15,
            'estimated_duration': 0.10,
            'urgency_factors': 0.10
        }
        self._ensure_model()
    
    def _ensure_model(self):
        """Ensure the ML model file exists with default weights"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        if not os.path.exists(self.model_path):
            default_model = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'feature_weights': self.feature_weights.copy(),
                'agent_performance': {},
                'task_type_difficulty': {},
                'training_samples': 0
            }
            with open(self.model_path, 'w') as f:
                json.dump(default_model, f, indent=2)
    
    def load_model(self) -> Dict[str, Any]:
        """Load the ML model"""
        with open(self.model_path, 'r') as f:
            return json.load(f)
    
    def save_model(self, model: Dict[str, Any]):
        """Save the ML model"""
        model['last_updated'] = datetime.now().isoformat()
        with open(self.model_path, 'w') as f:
            json.dump(model, f, indent=2)
    
    def load_task_data(self) -> List[Dict]:
        """Load task data from stqueue"""
        if os.path.exists(self.stqueue_path):
            with open(self.stqueue_path, 'r') as f:
                return json.load(f).get('queue', [])
        return []
    
    def extract_features(self, task: Dict, model: Dict[str, Any]) -> Dict[str, float]:
        """Extract features for ML-based priority prediction"""
        features = {}
        
        # Agent experience feature
        agent = task.get('agent', 'Unknown')
        agent_perf = model.get('agent_performance', {}).get(agent, {
            'completion_rate': 0.5,
            'avg_completion_time': 4.0,
            'task_count': 0
        })
        # Normalize agent experience (0-1 scale)
        agent_exp = min(1.0, agent_perf.get('task_count', 0) / 50.0)  # 50 tasks = max experience
        features['agent_experience'] = agent_exp
        
        # Task complexity (based on description length and keywords)
        task_desc = task.get('task', '')
        complexity_indicators = ['implement', 'develop', 'create', 'build', 'design', 'architecture', 
                               'system', 'framework', 'optimize', 'analyze', 'research']
        complexity_score = sum(1 for indicator in complexity_indicators 
                             if indicator in task_desc.lower()) / len(complexity_indicators)
        features['task_complexity'] = min(1.0, complexity_score)
        
        # Historical priority feature
        historical_priority = task.get('priority', 3) / 4.0  # Normalize to 0-1
        features['historical_priority'] = historical_priority
        
        # Dependency count (placeholder - would analyze actual dependencies)
        features['dependency_count'] = 0.3  # Default moderate dependency
        
        # Estimated duration (based on task type and historical data)
        # Simple heuristic: longer descriptions = longer estimated time
        desc_length = len(task.get('task', ''))
        norm_duration = min(1.0, desc_length / 200.0)  # 200 chars = max duration
        features['estimated_duration'] = norm_duration
        
        # Urgency factors (keywords indicating urgency)
        urgency_keywords = ['urgent', 'critical', 'asap', 'immediately', 'blocking', 'breakage']
        urgency_score = sum(1 for keyword in urgency_keywords 
                          if keyword in task.get('task', '').lower()) / len(urgency_keywords)
        features['urgency_factors'] = min(1.0, urgency_score)
        
        return features
    
    def predict_priority(self, task: Dict) -> Dict[str, Any]:
        """Predict optimal priority for a task using ML model"""
        model = self.load_model()
        features = self.extract_features(task, model)
        
        # Calculate weighted score
        score = 0.0
        feature_contributions = {}
        
        for feature, value in features.items():
            weight = model.get('feature_weights', self.feature_weights).get(feature, 0)
            contribution = value * weight
            score += contribution
            feature_contributions[feature] = {
                'value': value,
                'weight': weight,
                'contribution': contribution
            }
        
        # Convert score (0-1) to priority level (1-5)
        # Use sigmoid-like distribution to favor middle priorities
        priority_float = 1 + (score * 4)  # Map 0-1 to 1-5
        
        # Apply some non-linearity to avoid too many extreme priorities
        if priority_float < 1.5:
            priority_level = 1
        elif priority_float < 2.5:
            priority_level = 2
        elif priority_float < 3.5:
            priority_level = 3
        elif priority_float < 4.5:
            priority_level = 4
        else:
            priority_level = 5
        
        confidence = min(0.95, 0.5 + (len(model.get('agent_performance', {})) * 0.01))  # More data = more confidence
        
        return {
            'task_id': task.get('id', 'unknown'),
            'predicted_priority': priority_level,
            'priority_score': priority_float,
            'confidence': confidence,
            'features': features,
            'feature_contributions': feature_contributions,
            'original_priority': task.get('priority', 3)
        }
    
    def optimize_queue(self) -> Dict[str, Any]:
        """Optimize the entire task queue using ML predictions"""
        tasks = self.load_task_data()
        pending_tasks = [t for t in tasks if t.get('status') == 'pending']
        
        optimizations = []
        for task in pending_tasks:
            prediction = self.predict_priority(task)
            optimizations.append(prediction)
        
        # Sort by predicted priority score (descending)
        optimizations.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Update model with recent task data (simplified learning)
        self._update_model(tasks)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_tasks_analyzed': len(pending_tasks),
            'optimizations': optimizations,
            'model_info': {
                'version': self.load_model().get('version', '1.0'),
                'agent_types_tracked': len(self.load_model().get('agent_performance', {}))
            }
        }
    
    def _update_model(self, tasks: List[Dict]):
        """Update the ML model with new task completion data"""
        model = self.load_model()
        
        # Update agent performance metrics
        agent_stats = defaultdict(lambda: {'completed': 0, 'total_time': 0.0, 'count': 0})
        
        for task in tasks:
            agent = task.get('agent', 'Unknown')
            if task.get('status') == 'completed':
                # In a real system, we'd have actual timing data
                # For now, use estimated completion time based on priority
                est_time = task.get('priority', 3) * 2.0  # Rough estimate
                agent_stats[agent]['completed'] += 1
                agent_stats[agent]['total_time'] += est_time
            agent_stats[agent]['count'] += 1
        
        # Update model
        for agent, stats in agent_stats.items():
            if agent not in model['agent_performance']:
                model['agent_performance'][agent] = {
                    'completion_rate': 0.5,
                    'avg_completion_time': 4.0,
                    'task_count': 0
                }
            
            perf = model['agent_performance'][agent]
            if stats['count'] > 0:
                perf['completion_rate'] = stats['completed'] / stats['count']
                if stats['completed'] > 0:
                    perf['avg_completion_time'] = stats['total_time'] / stats['completed']
                perf['task_count'] = stats['count']
        
        # Increment training samples
        model['training_samples'] = len([t for t in tasks if t.get('status') == 'completed'])
        
        # Save updated model
        self.save_model(model)

if __name__ == "__main__":
    optimizer = MLTaskPriorityOptimizer()
    result = optimizer.optimize_queue()
    
    print(f"ML Task Priority Optimization - {result['timestamp']}")
    print(f"Analyzed {result['total_tasks_analyzed']} pending tasks")
    
    print("\nTop 5 Priority Optimizations:")
    for opt in result['optimizations'][:5]:
        direction = "↑" if opt['predicted_priority'] > opt['original_priority'] else "↓" if opt['predicted_priority'] < opt['original_priority'] else "→"
        print(f"  {opt['task_id']}: {opt['original_priority']} → {opt['predicted_priority']} {direction} "
              f"(score: {opt['priority_score']:.2f}, conf: {opt['confidence']:.2%})")
    
    print(f"\nModel Info: {result['model_info']}")