#!/usr/bin/env python3
"""
Intelligent Documentation Evolution System
Automatically updates docs based on code changes and verification results
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any
import hashlib
import re

class IntelligentDocEvolutionSystem:
    def __init__(self, data_dir: str = "/home/yahwehatwork/human-ai"):
        self.data_dir = data_dir
        self.docs_dir = os.path.join(data_dir, "docs")
        self.cache_dir = os.path.join(data_dir, "docs/verification/.doc_evolution_cache")
        self.report_file = os.path.join(self.docs_dir, "verification/doc_evolution_report.json")
        self.ensure_directories()
    
    def ensure_directories(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.report_file), exist_ok=True)
    
    def get_file_hash(self, filepath: str) -> str:
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def scan_code_changes(self, since_hours: int = 24) -> List[Dict]:
        """Scan for code changes in the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=since_hours)
        changed_files = []
        
        # Define code directories and extensions
        code_dirs = ['agents', 'core', 'scripts', 'infrastructure', 'validation', 'research', 'data']
        code_extensions = {'.py', '.sh', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs'}
        
        for code_dir in code_dirs:
            dir_path = os.path.join(self.data_dir, code_dir)
            if not os.path.exists(dir_path):
                continue
            for root, dirs, files in os.walk(dir_path):
                # Skip certain directories
                dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', '.venv', 'env', 'build', 'dist']]
                for file in files:
                    filepath = os.path.join(root, file)
                    ext = os.path.splitext(file)[1].lower()
                    if ext in code_extensions:
                        try:
                            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                            if mtime > cutoff_time:
                                changed_files.append({
                                    'path': filepath,
                                    'relative': os.path.relpath(filepath, self.data_dir),
                                    'modified': mtime.isoformat(),
                                    'hash': self.get_file_hash(filepath),
                                    'size': os.path.getsize(filepath)
                                })
                        except (OSError, FileNotFoundError):
                            continue
        return changed_files
    
    def scan_documentation_files(self) -> List[Dict]:
        """Scan all documentation files"""
        doc_files = []
        doc_dirs = ['docs', 'knowledge']
        doc_extensions = {'.md', '.rst', '.txt', '.docx'}
        
        for doc_dir in doc_dirs:
            dir_path = os.path.join(self.data_dir, doc_dir)
            if not os.path.exists(dir_path):
                continue
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', '.venv', 'env', 'build', 'dist']]
                for file in files:
                    filepath = os.path.join(root, file)
                    ext = os.path.splitext(file)[1].lower()
                    if ext in doc_extensions:
                        try:
                            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                            doc_files.append({
                                'path': filepath,
                                'relative': os.path.relpath(filepath, self.data_dir),
                                'modified': mtime.isoformat(),
                                'hash': self.get_file_hash(filepath),
                                'size': os.path.getsize(filepath)
                            })
                        except (OSError, FileNotFoundError):
                            continue
        return doc_files
    
    def load_cache(self) -> Dict[str, str]:
        """Load cached file hashes"""
        cache_file = os.path.join(self.cache_dir, 'file_hashes.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_cache(self, cache: Dict[str, str]):
        """Save file hashes to cache"""
        cache_file = os.path.join(self.cache_dir, 'file_hashes.json')
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
    
    def identify_affected_documentation(self, changed_code: List[Dict]) -> List[Dict]:
        """Identify which documentation files might be affected by code changes"""
        affected = []
        
        for code_change in changed_code:
            code_path = code_change['relative']
            # Generate possible documentation paths
            # Remove extension and add .md
            base_without_ext = os.path.splitext(code_path)[0]
            possible_docs = [
                base_without_ext + '.md',
                os.path.join('docs', code_path + '.md'),
                os.path.join('docs', os.path.splitext(code_path)[0] + '.md'),
                os.path.join('docs', 'api', os.path.basename(code_path) + '.md'),
                os.path.join('docs', 'agents', os.path.dirname(code_path), os.path.basename(code_path) + '.md') if '/' in code_path else None,
                os.path.join('docs', 'core', os.path.dirname(code_path), os.path.basename(code_path) + '.md') if '/' in code_path else None,
            ]
            # Filter out None
            possible_docs = [p for p in possible_docs if p is not None]
            
            # Check if any of these documentation files exist
            for doc_path in possible_docs:
                full_doc_path = os.path.join(self.data_dir, doc_path)
                if os.path.exists(full_doc_path):
                    affected.append({
                        'code_file': code_path,
                        'doc_file': doc_path,
                        'change_type': 'code_modification',
                        'code_modified': code_change['modified'],
                        'doc_hash': self.get_file_hash(full_doc_path)
                    })
        
        return affected
    
    def generate_documentation_update_suggestions(self, affected_docs: List[Dict]) -> List[Dict]:
        """Generate suggestions for updating documentation based on code changes"""
        suggestions = []
        
        for item in affected_docs:
            code_file = item['code_file']
            doc_file = item['doc_file']
            
            # Analyze the code change to suggest what to update
            suggestion = {
                'documentation_file': doc_file,
                'associated_code': code_file,
                'suggested_actions': [],
                'priority': 'medium',
                'reason': 'Code change detected, documentation may be out of sync'
            }
            
            # Determine what kind of documentation update might be needed
            if 'api' in code_file.lower() or '/agents/' in code_file.lower() or '/core/' in code_file.lower():
                suggestion['suggested_actions'].append("Update API documentation if code defines interfaces or functions")
                suggestion['suggested_actions'].append("Update usage examples if function signatures changed")
                suggestion['priority'] = 'high'
            
            if 'test' in code_file.lower():
                suggestion['suggested_actions'].append("Update test documentation or test plan")
                suggestion['suggested_actions'].append("Verify test coverage documentation")
            
            if 'config' in code_file.lower() or '.yaml' in code_file or '.yml' in code_file:
                suggestion['suggested_actions'].append("Update configuration documentation")
                suggestion['suggested_actions'].append("Update environment setup instructions")
                suggestion['priority'] = 'high'
            
            if 'script' in code_file.lower() or '/scripts/' in code_file:
                suggestion['suggested_actions'].append("Update script usage documentation")
                suggestion['suggested_actions'].append("Update command-line interface help")
            
            if not suggestion['suggested_actions']:
                suggestion['suggested_actions'].append("Review documentation for accuracy against code changes")
                suggestion['suggested_actions'].append("Update any outdated examples or descriptions")
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def run_evolution_check(self, since_hours: int = 24) -> Dict[str, Any]:
        """Run the documentation evolution check"""
        print(f"Scanning for code changes in the last {since_hours} hours...")
        changed_code = self.scan_code_changes(since_hours=since_hours)
        print(f"Found {len(changed_code)} changed code files.")
        
        print("Scanning documentation files...")
        doc_files = self.scan_documentation_files()
        print(f"Found {len(doc_files)} documentation files.")
        
        print("Identifying affected documentation...")
        affected_docs = self.identify_affected_documentation(changed_code)
        print(f"Identified {len(affected_docs)} potentially affected documentation files.")
        
        print("Generating update suggestions...")
        suggestions = self.generate_documentation_update_suggestions(affected_docs)
        
        # Load previous cache to see what's new
        old_cache = self.load_cache()
        new_cache = {}
        for item in changed_code:
            new_cache[item['path']] = item['hash']
        for item in doc_files:
            new_cache[item['path']] = item['hash']
        
        # Determine what's new or changed
        newly_changed = []
        for path, hash_val in new_cache.items():
            if path not in old_cache or old_cache[path] != hash_val:
                newly_changed.append(path)
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'scan_period_hours': since_hours,
            'changed_code_count': len(changed_code),
            'documentation_files_count': len(doc_files),
            'affected_documentation_count': len(affected_docs),
            'newly_changed_files': len(newly_changed),
            'changed_code_files': changed_code[:10],  # Limit output
            'affected_documentation': affected_docs[:10],
            'suggestions': suggestions[:20],  # Limit output
            'recommendations': self._generate_recommendations(changed_code, affected_docs, suggestions)
        }
        
        # Save report
        with open(self.report_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Update cache
        self.save_cache(new_cache)
        
        return result
    
    def _generate_recommendations(self, changed_code: List[Dict], affected_docs: List[Dict], suggestions: List[Dict]) -> List[str]:
        """Generate recommendations based on the analysis"""
        recommendations = []
        
        if len(changed_code) == 0:
            recommendations.append("No code changes detected in the scan period - documentation is likely up to date")
            return recommendations
        
        if len(affected_docs) == 0:
            recommendations.append("Code changes detected but no obvious documentation mappings found")
            recommendations.append("Consider manually reviewing documentation for any implicit impacts")
        else:
            recommendations.append(f"{len(affected_docs)} documentation files may need updates based on code changes")
            high_priority = sum(1 for s in suggestions if s.get('priority') == 'high')
            if high_priority > 0:
                recommendations.append(f"{high_priority} documentation updates are high priority")
        
        # Add specific recommendations
        if len(changed_code) > 10:
            recommendations.append("Large number of code changes detected - consider batching documentation updates")
        
        # Check for critical paths
        critical_paths = ['agents/', 'core/', 'scripts/', 'infrastructure/']
        critical_changes = [c for c in changed_code if any(cp in c['relative'] for cp in critical_paths)]
        if len(critical_changes) > len(changed_code) * 0.5:
            recommendations.append("Majority of changes are in core system areas - documentation update is critical")
        
        recommendations.append("Run documentation evolution check regularly (e.g., daily) to keep docs in sync")
        recommendations.append("Consider integrating this check into CI/CD pipeline for automatic documentation updates")
        
        return recommendations

def main():
    """Main entry point for the Intelligent Documentation Evolution System"""
    evolver = IntelligentDocEvolutionSystem()
    result = evolver.run_evolution_check(since_hours=24)
    
    print(f"\nIntelligent Documentation Evolution Check Complete")
    print(f"Timestamp: {result['timestamp']}")
    print(f"Code changes scanned: {result['changed_code_count']}")
    print(f"Documentation files: {result['documentation_files_count']}")
    print(f"Potentially affected docs: {result['affected_documentation_count']}")
    print(f"Newly changed files: {result['newly_changed_files']}")
    
    if result['recommendations']:
        print("\nRecommendations:")
        for rec in result['recommendations'][:5]:
            print(f"  - {rec}")
    
    print(f"\nReport saved to: {evolver.report_file}")
    return True

if __name__ == "__main__":
    main()