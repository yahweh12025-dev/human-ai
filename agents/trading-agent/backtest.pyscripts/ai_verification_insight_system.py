#!/usr/bin/env python3
"""
AI-Powered Verification Insight System
Uses ML to identify patterns in verification results and suggest improvements to agent workflows
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import statistics

class AIVerificationInsightSystem:
    def __init__(self, data_dir: str = "/home/yahwehatwork/human-ai"):
        self.data_dir = data_dir
        self.verification_dir = os.path.join(data_dir, "docs/verification")
        self.insights_dir = os.path.join(self.verification_dir, "ai_insights")
        self.model_file = os.path.join(self.insights_dir, "verification_insight_model.json")
        self.history_file = os.path.join(self.verification_dir, "verification_history.json")
        self.insights_file = os.path.join(self.insights_dir, "latest_insights.json")
        
        # Ensure directories exist
        os.makedirs(self.insights_dir, exist_ok=True)
        
        # Initialize or load model
        self.insights_model = self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing insights model or create a new one"""
        if os.path.exists(self.model_file):
            try:
                with open(self.model_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading model: {e}")
                return self._create_new_model()
        else:
            return self._create_new_model()
    
    def _create_new_model(self):
        """Create a new empty model structure"""
        return {
            "version": "1.0",
            "last_updated": None,
            "patterns": {
                "agent_performance_patterns": {},
                "task_type_patterns": {},
                "time_patterns": {},
                "priority_patterns": {}
            },
            "improvement_suggestions": [],
            "training_samples": 0
        }
    
    def save_model(self):
        """Save the current model to disk"""
        self.insights_model["last_updated"] = datetime.now().isoformat()
        with open(self.model_file, 'w') as f:
            json.dump(self.insights_model, f, indent=2)
    
    def load_verification_history(self) -> List[Dict]:
        """Load historical verification records"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    return data.get('verifications', [])
            except:
                return []
        return []
    
    def save_verification_record(self, record: Dict):
        """Save a verification record to history"""
        history = self.load_verification_history()
        history.append(record)
        
        # Keep last 1000 records
        if len(history) > 1000:
            history = history[-1000:]
        
        with open(self.history_file, 'w') as f:
            json.dump({'verifications': history}, f, indent=2)
    
    def extract_features(self, verification_record: Dict) -> Dict[str, Any]:
        """Extract features for pattern analysis"""
        return {
            'agent': verification_record.get('agent', 'Unknown'),
            'task_type': verification_record.get('task_type', 'general'),
            'priority': verification_record.get('priority', 3),
            'status': verification_record.get('status', 'unknown'),
            'timestamp': verification_record.get('timestamp', datetime.now().isoformat()),
            'score': verification_record.get('score', verification_record.get('result', 0))
        }
    
    def train_model(self) -> Dict[str, Any]:
        """Train the insights model on historical verification data"""
        history = self.load_verification_history()
        if len(history) < 5:
            return {
                'status': 'insufficient_data',
                'message': f'Insufficient data for training. Need at least 5 records, got {len(history)}',
                'records_available': len(history)
            }
        
        # Initialize pattern counters
        patterns = {
            'agent_performance_patterns': {},
            'task_type_patterns': {},
            'time_patterns': {},
            'priority_patterns': {}
        }
        
        # Process each verification record
        for record in history:
            features = self.extract_features(record)
            agent = features['agent']
            task_type = features['task_type']
            priority = features['priority']
            status = features['status']
            score = features['score']
            
            # Agent performance patterns
            if agent not in patterns['agent_performance_patterns']:
                patterns['agent_performance_patterns'][agent] = {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'avg_score': 0.0,
                    'score_sum': 0.0
                }
            
            agent_pattern = patterns['agent_performance_patterns'][agent]
            agent_pattern['total'] += 1
            if status in ['passed', 'success']:
                agent_pattern['passed'] += 1
            elif status in ['failed', 'failure']:
                agent_pattern['failed'] += 1
            if isinstance(score, (int, float)):
                agent_pattern['score_sum'] += score
                agent_pattern['avg_score'] = agent_pattern['score_sum'] / agent_pattern['total']
            
            # Task type patterns
            if task_type not in patterns['task_type_patterns']:
                patterns['task_type_patterns'][task_type] = {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'avg_score': 0.0,
                    'score_sum': 0.0
                }
            
            task_pattern = patterns['task_type_patterns'][task_type]
            task_pattern['total'] += 1
            if status in ['passed', 'success']:
                task_pattern['passed'] += 1
            elif status in ['failed', 'failure']:
                task_pattern['failed'] += 1
            if isinstance(score, (int, float)):
                task_pattern['score_sum'] += score
                task_pattern['avg_score'] = task_pattern['score_sum'] / task_pattern['total']
            
            # Priority patterns
            if priority not in patterns['priority_patterns']:
                patterns['priority_patterns'][priority] = {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'avg_score': 0.0,
                    'score_sum': 0.0
                }
            
            priority_pattern = patterns['priority_patterns'][priority]
            priority_pattern['total'] += 1
            if status in ['passed', 'success']:
                priority_pattern['passed'] += 1
            elif status in ['failed', 'failure']:
                priority_pattern['failed'] += 1
            if isinstance(score, (int, float)):
                priority_pattern['score_sum'] += score
                priority_pattern['avg_score'] = priority_pattern['score_sum'] / priority_pattern['total']
            
            # Time patterns (hour of day)
            try:
                timestamp = datetime.fromisoformat(features['timestamp'].replace('Z', '+00:00'))
                hour = timestamp.hour
                if hour not in patterns['time_patterns']:
                    patterns['time_patterns'][hour] = {
                        'total': 0,
                        'passed': 0,
                        'failed': 0,
                        'avg_score': 0.0,
                        'score_sum': 0.0
                    }
                
                time_pattern = patterns['time_patterns'][hour]
                time_pattern['total'] += 1
                if status in ['passed', 'success']:
                    time_pattern['passed'] += 1
                elif status in ['failed', 'failure']:
                    time_pattern['failed'] += 1
                if isinstance(score, (int, float)):
                    time_pattern['score_sum'] += score
                    time_pattern['avg_score'] = time_pattern['score_sum'] / time_pattern['total']
            except:
                pass  # Skip time pattern if timestamp parsing fails
        
        # Calculate success rates and update model
        self.insights_model['patterns'] = patterns
        self.insights_model['training_samples'] = len(history)
        self.save_model()
        
        # Generate improvement suggestions based on patterns
        suggestions = self._generate_improvement_suggestions(patterns)
        self.insights_model['improvement_suggestions'] = suggestions
        self.save_model()
        
        return {
            'status': 'trained',
            'message': f'Model trained successfully on {len(history)} verification records',
            'patterns_found': {
                'agents': len(patterns['agent_performance_patterns']),
                'task_types': len(patterns['task_type_patterns']),
                'priorities': len(patterns['priority_patterns']),
                'time_hours': len(patterns['time_patterns'])
            },
            'suggestions_generated': len(suggestions)
        }
    
    def _generate_improvement_suggestions(self, patterns: Dict) -> List[Dict]:
        """Generate improvement suggestions based on discovered patterns"""
        suggestions = []
        
        # Agent performance suggestions
        agent_patterns = patterns['agent_performance_patterns']
        for agent, data in agent_patterns.items():
            if data['total'] >= 3:  # Only suggest if we have enough data
                success_rate = data['passed'] / data['total'] if data['total'] > 0 else 0
                avg_score = data['avg_score']
                
                if success_rate < 0.7:
                    suggestions.append({
                        'type': 'agent_performance',
                        'agent': agent,
                        'issue': f'Low success rate: {success_rate:.1%}',
                        'suggestion': f'Consider providing additional training or resources for {agent}',
                        'priority': 'high' if success_rate < 0.5 else 'medium',
                        'confidence': min(0.9, data['total'] / 20.0)  # More data = higher confidence
                    })
                elif success_rate > 0.95:
                    suggestions.append({
                        'type': 'agent_performance',
                        'agent': agent,
                        'issue': f'Excellent success rate: {success_rate:.1%}',
                        'suggestion': f'Consider leveraging {agent}\'s expertise for mentoring or complex tasks',
                        'priority': 'low',
                        'confidence': min(0.9, data['total'] / 20.0)
                    })
                
                if data['total'] >= 5:
                    if avg_score < 60:  # Assuming score out of 100
                        suggestions.append({
                            'type': 'agent_performance',
                            'agent': agent,
                            'issue': f'Below average score: {avg_score:.1f}',
                            'suggestion': f'Review {agent}\'s task completion quality and provide feedback',
                            'priority': 'medium',
                            'confidence': min(0.9, data['total'] / 20.0)
                        })
        
        # Task type difficulty suggestions
        task_patterns = patterns['task_type_patterns']
        for task_type, data in task_patterns.items():
            if data['total'] >= 3:
                success_rate = data['passed'] / data['total'] if data['total'] > 0 else 0
                if success_rate < 0.6:
                    suggestions.append({
                        'type': 'task_type_difficulty',
                        'task_type': task_type,
                        'issue': f'Low success rate for {task_type} tasks: {success_rate:.1%}',
                        'suggestion': f'Consider breaking down {task_type} tasks into smaller subtasks or providing additional resources',
                        'priority': 'high' if success_rate < 0.4 else 'medium',
                        'confidence': min(0.9, data['total'] / 15.0)
                    })
        
        # Priority handling suggestions
        priority_patterns = patterns['priority_patterns']
        for priority, data in priority_patterns.items():
            if data['total'] >= 3:
                success_rate = data['passed'] / data['total'] if data['total'] > 0 else 0
                # We expect higher priority tasks to have higher success rates (more attention)
                # If priority 1 (highest) has lower success than priority 4 (lowest), that's an issue
                if priority == 1 and success_rate < 0.7:
                    suggestions.append({
                        'type': 'priority_handling',
                        'priority': priority,
                        'issue': f'Highest priority tasks have low success rate: {success_rate:.1%}',
                        'suggestion': 'Review handling of high-priority tasks - may need more resources or better definition',
                        'priority': 'high',
                        'confidence': min(0.9, data['total'] / 15.0)
                    })
        
        # Time-based suggestions (e.g., certain times of day have lower success)
        time_patterns = patterns['time_patterns']
        if time_patterns:
            # Find hours with unusually low success rates
            hour_success_rates = {}
            for hour, data in time_patterns.items():
                if data['total'] >= 3:
                    success_rate = data['passed'] / data['total'] if data['total'] > 0 else 0
                    hour_success_rates[hour] = success_rate
            
            if hour_success_rates:
                avg_success = sum(hour_success_rates.values()) / len(hour_success_rates)
                low_hours = [hour for hour, rate in hour_success_rates.items() if rate < avg_success * 0.7]
                if low_hours:
                    suggestions.append({
                        'type': 'time_based',
                        'issue': f'Lower verification success during hours: {sorted(low_hours)}',
                        'suggestion': 'Consider scheduling verifications outside these hours or investigating causes of temporal variation',
                        'priority': 'medium',
                        'confidence': 0.7
                    })
        
        # If no specific suggestions, add a general one
        if not suggestions:
            suggestions.append({
                'type': 'general',
                'issue': 'No strong patterns detected in current data',
                'suggestion': 'Continue collecting verification data to enable deeper insights',
                'priority': 'low',
                'confidence': 0.5
            })
        
        return suggestions
    
    def generate_insights(self) -> Dict[str, Any]:
        """Generate insights from the trained model"""
        if self.insights_model.get('training_samples', 0) == 0:
            # Try to train first
            train_result = self.train_model()
            if train_result['status'] != 'trained':
                return {
                    'error': 'Unable to generate insights - model not trained and insufficient data',
                    'train_result': train_result
                }
        
        # Generate insights based on current model
        patterns = self.insights_model['patterns']
        suggestions = self.insights_model['improvement_suggestions']
        
        # Calculate overall statistics
        total_verifications = self.insights_model['training_samples']
        
        # Agent performance summary
        agent_summary = {}
        for agent, data in patterns['agent_performance_patterns'].items():
            if data['total'] > 0:
                success_rate = data['passed'] / data['total']
                agent_summary[agent] = {
                    'total': data['total'],
                    'passed': data['passed'],
                    'failed': data['failed'],
                    'success_rate': success_rate,
                    'avg_score': data['avg_score']
                }
        
        # Task type summary
        task_type_summary = {}
        for task_type, data in patterns['task_type_patterns'].items():
            if data['total'] > 0:
                success_rate = data['passed'] / data['total']
                task_type_summary[task_type] = {
                    'total': data['total'],
                    'passed': data['passed'],
                    'failed': data['failed'],
                    'success_rate': success_rate,
                    'avg_score': data['avg_score']
                }
        
        # Priority summary
        priority_summary = {}
        for priority, data in patterns['priority_patterns'].items():
            if data['total'] > 0:
                success_rate = data['passed'] / data['total']
                priority_summary[priority] = {
                    'total': data['total'],
                    'passed': data['passed'],
                    'failed': data['failed'],
                    'success_rate': success_rate,
                    'avg_score': data['avg_score']
                }
        
        insights = {
            'timestamp': datetime.now().isoformat(),
            'model_info': {
                'version': self.insights_model.get('version'),
                'last_updated': self.insights_model.get('last_updated'),
                'training_samples': total_verifications
            },
            'patterns_discovered': {
                'agent_performance': agent_summary,
                'task_type_performance': task_type_summary,
                'priority_performance': priority_summary,
                'time_patterns_available': len(patterns['time_patterns']) > 0
            },
            'improvement_suggestions': suggestions,
            'overall_health': self._calculate_overall_health(patterns),
            'recommendations': self._generate_recommendations(suggestions, patterns)
        }
        
        # Save insights
        with open(self.insights_file, 'w') as f:
            json.dump(insights, f, indent=2)
        
        return insights
    
    def _calculate_overall_health(self, patterns: Dict) -> Dict[str, Any]:
        """Calculate overall system health from patterns"""
        agent_patterns = patterns['agent_performance_patterns']
        if not agent_patterns:
            return {'status': 'unknown', 'score': 0.5}
        
        # Calculate weighted average success rate
        total_tasks = 0
        weighted_success = 0.0
        
        for agent, data in agent_patterns.items():
            total = data['total']
            if total > 0:
                success_rate = data['passed'] / data['total']
                weighted_success += success_rate * total
                total_tasks += total
        
        overall_success_rate = weighted_success / total_tasks if total_tasks > 0 else 0.5
        
        # Convert to health score (0-1)
        health_score = overall_success_rate  # Already 0-1
        
        if health_score >= 0.9:
            status = 'excellent'
        elif health_score >= 0.8:
            status = 'good'
        elif health_score >= 0.7:
            status = 'fair'
        elif health_score >= 0.6:
            status = 'poor'
        else:
            status = 'critical'
        
        return {
            'status': status,
            'score': health_score,
            'success_rate': overall_success_rate
        }
    
    def _generate_recommendations(self, suggestions: List[Dict], patterns: Dict) -> List[str]:
        """Generate high-level recommendations based on insights"""
        recommendations = []
        
        # Count suggestions by priority and type
        high_priority = [s for s in suggestions if s.get('priority') == 'high']
        medium_priority = [s for s in suggestions if s.get('priority') == 'medium']
        low_priority = [s for s in suggestions if s.get('priority') == 'low']
        
        if high_priority:
            recommendations.append(f"Address {len(high_priority)} high-priority issues immediately")
            # Add specific high-priority suggestions
            for suggestion in high_priority[:2]:  # Top 2
                recommendations.append(f"  - {suggestion['suggestion']}")
        
        if medium_priority:
            recommendations.append(f"Review {len(medium_priority)} medium-priority improvement areas")
        
        # Add general recommendations
        recommendations.extend([
            "Continue collecting verification data to improve insight accuracy",
            "Consider implementing automated feedback loops based on these insights",
            "Regularly review and update the insight model as new data arrives",
            "Share insights with team leads to drive continuous improvement"
        ])
        
        return recommendations[:8]  # Limit to top 8

def main():
    """Main entry point for the AI Verification Insight System"""
    insight_system = AIVerificationInsightSystem()
    
    print("Training AI verification insight model...")
    train_result = insight_system.train_model()
    print(f"Training result: {train_result['status']}")
    if train_result['status'] == 'trained':
        print(f"  - Trained on {train_result.get('records_available', 0)} records")
        print(f"  - Patterns found: {train_result.get('patterns_found', {})}")
    
    print("\nGenerating insights...")
    insights = insight_system.generate_insights()
    
    if 'error' in insights:
        print(f"Error: {insights['error']}")
        return False
    
    print(f"\nAI Verification Insight Generation Complete")
    print(f"Timestamp: {insights['timestamp']}")
    print(f"Training samples: {insights['model_info']['training_samples']}")
    print(f"Overall health: {insights['overall_health']['status']} ({insights['overall_health']['score']*100:.0f}%)")
    
    print(f"\nImprovement Suggestions ({len(insights['improvement_suggestions'])}):")
    for i, suggestion in enumerate(insights['improvement_suggestions'][:5], 1):
        print(f"  {i}. [{suggestion['priority'].upper()}] {suggestion['suggestion']}")
        print(f"      Issue: {suggestion['issue']}")
    
    if insights['recommendations']:
        print("\nRecommendations:")
        for rec in insights['recommendations'][:3]:
            print(f"  - {rec}")
    
    print(f"\nInsights saved to: {insight_system.insights_file}")
    return True

if __name__ == "__main__":
    main()