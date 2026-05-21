#!/usr/bin/env python3
"""
Autonomous Development Service
Runs the development loop as a service that can be managed
"""

import sys
import os
import time
import signal
import threading
from datetime import datetime

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dev_loop_coordinator import AutonomousDevLoop

class AutonomousDevService:
    def __init__(self):
        self.dev_loop = None
        self.running = False
        
    def start(self):
        """Start the autonomous development service"""
        print("🚀 Starting Autonomous Development Service...")
        self.running = True
        
        # Initialize the development loop
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dev_loop = AutonomousDevLoop(repo_root)
        
        # Start the loop
        self.dev_loop.start_loop()
        
        print("✅ Autonomous Development Service started")
        print("💡 Service will run continuously until stopped")
        print("📊 Monitor progress with: tail -f autonomous_dev/dev_loop_stats.json")
        
        # Keep the main thread alive
        try:
            while self.running:
                time.sleep(10)
                # Print status every 5 minutes
                if int(time.time()) % 300 == 0:
                    stats = self.dev_loop.stats
                    print(f"💓 Service heartbeat - {datetime.now().strftime('%H:%M:%S')} | "
                          f"Tasks: {stats['tasks_processed']} | "
                          f"Success: {stats['successful_tasks']} | "
                          f"Failed: {stats['failed_tasks']}")
        except KeyboardInterrupt:
            print("\n🛑 Received shutdown signal...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the autonomous development service"""
        print("🛑 Stopping Autonomous Development Service...")
        self.running = False
        if self.dev_loop:
            self.dev_loop.stop_loop()
        print("✅ Autonomous Development Service stopped")

def main():
    service = AutonomousDevService()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\n📡 Received signal {signum}, shutting down gracefully...")
        service.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the service
    service.start()

if __name__ == "__main__":
    main()
