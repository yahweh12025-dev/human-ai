#!/usr/bin/env python3
"""
Human AI: Continuous Improvement Orchestrator
Reads targets from improvements.txt and drives the Researcher Agent to execute them.
"""

import asyncio
import os
import sys
from datetime import datetime
from researcher_agent import HumanAIResearcher

# Constants
IMPROVEMENTS_FILE = "/home/ubuntu/human-ai/improvements.txt"
LOG_FILE = "/home/ubuntu/human-ai/improvement.log"
MAX_LOG_SIZE = 1 * 1024 * 1024  # 1MB

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    
    # Rotate log if too large
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
        os.rename(LOG_FILE, f"{LOG_FILE}.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
    with open(LOG_FILE, "a") as f:
        f.write(entry + "\n")

async def run_cycle():
    log_message("🚀 Starting Human AI Improvement Cycle...")
    
    agent = HumanAIResearcher()
    
    # Check basic connectivity
    status = await agent.check_status()
    log_message(f"📊 System Status: {status}")
    
    if status.get("openclaw_gateway") == "❌ Down":
        log_message("⚠️ Warning: OpenClaw Gateway is down. Falling back to local Ollama.")

    if not os.path.exists(IMPROVEMENTS_FILE):
        log_message(f"❌ Improvements file not found: {IMPROVEMENTS_FILE}")
        return

    with open(IMPROVEMENTS_FILE, "r") as f:
        topics = [line.strip() for line in f.readlines() if line.strip()]

    if not topics:
        log_message("✨ No improvement topics found in improvements.txt")
        return

    for topic in topics:
        log_message(f"🔧 Processing topic: {topic}")
        try:
            # We trigger the research function directly from the agent
            result = await agent.research(topic)
            log_message(f"✅ Research completed for {topic}. Report saved to outputs/")
            
            # Optionally trigger a build if the topic contains "implement" or "code"
            if any(word in topic.lower() for word in ["implement", "code", "build", "create"]):
                log_message(f"🔨 Triggering implementation for {topic}...")
                build_res = await agent.build(f"Implement the following based on research: {topic}")
                log_message(f"Build result: {build_res}")
                
        except Exception as e:
            log_message(f"❌ Error processing {topic}: {str(e)}")

    log_message("✅ Continuous improvement cycle completed.")

if __name__ == "__main__":
    try:
        asyncio.run(run_cycle())
    except KeyboardInterrupt:
        pass
