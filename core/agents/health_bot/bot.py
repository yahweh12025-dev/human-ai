
import asyncio
import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/home/ubuntu/human-ai/core/agents/health_bot/bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SwarmHealthBot")

class SwarmHealthMonitor:
    def __init__(self, base_dir="/home/ubuntu/human-ai"):
        self.base_dir = Path(base_dir)

    def get_gateway_status(self):
        try:
            res = subprocess.run(["systemctl", "is-active", "openclaw-gateway.service"], 
                                 capture_output=True, text=True)
            status = res.stdout.strip()
            return "✅ Active" if status == "active" else f"❌ {status}"
        except Exception as e:
            logger.error(f"Gateway status error: {e}")
            return f"❓ Error: {e}"

    def get_cron_status(self):
        try:
            res = subprocess.run(["hermes", "cron", "list"], capture_output=True, text=True)
            return res.stdout.strip() or "No active cron jobs"
        except Exception as e:
            logger.error(f"Cron status error: {e}")
            return f"❓ Error: {e}"

    def get_todo_progress(self):
        try:
            # Update path to correct config location
            todo_path = self.base_dir / "infrastructure/configs/todo.json"
            if not todo_path.exists():
                return "Todo file not found"
            with open(todo_path, 'r') as f:
                data = json.load(f)
            
            completed = len(data.get('completed', []))
            pending = len([t for t in data.get('pending', []) if isinstance(t, dict)])
            in_progress = len(data.get('in_progress', []))
            
            return f"Tasks: {completed} Completed | {in_progress} In Progress | {pending} Pending"
        except Exception as e:
            logger.error(f"Todo progress error: {e}")
            return f"❓ Error: {e}"

    def get_openclaw_sessions(self):
        try:
            res = subprocess.run(["openclaw", "sessions"], capture_output=True, text=True)
            lines = res.stdout.strip().split('\n')
            return "\n".join(lines[:10]) if lines else "No sessions found"
        except Exception as e:
            logger.error(f"OpenClaw sessions error: {e}")
            return f"❓ Error: {e}"

    def generate_report(self):
        report = [
            "🤖 **SWARM HEALTH REPORT** 🤖",
            f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🌐 Gateway: {self.get_gateway_status()}",
            f"📝 {self.get_todo_progress()}",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "🕒 **Active Cron Jobs:**",
            self.get_cron_status(),
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "👥 **OpenClaw Sessions:**",
            self.get_openclaw_sessions(),
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "✨ *Status: Operational*"
        ]
        return "\n".join(report)

class SwarmHealthBot:
    def __init__(self):
        self.monitor = SwarmHealthMonitor()

    async def send_message(self, text: str):
        # Use hermes chat -q to send messages via the agent's toolset
        # This is the most reliable way to route through the gateway
        cmd = [
            "hermes", "chat", "-q", f"send a message to telegram saying '{text}'"
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                logger.info("Heartbeat sent successfully via hermes chat")
            else:
                logger.error(f"Failed to send heartbeat: {stderr.decode()}")
        except Exception as e:
            logger.error(f"Exception while sending telegram message: {e}")

    async def run_heartbeat(self):
        logger.info("Generating and sending heartbeat report...")
        report = self.monitor.generate_report()
        await self.send_message(report)

if __name__ == "__main__":
    bot = SwarmHealthBot()
    asyncio.run(bot.run_heartbeat())
