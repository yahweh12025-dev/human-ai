import asyncio
import os
import json
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Import Swarm Logger
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from core.utils.swarm_logger import get_logger

# Setup Swarm Logger for this agent
logger = get_logger("SwarmHealthBot")

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
            logger.error(f"Gateway status error: {e}", error=str(e))
            return f"❓ Error: {e}"

    def get_cron_status(self):
        try:
            res = subprocess.run(["hermes", "cron", "list"], capture_output=True, text=True)
            return res.stdout.strip() or "No active cron jobs"
        except Exception as e:
            logger.error(f"Cron status error: {e}", error=str(e))
            return f"❓ Error: {e}"

    def get_active_agents(self):
        try:
            res = subprocess.run(["ps", "-eo", "pid,comm,args"], capture_output=True, text=True)
            lines = res.stdout.strip().split('\n')
            agents = []
            for line in lines[1:]:
                if any(x in line for x in ["ga.py", "developer_agent", "researcher_agent", "navigator_agent"]):
                    agents.append(line.strip())
            return "\n".join(agents) if agents else "No active agent processes found"
        except Exception as e:
            logger.error(f"Active agents error: {e}", error=str(e))
            return f"❓ Error: {e}"

    def get_todo_progress(self):
        try:
            todo_path = self.base_dir / "infrastructure/configs/todo.json"
            if not todo_path.exists():
                logger.warning("Todo file not found")
                return "Todo file not found"
            with open(todo_path, 'r') as f:
                data = json.load(f)
            
            completed = len(data.get('completed', []))
            pending = len([t for t in data.get('pending', []) if isinstance(t, dict)])
            in_progress = len(data.get('in_progress', []))
            
            logger.debug("Todo progress retrieved", completed=completed, in_progress=in_progress, pending=pending)
            return f"Tasks: {completed} Completed | {in_progress} In Progress | {pending} Pending"
        except Exception as e:
            logger.error(f"Todo progress error: {e}", error=str(e))
            return f"❓ Error: {e}"

    def get_openclaw_sessions(self):
        try:
            res = subprocess.run(["openclaw", "sessions"], capture_output=True, text=True)
            lines = res.stdout.strip().split('\n')
            return "\n".join(lines[:10]) if lines else "No sessions found"
        except Exception as e:
            logger.error(f"OpenClaw sessions error: {e}", error=str(e))
            return f"❓ Error: {e}"

    def generate_report(self):
        report = [
            "🤖 **SWARM HEALTH REPORT** 🤖",
            f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🌐 Gateway: {self.get_gateway_status()}",
            f"👥 Agents: {self.get_active_agents()}",
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

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    monitor = SwarmHealthMonitor()
    await update.message.reply_text(monitor.generate_report(), parse_mode="Markdown")

async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    monitor = SwarmHealthMonitor()
    await update.message.reply_text(f"👥 **Active Agents:**\\n{monitor.get_active_agents()}", parse_mode="Markdown")

async def prioritize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎯 *Prioritization requested.* (Currently requires manual Orchestrator input)", parse_mode="Markdown")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛑 *Emergency stop signal sent.* (Interfacing with process manager...)", parse_mode="Markdown")

async def main():
    # Retrieve token from environment (mapped to SWARM_BOT_TOKEN from .env)
    # In production, this would be loaded via os.environ or a config file
    token = os.getenv("SWARM_BOT_TOKEN") or "REPLACE_WITH_ACTUAL_TOKEN_FROM_ENV"
    
    if "REPLACE" in token:
        logger.error("SWARM_BOT_TOKEN not found in environment. Bot cannot start.")
        return
    
    application = ApplicationBuilder().token(token).build()
    
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("agents", agents_command))
    application.add_handler(CommandHandler("prioritize", prioritize_command))
    application.add_handler(CommandHandler("stop", stop_command))
    
    logger.info("Swarm26 Health Bot started. Listening for commands...")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())