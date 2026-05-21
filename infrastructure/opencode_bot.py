import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load config
with open('/home/yahwehatwork/human-ai/infrastructure/opencode_bot.env', 'r') as f:
    lines = f.read().splitlines()
    config = {l.split('=')[0]: l.split('=')[1] for l in lines if '=' in l}

TOKEN = config['TOKEN']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 OpenCode Bot Active. I am monitoring the repository and optimizing the swarm. How can I assist?")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛠️ OpenCode Status: Monitoring for duplicate files and refactoring agent logic. Current priority: DeepSeek extraction fix.")

async def test_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ This is a test message from OpenCode! I am fully operational and connected to the swarm.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("test", test_msg))
    
    print("Starting OpenCode Bot...")
    app.run_polling()
