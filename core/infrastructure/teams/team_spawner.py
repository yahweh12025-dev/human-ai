#!/usr/bin/env python3
"""
OpenClaw Team Spawner: Implements parallel task execution using OpenClaw Agent Teams.
Allows spawning multiple agent teams to work on tasks in parallel using background processes.
"""
import asyncio
import json
import os
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import signal
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenClawTeamSpawner:
    """Manages spawning and coordinating OpenClaw agent teams for parallel task execution."""
    
    def __init__(self, base_workdir: str = "/home/ubuntu/human-ai"):
        self.base_workdir = Path(base_workdir)
        self.active_teams: Dict[str, Dict] = {}
        self.team_history: List[Dict] = []
        self.shutdown_requested = False
        self.outcome_log_path = Path("/home/ubuntu/human-ai/OUTCOME_LOG.md")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
    
    def _create_success_entry(self, team_info: Dict):
        """Create a SUCCESS entry in OUTCOME_LOG.md for a completed team."""
        if not self.outcome_log_path.parent.exists():
            self.outcome_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().isoformat()
        entry = f'''
## ✅ SUCCESS: Team {team_info["team_id"]} Completed Task
**Timestamp**: {timestamp}
**Agent**: OpenClaw Team Spawner (Autonomous)
**Task**: {team_info["task_description"]}
**Details**: 
- Agent Type: {team_info["agent_type"]}
- Work Directory: {team_info["workdir"]}
- Execution Time: {team_info.get("end_time", "N/A")}
- Return Code: {team_info.get("return_code", "N/A")}
**Files Modified**:
- Outcome Journal updated via autonomous team execution
**Next Steps**: 
- Monitor team performance and task completion rates
'''

        # Append to OUTCOME_LOG.md
        with open(self.outcome_log_path, 'a') as f:
            f.write(entry)
        
        logger.info(f"Created SUCCESS entry for team {team_info['team_id']} in OUTCOME_LOG.md")
    
    def spawn_team(self, 
                   team_id: str,
                   task_description: str,
                   agent_type: str = "codex",
                   workdir: Optional[str] = None,
                   timeout: int = 300,
                   full_auto: bool = True,
                   env_vars: Optional[Dict[str, str]] = None,
                   auto_notify: bool = True,
                   auto_outcome: bool = True) -> str:
        """
        Spawn a new agent team to work on a task in the background.
        
        Args:
            team_id: Unique identifier for the team
            task_description: Description of the task to execute
            agent_type: Type of agent to use (codex, claude, opencode, pi)
            workdir: Working directory for the team (defaults to base_workdir/team_{team_id})
            timeout: Timeout in seconds
            full_auto: Whether to use --full-auto flag for automatic approvals
            env_vars: Additional environment variables to set
            auto_notify: Whether to auto-trigger system events on completion
            auto_outcome: Whether to auto-create SUCCESS entry in OUTCOME_LOG.md
            
        Returns:
            session_id: Identifier for monitoring the team
        """
        if self.shutdown_requested:
            raise RuntimeError("Shutdown requested, cannot spawn new teams")
            
        if workdir is None:
            workdir = self.base_workdir / f"team_{team_id}"
        else:
            workdir = Path(workdir)
            
        # Create working directory
        workdir.mkdir(parents=True, exist_ok=True)
        
        # Initialize git repo if needed (for Codex)
        if agent_type in ["codex", "opencode"]:
            git_dir = workdir / ".git"
            if not git_dir.exists():
                subprocess.run(["git", "init"], cwd=workdir, capture_output=True)
                subprocess.run(["git", "config", "user.name", "OpenClaw Team"], cwd=workdir, capture_output=True)
                subprocess.run(["git", "config", "user.email", "team@openclaw.ai"], cwd=workdir, capture_output=True)
        
        # Build the command
        if agent_type == "codex":
            cmd = ["codex", "exec"]
            if full_auto:
                cmd.append("--full-auto")
            cmd.append(f"'{task_description}'")
            
            # Add completion notification
            completion_msg = f"Team {team_id} completed: {task_description[:50]}..."
            if auto_notify:
                cmd.extend(["&&", "openclaw", "system", "event", "--text", f'"{completion_msg}"', "--mode", "now"])
            
        elif agent_type == "claude":
            cmd = ["claude", "--permission-mode", "bypassPermissions", "--print", f"'{task_description}'"]
            
        elif agent_type == "opencode":
            cmd = ["opencode", "run"]
            if full_auto:
                cmd.append("--yolo")
            cmd.append(f"'{task_description}'")
            
        elif agent_type == "pi":
            cmd = ["pi", f"'{task_description}'"]
            
        else:
            raise ValueError(f"Unsupported agent type: {agent_type}")
        
        # Prepare the bash command with PTY (required for interactive agents)
        bash_cmd = " ".join(cmd)
        full_command = ["bash", "-c", bash_cmd]
        
        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        # Start the process in background
        try:
            process = subprocess.Popen(
                full_command,
                cwd=workdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            session_id = str(uuid.uuid4())
            
            team_info = {
                "team_id": team_id,
                "session_id": session_id,
                "task_description": task_description,
                "agent_type": agent_type,
                "workdir": str(workdir),
                "start_time": datetime.now().isoformat(),
                "timeout": timeout,
                "full_auto": full_auto,
                "env_vars": env_vars or {},
                "auto_notify": auto_notify,
                "auto_outcome": auto_outcome,
                "process": process,
                "status": "running",
                "logs": [],
                "heartbeat": datetime.now().timestamp()
            }
            
            self.active_teams[team_id] = team_info
            logger.info(f"Spawned team {team_id} ({agent_type}) for task: {task_description}")
            
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to spawn team {team_id}: {e}")
            raise
    
    def check_team_status(self, team_id: str) -> Dict:
        """Check the status of a team."""
        if team_id not in self.active_teams:
            # Check in history
            for team in self.team_history:
                if team["team_id"] == team_id:
                    return team
            return {"error": f"Team {team_id} not found"}
            
        team = self.active_teams[team_id]
        process = team["process"]
        
        # Check if process is still running
        if process.poll() is None:
            team["status"] = "running"
            team["heartbeat"] = datetime.now().timestamp()
            # Get some output if available (non-blocking)
            try:
                # Check if there's output available to read
                import select
                if process.stdout:
                    ready, _, _ = select.select([process.stdout], [], [], 0)
                    if ready:
                        output = process.stdout.read(1024)
                        if output:
                            team["logs"].append({
                                "timestamp": datetime.now().isoformat(),
                                "type": "stdout",
                                "output": output.strip()
                            })
                if process.stderr:
                    ready, _, _ = select.select([process.stderr], [], [], 0)
                    if ready:
                        error = process.stderr.read(1024)
                        if error:
                            team["logs"].append({
                                "timestamp": datetime.now().isoformat(),
                                "type": "stderr",
                                "output": error.strip()
                            })
            except Exception as e:
                # Non-critical, just means we couldn't read output
                pass
        else:
            # Process has completed
            stdout, stderr = process.communicate()
            team["status"] = "completed" if process.returncode == 0 else "failed"
            team["end_time"] = datetime.now().isoformat()
            team["return_code"] = process.returncode
            team["heartbeat"] = datetime.now().timestamp()
            if stdout:
                team["logs"].append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "stdout",
                    "output": stdout.strip()
                })
            if stderr:
                team["logs"].append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "stderr",
                    "output": stderr.strip()
                })
            
            # Trigger outcome scribe if enabled
            if team.get("auto_notify", True):
                try:
                    subprocess.run(["python3", "/home/ubuntu/human-ai/scripts/outcome_scribe.py"], 
                                 capture_output=True, timeout=30)
                    logger.debug("Outcome scribe triggered successfully")
                except Exception as e:
                    logger.debug(f"Could not trigger outcome scribe: {e}")
            
            # Create SUCCESS entry in OUTCOME_LOG.md if enabled
            if team.get("auto_outcome", True):
                self._create_success_entry(team)
            
            # Move to history
            self.team_history.append(team)
            del self.active_teams[team_id]
            
        return team
    
    def list_active_teams(self) -> List[Dict]:
        """List all currently active teams."""
        result = []
        for team_id in list(self.active_teams.keys()):  # Copy keys to avoid dict change during iteration
            team_info = self.check_team_status(team_id)
            if "error" not in team_info:
                result.append(team_info)
        return result
    
    def spawn_parallel_teams(self, 
                           tasks: List[Dict[str, Any]]) -> List[str]:
        """
        Spawn multiple teams to work on tasks in parallel.
        
        Args:
            tasks: List of task dictionaries with keys:
                  - team_id: str
                  - task_description: str
                  - agent_type: str (optional, defaults to "codex")
                  - workdir: str (optional)
                  - timeout: int (optional, defaults to 300)
                  - full_auto: bool (optional, defaults to True)
                  - env_vars: dict (optional)
                  - auto_notify: bool (optional, defaults to True)
                  - auto_outcome: bool (optional, defaults to True)
                  
        Returns:
            List of session IDs for the spawned teams
        """
        session_ids = []
        
        for task in tasks:
            if self.shutdown_requested:
                break
                
            team_id = task.get("team_id", str(uuid.uuid4()))
            task_description = task["task_description"]
            agent_type = task.get("agent_type", "codex")
            workdir = task.get("workdir")
            timeout = task.get("timeout", 300)
            full_auto = task.get("full_auto", True)
            env_vars = task.get("env_vars")
            auto_notify = task.get("auto_notify", True)
            auto_outcome = task.get("auto_outcome", True)
            
            session_id = self.spawn_team(
                team_id=team_id,
                task_description=task_description,
                agent_type=agent_type,
                workdir=workdir,
                timeout=timeout,
                full_auto=full_auto,
                env_vars=env_vars,
                auto_notify=auto_notify,
                auto_outcome=auto_outcome
            )
            session_ids.append(session_id)
            
        return session_ids
    
    def get_team_logs(self, team_id: str, limit: int = 100) -> List[Dict]:
        """Get logs for a specific team."""
        # Check active teams
        if team_id in self.active_teams:
            team = self.active_teams[team_id]
            logs = team.get("logs", [])
            return logs[-limit:] if logs else []
        
        # Check history
        for team in self.team_history:
            if team["team_id"] == team_id:
                logs = team.get("logs", [])
                return logs[-limit:] if logs else []
                
        return []
    
    
    def check_system_health(self) -> Dict[str, Any]:
        """Check if all required directories and files are present."""
        required_paths = [
            self.base_workdir,
            self.outcome_log_path,
            Path('/home/ubuntu/human-ai/master_log.json')
        ]
        
        health = {
            'status': 'healthy',
            'checks': {}
        }
        
        for path in required_paths:
            exists = path.exists()
            health['checks'][str(path)] = '✅' if exists else '❌'
            if not exists:
                health['status'] = 'unhealthy'
        
        return health


    def get_system_status(self) -> Dict:
        """Get overall system status."""
        active_teams = self.list_active_teams()
        return {
            "timestamp": datetime.now().isoformat(),
            "active_teams_count": len(active_teams),
            "completed_teams_count": len(self.team_history),
            "shutdown_requested": self.shutdown_requested,
            "active_teams": [
                {
                    "team_id": t["team_id"],
                    "status": t["status"],
                    "agent_type": t["agent_type"],
                    "task": t["task_description"][:50] + "..." if len(t["task_description"]) > 50 else t["task_description"]
                }
                for t in active_teams
            ]
        }

def main():
    """Example usage of the OpenClaw Team Spawner."""
    import sys
    
    spawner = OpenClawTeamSpawner()
    
    # If called with arguments, spawn a team
    if len(sys.argv) > 1:
        task_description = " ".join(sys.argv[1:])
        session_id = spawner.spawn_team(
            team_id=f"cli-task-{int(time.time())}",
            task_description=task_description,
            agent_type="codex",
            full_auto=True
        )
        print(f"Spawned team with session ID: {session_id}")
        print("Use 'python3 -c \"from teams.team_spawner import OpenClawTeamSpawner; s=OpenClawTeamSpawner(); print(s.list_active_teams())\"' to check status")
        return
    
    # Otherwise, show help
    print("OpenClaw Team Spawner")
    print("=====================")
    print("Usage:")
    print("  python3 team_spawner.py \"<task description>\"  # Spawn a team to execute task")
    print("  python3 -c \"from teams.team_spawner import OpenClawTeamSpawner; s=OpenClawTeamSpawner(); print(s.list_active_teams())\"  # List active teams")
    print("  python3 -c \"from teams.team_spawner import OpenClawTeamSpawner; s=OpenClawTeamSpawner(); print(s.get_system_status())\"  # Get system status")

if __name__ == "__main__":
    main()
