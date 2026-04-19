#!/usr/bin/env python3
"""
Swarm Health Bot: A Telegram bot for real-time monitoring, status checks, and steering
of the OpenClaw/Hermes agent swarm.
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Load environment variables
from dotenv import load_dotenv
load_dotenv("/home/ubuntu/human-ai/.env")

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SwarmHealthBot:
    def __init__(self):
        self.token = os.getenv('SWARM_BOT_TOKEN')  # Swarm bot token for @Swarm26_bot
        self.master_log_path = Path("/home/ubuntu/human-ai/master_log.json")
        self.outcome_log_path = Path("/home/ubuntu/human-ai/OUTCOME_LOG.md")
        self.todo_path = Path("/home/ubuntu/human-ai/todo.json")
        self.roadmap_path = Path("/home/ubuntu/human-ai/ROADMAP.md")
        self.team_spawner_path = Path("/home/ubuntu/human-ai/teams/team_spawner.py")
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
        
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up command handlers for the bot."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("agents", self.agents_command))
        self.application.add_handler(CommandHandler("logs", self.logs_command))
        self.application.add_handler(CommandHandler("outcomes", self.outcomes_command))
        self.application.add_handler(CommandHandler("prioritize", self.prioritize_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        self.application.add_handler(CommandHandler("export_logs", self.export_logs_command))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /start is issued."""
        user = update.effective_user
        await update.message.reply_html(
            rf"Hi {user.mention_html()}! I am the Swarm Health Bot. "
            "I provide real-time monitoring and steering for the OpenClaw/Hermes agent swarm.\n\n"
            "Use /help to see available commands.",
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /help is issued."""
        help_text = """
Available commands:
/start - Start the bot and see welcome message
/status - Get overall swarm health status
/agents - List active agent teams and their progress
/logs - Get latest entries from the Master Log
/outcomes - Get recent SUCCESS entries from Outcome Journal
/prioritize <task_id> - Prioritize a specific task in the queue
/stop <team_id> - Stop a specific agent team
/help - Show this help message
        """
        await update.message.reply_text(help_text)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get overall swarm health status."""
        try:
            # Read MasterLog for recent activity
            if self.master_log_path.exists():
                with open(self.master_log_path, 'r') as f:
                    master_log = json.load(f)
                recent_entries = master_log[-10:] if len(master_log) >= 10 else master_log
                entry_count = len(recent_entries)
            else:
                recent_entries = []
                entry_count = 0
            
            # Read TODO.json for task status
            if self.todo_path.exists():
                with open(self.todo_path, 'r') as f:
                    todo_data = json.load(f)
                pending_count = len([t for t in todo_data.get('pending', []) if t.get('status') in ['in_progress', 'pending']])
                completed_count = len(todo_data.get('completed', []))
            else:
                pending_count = 0
                completed_count = 0
            
            status_message = f"""
🤖 *Swarm Health Status*
📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 *Activity*:
- Master Log entries (recent): {entry_count}
- Pending tasks: {pending_count}
- Completed tasks: {completed_count}

🔧 *System*:
- Telegram Bot: Online ✅
- Master Log: {'Available' if self.master_log_path.exists() else '❌ Missing'}
- TODO.json: {'Available' if self.todo_path.exists() else '❌ Missing'}

Use /agents for team details or /logs for recent activity.
            """
            await update.message.reply_text(status_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text("❌ Error retrieving status. Please try again later.")
    
    async def agents_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List active agent teams and their progress."""
        try:
            # Prepare for Team Spawner integration
            agents_message = """
👥 *Active Agent Teams*
(Preparing for Team Spawner integration - coming soon)

Current capabilities:
- /status: Overall swarm health
- /logs: Recent Master Log entries
- /outcomes: Recent SUCCESS entries
- /prioritize <task_id>: Prioritize tasks
- /stop <team_id>: Stop agent teams

Use /status for overall health or check /logs for recent activity.
            """
            await update.message.reply_text(agents_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in agents command: {e}")
            await update.message.reply_text("❌ Error retrieving agent information.")
    
    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get latest entries from the Master Log."""
        try:
            if not self.master_log_path.exists():
                await update.message.reply_text("❌ Master Log not found.")
                return
                
            with open(self.master_log_path, 'r') as f:
                master_log = json.load(f)
            
            # Get last 5 entries
            recent_entries = master_log[-5:] if len(master_log) >= 5 else master_log
            
            if not recent_entries:
                await update.message.reply_text("📭 No log entries found.")
                return
            
            logs_message = "📋 *Recent Master Log Entries*\n\n"
            for entry in recent_entries:
                timestamp = entry.get('timestamp', 'Unknown time')
                source = entry.get('source', 'Unknown source')
                msg_type = entry.get('type', 'Unknown type')
                message = entry.get('message', 'No message')
                
                # Truncate long messages
                if len(message) > 100:
                    message = message[:97] + "..."
                
                logs_message += f"*{timestamp}* [{source}] {msg_type}: {message}\n\n"
            
            await update.message.reply_text(logs_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in logs command: {e}")
            await update.message.reply_text("❌ Error retrieving log entries.")
    
    async def outcomes_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get recent SUCCESS entries from Outcome Journal."""
        try:
            if not self.outcome_log_path.exists():
                await update.message.reply_text("❌ Outcome Journal not found.")
                return
                
            with open(self.outcome_log_path, 'r') as f:
                content = f.read()
            
            # Extract SUCCESS entries (simplified)
            if "## ✅ SUCCESS:" not in content:
                await update.message.reply_text("📭 No SUCCESS entries found.")
                return
            
            # Get last 3 SUCCESS entries
            success_sections = content.split("## ✅ SUCCESS:")
            success_entries = ["## ✅ SUCCESS:" + section for section in success_sections[1:]]  # Skip first empty part
            recent_success = success_entries[-3:] if len(success_entries) >= 3 else success_entries
            
            outcomes_message = "🏆 *Recent SUCCESS Entries*\n\n"
            for entry in recent_success:
                # Extract timestamp if available
                import re
                timestamp_match = re.search(r'\*\*Timestamp\*\*: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.?\d*)', entry)
                timestamp = timestamp_match.group(1) if timestamp_match else "Unknown time"
                
                # Extract task description
                title_match = re.search(r'## ✅ SUCCESS: (.+)', entry)
                title = title_match.group(1).strip() if title_match else "Unknown task"
                
                outcomes_message += f"*{timestamp}*\n{title}\n\n---\n\n"
            
            await update.message.reply_text(outcomes_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in outcomes command: {e}")
            await update.message.reply_text("❌ Error retrieving SUCCESS entries.")
    
    async def prioritize_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prioritize a specific task in the queue."""
        try:
            # Get the task ID from command arguments
            if not context.args:
                await update.message.reply_text("❌ Usage: /prioritize <task_id>\nExample: /prioritize obsidian-integration-1")
                return
            
            task_id = context.args[0]
            
            # TODO: Implement actual prioritization logic with todo.json modification
            # For now, show placeholder response
            prioritize_message = f"""
🎯 *Task Prioritization Requested*
Task ID: {task_id}

(Feature coming soon - will integrate with todo.json modification system to move task to front of queue)

Use /status to see current task queue status.
            """
            await update.message.reply_text(prioritize_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in prioritize command: {e}")
            await update.message.reply_text("❌ Error processing prioritization request.")
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop a specific agent team."""
        try:
            # Get the team ID from command arguments
            if not context.args:
                await update.message.reply_text("❌ Usage: /stop <team_id>\nExample: /stop team_123")
                return
            
            team_id = context.args[0]
            
            # TODO: Implement actual team stopping logic with Team Spawner system
            # For now, show placeholder response
            stop_message = f"""
🛑 *Team Stop Requested*
Team ID: {team_id}

(Feature coming soon - will integrate with Team Spawner system to gracefully stop team)

Use /agents to see current active teams.
            """
            await update.message.reply_text(stop_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in stop command: {e}")
            await update.message.reply_text("❌ Error processing stop request.")
    
    async def export_logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Export master log entries to the chat."""
        try:
            if not self.master_log_path.exists():
                await update.message.reply_text("❌ Master Log not found.")
                return
                
            with open(self.master_log_path, 'r') as f:
                master_log = json.load(f)
            
            # Format logs for display
            if not master_log:
                await update.message.reply_text("📭 Master Log is empty.")
                return
            
            # Get last 10 entries for reasonable message size
            recent_entries = master_log[-10:] if len(master_log) >= 10 else master_log
            
            export_message = "📤 *Master Log Export* (last 10 entries)\n\n"
            for i, entry in enumerate(recent_entries, 1):
                timestamp = entry.get('timestamp', 'Unknown time')
                source = entry.get('source', 'Unknown source')
                msg_type = entry.get('type', 'Unknown type')
                message = entry.get('message', 'No message')
                
                # Truncate long messages for readability
                if len(message) > 150:
                    message = message[:147] + "..."
                
                export_message += f"{i}. *[{source}] {msg_type}*\n   {timestamp}\n   {message}\n\n"
            
            await update.message.reply_text(export_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error exporting logs: {e}")
            await update.message.reply_text("❌ Error exporting logs.")

    
    def run(self):
        """Start the bot."""
        logger.info("Starting Swarm Health Bot...")
        self.application.run_polling()

if __name__ == "__main__":
    bot = SwarmHealthBot()
    bot.run()
