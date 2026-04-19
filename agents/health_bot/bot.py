
import asyncio
import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

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
            return f"❓ Error: {e}"

    def get_cron_status(self):
        try:
            res = subprocess.run(["hermes", "cron", "list"], capture_output=True, text=True)
            return res.stdout.strip() or "No active cron jobs"
        except Exception as e:
            return f"❓ Error: {e}"

    def get_todo_progress(self):
        try:
            todo_path = self.base_dir / "todo.json"
            if not todo_path.exists():
                return "Todo file not found"
            with open(todo_path, 'r') as f:
                data = json.load(f)
            
            completed = len(data.get('completed', []))
            pending = len(data.get('pending', []))
            in_progress = len(data.get('in_progress', []))
            
            return f"Tasks: {completed} Completed | {in_progress} In Progress | {pending} Pending"
        except Exception as e:
            return f"❓ Error: {e}"

    def get_openclaw_sessions(self):
        try:
            res = subprocess.run(["openclaw", "sessions"], capture_output=True, text=True)
            lines = res.stdout.strip().split('\n')
            return "\n".join(lines[:10]) if lines else "No sessions found"
        except Exception as e:
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
        cmd = [
            "hermes", "send_message",
            "--target", "telegram",
            "--message", text
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
        except Exception as e:
            print(f"Error sending telegram message: {e}")

    async def run_heartbeat(self):
        print("Sending heartbeat report...")
        report = self.monitor.generate_report()
        await self.send_message(report)

if __name__ == "__main__":
    bot = SwarmHealthBot()
    asyncio.run(bot.run_heartbeat())
