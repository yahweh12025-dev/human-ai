#!/usr/bin/env python3
"""
Automated Remediation Suggester
Suggests fixes when verification audits detect issues
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any

class AutomatedRemediationSuggester:
    def __init__(self, data_dir: str = "/home/yahwehatwork/human-ai"):
        self.data_dir = data_dir
        self.remediation_rules_path = os.path.join(data_dir, "scripts/remediation_rules.json")
        self.suggestion_log_path = os.path.join(data_dir, "scripts/remediation_suggestions.json")
        self._ensure_data_files()
    
    def _ensure_data_files(self):
        """Ensure data files exist"""
        os.makedirs(os.path.dirname(self.remediation_rules_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.suggestion_log_path), exist_ok=True)
        
        if not os.path.exists(self.remediation_rules_path):
            default_rules = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "rules": {
                    "missing_file": {
                        "pattern": ".*File not found.*|.*No such file or directory.*",
                        "suggestion": "Create the missing file or verify the file path",
                        "action": "create_file_if_missing",
                        "priority": "high"
                    },
                    "permission_denied": {
                        "pattern": ".*Permission denied.*|.*Access is denied.*",
                        "suggestion": "Check file permissions and run with appropriate privileges",
                        "action": "check_permissions",
                        "priority": "high"
                    },
                    "module_not_found": {
                        "pattern": ".*ModuleNotFoundError.*|.*ImportError.*No module named.*",
                        "suggestion": "Install missing Python package using pip",
                        "action": "install_package",
                        "priority": "high"
                    },
                    "syntax_error": {
                        "pattern": ".*SyntaxError.*|.*Invalid syntax.*",
                        "suggestion": "Review and fix syntax errors in the code",
                        "action": "review_syntax",
                        "priority": "high"
                    },
                    "timeout_error": {
                        "pattern": ".*timeout.*|.*TimeoutError.*",
                        "suggestion": "Increase timeout values or optimize performance",
                        "action": "adjust_timeout",
                        "priority": "medium"
                    },
                    "connection_error": {
                        "pattern": ".*ConnectionError.*|.*Failed to establish connection.*",
                        "suggestion": "Check network connectivity and endpoint availability",
                        "action": "check_connectivity",
                        "priority": "medium"
                    },
                    "assertion_error": {
                        "pattern": ".*AssertionError.*",
                        "suggestion": "Review assertion conditions and test data validity",
                        "action": "review_assertions",
                        "priority": "medium"
                    }
                }
            }
            with open(self.remediation_rules_path, 'w') as f:
                json.dump(default_rules, f, indent=2)
        
        if not os.path.exists(self.suggestion_log_path):
            with open(self.suggestion_log_path, 'w') as f:
                json.dump({"suggestions": []}, f, indent=2)
    
    def load_rules(self) -> Dict[str, Any]:
        with open(self.remediation_rules_path, 'r') as f:
            return json.load(f)
    
    def analyze_issue(self, error_message: str, context: Dict = None) -> List[Dict]:
        """Analyze an error message and suggest remediation"""
        rules = self.load_rules()
        suggestions = []
        
        error_lower = error_message.lower()
        
        for rule_id, rule in rules.get("rules", {}).items():
            pattern = rule.get("pattern", "").lower()
            if pattern and pattern in error_lower:
                suggestion = {
                    "rule_id": rule_id,
                    "error_pattern": pattern,
                    "suggestion": rule.get("suggestion", ""),
                    "action": rule.get("action", ""),
                    "priority": rule.get("priority", "medium"),
                    "timestamp": datetime.now().isoformat(),
                    "context": context or {}
                }
                suggestions.append(suggestion)
        
        # If no specific rules matched, provide general suggestions
        if not suggestions:
            suggestions.append({
                "rule_id": "general_analysis",
                "error_pattern": "no_specific_match",
                "suggestion": "Review the error message and surrounding context for clues",
                "action": "manual_review",
                "priority": "low",
                "timestamp": datetime.now().isoformat(),
                "context": context or {}
            })
        
        return suggestions
    
    def suggest_remediation_for_verification_failure(self, verification_record: Dict) -> Dict[str, Any]:
        """Suggest remediation for a verification failure"""
        # Extract error information from verification record
        error_message = verification_record.get("error_message", "")
        error_details = verification_record.get("error_details", "")
        context = verification_record.get("context", {})
        
        full_error = f"{error_message} {error_details}".strip()
        
        suggestions = self.analyze_issue(full_error, context)
        
        remediation_plan = {
            "verification_id": verification_record.get("id", "unknown"),
            "task": verification_record.get("task", ""),
            "agent": verification_record.get("agent", ""),
            "timestamp": datetime.now().isoformat(),
            "error_analysis": {
                "error_message": error_message,
                "error_details": error_details
            },
            "suggestions": suggestions,
            "recommended_actions": self._prioritize_actions(suggestions)
        }
        
        # Log the suggestion
        self._log_suggestion(remediation_plan)
        
        return remediation_plan
    
    def _prioritize_actions(self, suggestions: List[Dict]) -> List[Dict]:
        """Prioritize remediation actions"""
        # Sort by priority: high > medium > low
        priority_order = {"high": 3, "medium": 2, "low": 1}
        
        sorted_suggestions = sorted(
            suggestions,
            key=lambda x: priority_order.get(x.get("priority", "low"), 0),
            reverse=True
        )
        
        # Return top 3 actions
        return sorted_suggestions[:3]
    
    def _log_suggestion(self, remediation_plan: Dict):
        """Log remediation suggestion"""
        with open(self.suggestion_log_path, 'r') as f:
            log = json.load(f)
        
        log["suggestions"].append(remediation_plan)
        
        # Keep last 1000 suggestions
        if len(log["suggestions"]) > 1000:
            log["suggestions"] = log["suggestions"][-1000:]
        
        with open(self.suggestion_log_path, 'w') as f:
            json.dump(log, f, indent=2)
    
    def get_suggestion_statistics(self) -> Dict[str, Any]:
        """Get statistics about remediation suggestions"""
        with open(self.suggestion_log_path, 'r') as f:
            log = json.load(f)
        
        with open(self.remediation_rules_path, 'r') as f:
            rules = json.load(f)
        
        suggestions = log.get("suggestions", [])
        
        # Count by priority
        priority_counts = {"high": 0, "medium": 0, "low": 0}
        for sug in suggestions:
            priority = sug.get("priority", "low")
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Count by action type
        action_counts = {}
        for sug in suggestions:
            action = sug.get("recommended_actions", [{}])[0].get("action", "unknown") if sug.get("recommended_actions") else "unknown"
            action_counts[action] = action_counts.get(action, 0) + 1
        
        return {
            "total_suggestions": len(suggestions),
            "priority_distribution": priority_counts,
            "action_distribution": action_counts,
            "available_rules": len(rules.get("rules", {})),
            "last_updated": rules.get("last_updated", "unknown")
        }

if __name__ == "__main__":
    suggester = AutomatedRemediationSuggester()
    
    # Test with sample error
    sample_verification = {
        "id": "V-TEST-001",
        "task": "Verify database connection",
        "agent": "Hermes",
        "error_message": "ConnectionError: Failed to establish connection to database",
        "error_details": "sqlite3.OperationalError: unable to open database file",
        "context": {"database_path": "/data/app.db", "attempt": 3}
    }
    
    remediation = suggester.suggest_remediation_for_verification_failure(sample_verification)
    
    print(f"Remediation Suggestions for {remediation['verification_id']}:")
    print(f"Task: {remediation['task']}")
    print(f"Agent: {remediation['agent']}")
    print(f"Error: {remediation['error_analysis']['error_message']}")
    
    print("\nTop Recommendations:")
    for i, action in enumerate(remediation['recommended_actions'], 1):
        print(f"  {i}. [{action['priority'].upper()}] {action['suggestion']}")
        print(f"     Action: {action['action']}")
    
    # Show statistics
    stats = suggester.get_suggestion_statistics()
    print(f"\nSuggestion Statistics:")
    print(f"Total suggestions logged: {stats['total_suggestions']}")
    print(f"Priority distribution: {stats['priority_distribution']}")