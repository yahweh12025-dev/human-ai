# 🤖 Swarm Health Bot Design Specification

## Overview
The Swarm Health Bot is a dedicated Telegram bot designed to provide real-time monitoring, status checks, and steering capabilities for the OpenClaw/Hermes agent swarm.

## Core Objectives
1. **Real-time Visibility**: Provide instant status updates on all active agents and background services.
2. **Direct Steering**: Allow human operators to prioritize tasks, kill runaway processes, or trigger specific autonomous cycles.
3. **Health Monitoring**: Alert operators to failures, rate limits, or system crashes.
4. **Interactive Querying**: Query the MasterLog and Outcome Journal via natural language.

## Functional Requirements

### 1. Monitoring Commands
- `/status`: Returns overall swarm health, active tasks, and resource usage.
- `/agents`: Lists all active agent teams and their current progress.
- `/logs`: Fetches the latest critical entries from `master_log.json` or `improvement.log`.
- `/outcomes`: Summarizes the most recent SUCCESS entries from `OUTCOME_LOG.md`.

### 2. Steering Commands
- `/prioritize <task_id>`: Moves a specific task to the top of the execution queue.
- `/stop <team_id>`: Gracefully terminates a specific agent team.
- `/trigger <cycle_name>`: Manually triggers a specific autonomous cycle (e.g., "memory-review").
- `/reset`: Triggers a system-wide reset of session tokens or state if needed.

### 3. Notification System
- **Push Alerts**: Immediate notification on `IMPLEMENTATION_FAILURE` or `VERIFICATION_FAILURE`.
- **Heartbeat Summary**: A periodic summary of development velocity (tasks completed per hour).

## Technical Architecture

### Components
- **Telegram Gateway**: Uses `python-telegram-bot` or a similar library to interface with the Telegram Bot API.
- **Swarm Interface**: Communicates with the `AntFarmOrchestrator` and `OpenClawTeamSpawner` to query state and send commands.
- **Log Parser**: A utility to extract and format data from JSON logs for Telegram consumption.

### Integration Flow
`User` $\rightarrow$ `Telegram Bot` $\rightarrow$ `Swarm Interface` $\rightarrow$ `Active Agents/Logs` $\rightarrow$ `Response`

## Implementation Plan
1. **Bot Setup**: Configure new bot via BotFather and set up environment variables.
2. **Core Interface**: Implement basic command handlers for `/status` and `/agents`.
3. **Log Integration**: Build the log parsing logic to fetch data from `master_log.json`.
4. **Steering Logic**: Implement the `/prioritize` and `/stop` command handlers.
5. **Alerting System**: Set up a listener for critical log events to trigger push notifications.
6. **Verification**: End-to-end test with real-world swarm operations.
