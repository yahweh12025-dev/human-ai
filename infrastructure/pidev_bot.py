import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load config
with open('/home/yahwehatwork/human-ai/infrastructure/pidev_bot.env', 'r') as f:
    lines = f.read().splitlines()
    config = {l.split('=')[0]: l.split('=')[1] for l in lines if '=' in l}

TOKEN = config['TOKEN']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌐 Pi.dev Bot Active. I am researching selectors, optimizing the repo structure, and managing browser stealth. How can I assist?")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Pi.dev Status: Researching Claude session replication and analyzing browser-use integration. Current priority: Replicating DeepSeek success for Claude.")

async def test_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ This is a test message from Pi.dev! I am fully operational and connected to the swarm.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("test", test_msg))
    
    print("Starting Pi.dev Bot...")
    app.run_polling()
