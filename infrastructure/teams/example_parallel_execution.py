#!/usr/bin/env python3
"""
Example: Parallel task execution using OpenClaw Agent Teams.
Demonstrates how to spawn multiple agent teams to work on different tasks simultaneously.
"""
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from team_spawner import OpenClawTeamSpawner

def main():
    """Demonstrate parallel task execution."""
    print("🚀 OpenClaw Team Spawner - Parallel Task Execution Demo")
    print("=" * 60)
    
    spawner = OpenClawTeamSpawner()
    
    # Define multiple tasks to work on in parallel
    tasks = [
        {
            "team_id": "doc-enhancement-1",
            "task_description": "Enhance README.md with detailed examples of the outcome scribe loop and team spawner functionality",
            "agent_type": "codex",
            "timeout": 120
        },
        {
            "team_id": "skill-analysis-1", 
            "task_description": "Analyze existing AgentSkills in the repository to identify patterns and opportunities for new skill development",
            "agent_type": "codex",
            "timeout": 120
        },
        {
            "team_id": "test-improvement-1",
            "task_description": "Improve test coverage for the outcome scribe script by adding edge case tests and integration tests",
            "agent_type": "codex",
            "timeout": 120
        }
    ]
    
    print(f"📋 Spawning {len(tasks)} agent teams to work in parallel...")
    
    # Spawn all teams in parallel
    session_ids = spawner.spawn_parallel_teams(tasks)
    
    print(f"✅ Spawned {len(session_ids)} teams:")
    for i, (task, session_id) in enumerate(zip(tasks, session_ids)):
        print(f"   Team {i+1}: {task['team_id']} - {task['task_description'][:50]}...")
        print(f"      Session ID: {session_id}")
    
    print("\n🔍 To monitor progress, run:")
    print("   python3 -c \"from teams.team_spawner import OpenClawTeamSpawner; s=OpenClawTeamSpawner(); import json; print(json.dumps(s.list_active_teams(), indent=2))\"")
    print("\n📊 To get system status:")
    print("   python3 -c \"from teams.team_spawner import OpenClawTeamSpawner; s=OpenClawTeamSpawner(); import json; print(json.dumps(s.get_system_status(), indent=2))\"")
    print("\n💡 Teams will run in the background and notify OpenClaw when complete via system events.")
    
    # Show initial status
    print("\n📊 Initial team status:")
    status = spawner.get_system_status()
    print(f"   Active teams: {status['active_teams_count']}")
    print(f"   Completed teams: {status['completed_teams_count']}")
    for team in status['active_teams']:
        print(f"   • {team['team_id']} ({team['agent_type']}): {team['task']}")

if __name__ == "__main__":
    main()
