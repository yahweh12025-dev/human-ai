#!/bin/bash
# Start script for Swarm Telegram Bot

cd /home/yahwehatwork/human-ai
source .env
cd agents/swarm-bot
echo "Starting Swarm Telegram Bot..."
python3 swarm_bot.py >> swarm_bot.log 2>&1 &
echo $! > swarm_bot.pid
echo "Swarm Telegram Bot started with PID $(cat swarm_bot.pid)"