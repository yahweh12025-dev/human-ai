#!/bin/bash
while true; do
    pgrep -f opencode_bot.py > /dev/null || python3 /home/yahwehatwork/human-ai/infrastructure/opencode_bot.py >> /home/yahwehatwork/human-ai/infrastructure/opencode_bot.log 2>&1 &
    pgrep -f pidev_bot.py > /dev/null || python3 /home/yahwehatwork/human-ai/infrastructure/pidev_bot.py >> /home/yahwehatwork/human-ai/infrastructure/pidev_bot.log 2>&1 &
    sleep 60
done
