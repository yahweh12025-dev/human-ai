"""
Unified health monitoring system for the human-ai swarm
Integrates system health, service health, and application-specific monitoring
"""

import os
import sys
import json
import subprocess
import psutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class UnifiedHealthMonitor:
    """Unified health monitor for the human-ai swarm system"""
    
    def __init__(self, base_dir: str = "/home/yahwehatwork/human-ai"):
        self.base_dir = Path(base_dir)
        self.logger = logging.getLogger(f"{__name__}.UnifiedHealthMonitor")
        
        # Import the detailed health checker
        sys.path.insert(0, str(self.base_dir))
        try:
            from core.utils.swarm_health_check import SwarmHealthChecker
            self.detail_checker = SwarmHealthChecker(base_dir)
        except ImportError as e:
            self.logger.warning(f"Could not import detailed health checker: {e}")
            self.detail_checker = None
    
    def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        if self.detail_checker:
            return self.detail_checker.run_all_checks()
        else:
            # Fallback to basic implementation
            return self._basic_health_check()
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a condensed health summary"""
        health_data = self.get_comprehensive_health()
        
        summary = {
            "timestamp": health_data.get("timestamp"),
            "overall_status": health_data.get("overall_status", "unknown"),
            "key_metrics": {},
            "alerts": [],
            "warnings": []
        }
        
        # Extract key metrics
        system = health_data.get("system", {})
        if system:
            summary["key_metrics"]["cpu_percent"] = system.get("cpu_percent", 0)
            summary["key_metrics"]["memory_percent"] = system.get("memory_percent", 0)
            summary["key_metrics"]["disk_percent"] = system.get("disk_percent", 0)
        
        # Extract alerts and warnings
        failed_checks = health_data.get("failed_checks", [])
        for check in failed_checks:
            summary["alerts"].append(f"Health check failed: {check}")
        
        # Check for warnings in various systems
        disk_space = health_data.get("disk_space", {})
        if isinstance(disk_space, dict) and "directories" in disk_space:
            for dir_info in disk_space["directories"]:
                if dir_info.get("status") == "warning":
                    summary["warnings"].append(f"High disk usage in {dir_info['name']}: {dir_info.get('percent_used', 0):.1f}%")
        
        logs = health_data.get("logs", {})
        if isinstance(logs, dict) and "log_files" in logs:
            for log_info in logs["log_files"]:
                if log_info.get("status") == "warning":
                    summary["warnings"].append(f"Log file issue: {log_info['name']}")
                elif log_info.get("status") == "error":
                    summary["alerts"].append(f"Log file error: {log_info['name']}")
        
        return summary
    
    def is_healthy(self) -> bool:
        """Quick health check - returns True if system is healthy"""
        health_data = self.get_comprehensive_health()
        return health_data.get("overall_status") == "healthy"
    
    def get_service_status(self) -> Dict[str, str]:
        """Get status of key services"""
        health_data = self.get_comprehensive_health()
        services = health_data.get("services", {})
        
        if isinstance(services, dict) and "processes" in services:
            status_dict = {}
            for proc in services["processes"]:
                status_dict[proc["name"]] = proc["status"]
            return status_dict
        return {}
    
    def get_resource_usage(self) -> Dict[str, float]:
        """Get current resource usage"""
        health_data = self.get_comprehensive_health()
        system = health_data.get("system", {})
        
        return {
            "cpu_percent": system.get("cpu_percent", 0.0),
            "memory_percent": system.get("memory_percent", 0.0),
            "disk_percent": system.get("disk_percent", 0.0)
        }
    
    def _basic_health_check(self) -> Dict[str, Any]:
        """Fallback basic health check"""
        try:
            # Basic system check
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            status = "healthy"
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 95:
                status = "unhealthy"
            
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": status,
                "system": {
                    "status": status,
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent
                }
            }
        except Exception as e:
            self.logger.error(f"Basic health check failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "unhealthy",
                "error": str(e)
            }


def quick_health_check() -> bool:
    """Quick health check function for external use"""
    monitor = UnifiedHealthMonitor()
    return monitor.is_healthy()


def get_health_status() -> Dict[str, Any]:
    """Get health status dictionary"""
    monitor = UnifiedHealthMonitor()
    return monitor.get_comprehensive_health()


def get_health_summary() -> Dict[str, Any]:
    """Get condensed health summary"""
    monitor = UnifiedHealthMonitor()
    return monitor.get_health_summary()


if __name__ == "__main__":
    # Simple CLI interface
    import argparse
    
    parser = argparse.ArgumentParser(description='Check health of the human-ai swarm system')
    parser.add_argument('--summary', '-s', action='store_true', help='Show summary only')
    parser.add_argument('--json', '-j', action='store_true', help='Output as JSON')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode - only exit code')
    
    args = parser.parse_args()
    
    monitor = UnifiedHealthMonitor()
    
    if args.json:
        print(json.dumps(monitor.get_comprehensive_health(), indent=2))
    elif args.summary:
        summary = monitor.get_health_summary()
        print(f"Status: {summary['overall_status']}")
        if summary['key_metrics']:
            metrics = ", ".join([f"{k}: {v}%" for k, v in summary['key_metrics'].items()])
            print(f"Metrics: {metrics}")
        if summary['alerts']:
            print(f"Alerts: {'; '.join(summary['alerts'])}")
        if summary['warnings']:
            print(f"Warnings: {'; '.join(summary['warnings'])}")
    elif not args.quiet:
        monitor.detail_checker.print_report(detailed=True) if monitor.detail_checker else print("Detailed checker not available")
    
    # Exit with appropriate code
    sys.exit(0 if monitor.is_healthy() else 1)