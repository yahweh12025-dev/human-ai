# Cron Jobs Inventory

**Last Updated**: 2026-05-07 23:16:19  
**Repository**: human-ai  
**Purpose**: Inventory of all active cron jobs in the Hermes agent system for maintenance and review

## Active Cron Jobs (6 jobs)

## Detailed Job Listing

### 1. human-ai-github-sync
- **Job ID**: aaeaf1aaf934
- **Name**: human-ai-github-sync
- **Schedule**: 0 */2 * * * (Every 2 hours)
- **State**: scheduled
- **Last Run**: 2026-05-07T02:00:36.776358+00:00
- **Last Status**: ok
- **Script**: sync_to_github.sh
- **Type**: no_agent (classic watchdog pattern)
- **Description**: Synchronizes local changes to GitHub repository

### 2. hermes-self-directed-tasks
- **Job ID**: fd411b75ed0b
- **Name**: hermes-self-directed-tasks
- **Schedule**: 0 */1 * * * (Every hour)
- **State**: scheduled
- **Last Run**: 2026-05-07T23:02:20.316743+00:00
- **Last Status**: error
- **Script**: self_directed_task_loop.py
- **Type**: no_agent (classic watchdog pattern)
- **Description**: Runs Hermes agent in self-directed task loop mode

### 3. auto-push-every-2-hours
- **Job ID**: ae5d14c81209
- **Name**: auto-push-every-2-hours
- **Schedule**: every 120m (Every 2 hours)
- **State**: scheduled
- **Last Run**: 2026-05-07T02:50:57.404937+00:00
- **Last Status**: error
- **Last Delivery Error**: platform 'telegram' not configured/enabled
- **Description**: Executes safe auto-push script to update GitHub without leaking secrets
- **Workdir**: /home/yahwehatwork/human-ai
- **Note**: Has delivery configuration issue with Telegram platform

### 4. opencode-stqueue-review
- **Job ID**: f1a698f37eeb
- **Name**: opencode-stqueue-review
- **Schedule**: */15 * * * * (Every 15 minutes)
- **State**: scheduled
- **Last Run**: Not yet run
- **Last Status**: Not yet run
- **Description**: Review the stqueue.json file to confirm OpenCode is working on assigned tasks or that tasks have been completed, and report status
- **Toolsets**: terminal, file

### 5. pi-dev-task-manager
- **Job ID**: a2cadc4aea5a
- **Name**: pi-dev-task-manager
- **Schedule**: */20 * * * * (Every 20 minutes)
- **State**: scheduled
- **Last Run**: Not yet run
- **Last Status**: Not yet run
- **Description**: Act as Pi.dev agent to manage tasks in the stqueue: load env vars, prompt anythingllm, prompt deepseek agent, review stqueue, manage Pi.dev tasks
- **Toolsets**: terminal, file

### 6. hermes-task-assigner
- **Job ID**: db9007342b72
- **Name**: hermes-task-assigner
- **Schedule**: */30 * * * * (Every 30 minutes)
- **State**: scheduled
- **Last Run**: Not yet run
- **Last Status**: Not yet run
- **Description**: Act as Hermes Agent to manage task assignment and continuous development: review completed tasks, analyze repo, suggest new task assignments, add tasks to stqueue
- **Toolsets**: terminal, file

## Summary Statistics
- **Total Jobs**: 6
- **Scheduled Jobs**: 6
- **Paused Jobs**: 0
- **Jobs with Last Run**: 3
- **Jobs Never Run**: 3
- **Successful Last Runs**: 1
- **Failed Last Runs**: 2

## Next Scheduled Runs
1. opencode-stqueue-review: 2026-05-07T23:15:00+00:00 (in ~10 minutes)
2. pi-dev-task-manager: 2026-05-07T23:20:00+00:00 (in ~15 minutes)  
3. hermes-task-assigner: 2026-05-07T23:30:00+00:00 (in ~25 minutes)
4. human-ai-github-sync: 2026-05-08T00:00:00+00:00 (in ~2 hours)
5. auto-push-every-2-hours: 2026-05-08T00:35:49+00:00 (in ~2.5 hours)
6. hermes-self-directed-tasks: 2026-05-08T00:00:00+00:00 (in ~2 hours)

## Maintenance Notes
- Job 'auto-push-every-2-hours' has a delivery configuration error (Telegram platform not configured)
- Job 'hermes-self-directed-tasks' last run resulted in error status
- Three newer jobs (opencode-stqueue-review, pi-dev-task-manager, hermes-task-assigner) have not yet executed
- Consider reviewing error states and delivery configurations periodically

## File Location
This file is located at: /home/yahwehatwork/human-ai/docs/cronjobs/cron_jobs_list.md

## How to Update
To regenerate this list, run the cron job inventory script or manually update this file when cron jobs are added, modified, or removed.
