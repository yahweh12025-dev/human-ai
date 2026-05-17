#!/usr/bin/env python3
"""
Automated Documentation Drift Detector
Identifies when code changes require documentation updates
"""

import os
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Set
import fnmatch

class DocumentationDriftDetector:
    def __init__(self, repo_root: str = "/home/yahwehatwork/human-ai"):
        self.repo_root = repo_root
        self.cache_file = os.path.join(repo_root, "docs/verification/.doc_drift_cache.json")
        self.report_file = os.path.join(repo_root, "docs/verification/documentation_drift_report.json")
        
        # File extensions to monitor
        self.code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs'}
        self.doc_extensions = {'.md', '.rst', '.txt', '.docx'}
        
        # Directories to exclude
        self.exclude_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'env', 'build', 'dist'}
    
    def get_file_hash(self, filepath: str) -> str:
        """Calculate MD5 hash of a file"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def scan_files(self) -> Dict[str, str]:
        """Scan repository for code and documentation files"""
        code_files = {}
        doc_files = {}
        
        for root, dirs, files in os.walk(self.repo_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            
            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, self.repo_root)
                
                ext = os.path.splitext(file)[1].lower()
                if ext in self.code_extensions:
                    code_files[rel_path] = self.get_file_hash(filepath)
                elif ext in self.doc_extensions:
                    doc_files[rel_path] = self.get_file_hash(filepath)
        
        return {'code': code_files, 'docs': doc_files}
    
    def load_cache(self) -> Dict:
        """Load previous scan results"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'code': {}, 'docs': {}, 'timestamp': ''}
    
    def save_cache(self, data: Dict):
        """Save current scan results"""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        data['timestamp'] = datetime.now().isoformat()
        with open(self.cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def detect_drift(self) -> Dict:
        """Detect documentation drift between code and docs"""
        current = self.scan_files()
        cache = self.load_cache()
        
        drift_report = {
            'timestamp': datetime.now().isoformat(),
            'new_code_files': [],
            'modified_code_files': [],
            'potentially_affected_docs': [],
            'stale_docs': [],
            'recommendations': []
        }
        
        # Find new and modified code files
        for file_path, file_hash in current['code'].items():
            if file_path not in cache['code']:
                drift_report['new_code_files'].append(file_path)
            elif cache['code'][file_path] != file_hash:
                drift_report['modified_code_files'].append(file_path)
        
        # For each changed code file, find potentially affected documentation
        changed_files = drift_report['new_code_files'] + drift_report['modified_code_files']
        for code_file in changed_files:
            # Simple heuristic: look for docs with similar names or in related directories
            doc_name = os.path.splitext(os.path.basename(code_file))[0] + '.md'
            doc_dir = os.path.dirname(code_file).replace('agents/', 'docs/agents/').replace('core/', 'docs/core/').replace('scripts/', 'docs/scripts/')
            
            potential_docs = [
                os.path.join(doc_dir, doc_name),
                os.path.join('docs', code_file + '.md'),
                os.path.join('docs', os.path.splitext(code_file)[0] + '.md')
            ]
            
            for doc_path in potential_docs:
                # Normalize path
                doc_path = doc_path.replace('//', '/')
                if doc_path in current['docs'] or doc_path in cache['docs']:
                    drift_report['potentially_affected_docs'].append({
                        'code_file': code_file,
                        'doc_file': doc_path
                    })
        
        # Find stale documentation (docs without recent code changes)
        for doc_file, doc_hash in current['docs'].items():
            # Check if this doc has a corresponding code file that changed recently
            has_recent_code_change = False
            for code_file in drift_report['modified_code_files']:
                # Simple mapping check
                if (doc_file.replace('docs/', '').replace('.md', '.py') == code_file or
                    doc_file.replace('docs/', '').replace('.md', '.js') == code_file):
                    has_recent_code_change = True
                    break
            
            if not has_recent_code_change and doc_file in cache['docs']:
                # Check if doc is older than code (simplified)
                drift_report['stale_docs'].append(doc_file)
        
        # Generate recommendations
        if drift_report['new_code_files']:
            drift_report['recommendations'].append(
                f"Create documentation for {len(drift_report['new_code_files'])} new code files"
            )
        
        if drift_report['modified_code_files']:
            drift_report['recommendations'].append(
                f"Update documentation for {len(drift_report['modified_code_files'])} modified code files"
            )
        
        if drift_report['stale_docs']:
            drift_report['recommendations'].append(
                f"Review {len(drift_report['stale_docs'])} potentially stale documentation files"
            )
        
        return drift_report
    
    def run_check(self) -> Dict:
        """Run the documentation drift detection and save results"""
        report = self.detect_drift()
        
        # Save report
        os.makedirs(os.path.dirname(self.report_file), exist_ok=True)
        with open(self.report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Update cache
        current = self.scan_files()
        self.save_cache(current)
        
        return report

if __name__ == "__main__":
    detector = DocumentationDriftDetector()
    report = detector.run_check()
    
    print(f"Documentation drift check completed at {report['timestamp']}")
    print(f"New code files: {len(report['new_code_files'])}")
    print(f"Modified code files: {len(report['modified_code_files'])}")
    print(f"Potentially affected docs: {len(report['potentially_affected_docs'])}")
    print(f"Stale docs: {len(report['stale_docs'])}")
    
    for rec in report['recommendations']:
        print(f"  - {rec}")