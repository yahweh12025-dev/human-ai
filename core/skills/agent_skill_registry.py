#!/usr/bin/env python3
"""
Agent Skill Registry
Central registry for all agent skills/plugins. OpenClaw routes commands to appropriate skills.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable

sys.path.append(str(Path(__file__).parent.parent))


class AgentSkillRegistry:
    """
    Central registry for agent skills. Each agent can register and invoke skills.
    Skills are categorized by agent and can be triggered via OpenClaw gateway.
    """

    def __init__(self):
        self.project_root = Path.home() / "human-ai"
        self.skills: Dict[str, Dict[str, dict]] = {
            "openclaw": {},
            "hermes": {},
            "opencode": {},
            "freqtrade": {},
            "ea": {},
            "social": {},
        }
        self._register_all_skills()

    def _register_all_skills(self):
        """Register all built-in skills for each agent"""

        # OpenClaw Skills (Gateway/Coordinator)
        self.skills["openclaw"] = {
            "trigger_agent": {
                "description": "Trigger any agent to execute their assigned tasks",
                "usage": "/openclaw trigger <agent_name>",
                "handler": "core.orchestration.automode:AutoModeController"
            },
            "system_status": {
                "description": "Get full system status across all agents and integrations",
                "usage": "/openclaw status",
                "handler": "core.integrations.verify_all_integrations:run_all_verifications"
            },
            "deploy_coordinator": {
                "description": "Orchestrate multi-agent deployments with verification gates",
                "usage": "/openclaw deploy <target>",
                "handler": "scripts.deployment_orchestrator:deploy"
            },
            "task_manager": {
                "description": "View, assign, and manage tasks in unified_tasks.json",
                "usage": "/openclaw tasks [list|assign|complete]",
                "handler": "unified_tasks.json"
            },
            "sync_all": {
                "description": "Run full sync to Obsidian vault and Google Drive",
                "usage": "/openclaw sync",
                "handler": "scripts.sync.full_sync:main"
            },
        }

        # Hermes Skills (Strategy/Architecture)
        self.skills["hermes"] = {
            "strategy_review": {
                "description": "Review and improve trading strategies based on backtest data",
                "usage": "/hermes review_strategy <freqtrade|ea>",
                "handler": "core.orchestration.unified_improvement_workflow:UnifiedImprovementWorkflow"
            },
            "decision_intelligence": {
                "description": "Analyze agent performance and suggest optimal task assignments",
                "usage": "/hermes decide <context>",
                "handler": "scripts.cross_agent_decision_intelligence:analyze"
            },
            "knowledge_synthesis": {
                "description": "Synthesize research findings into actionable insights",
                "usage": "/hermes synthesize <topic>",
                "handler": "research.auto_synthesizer:synthesize"
            },
            "architecture_audit": {
                "description": "Audit system architecture and suggest improvements",
                "usage": "/hermes audit",
                "handler": "core.health.architecture_auditor:audit"
            },
            "dify_query": {
                "description": "Query Dify knowledge base for information",
                "usage": "/hermes query <question>",
                "handler": "core.integrations.dify_brain:DifyBrain.query"
            },
        }

        # OpenCode Skills (Implementation)
        self.skills["opencode"] = {
            "implement_task": {
                "description": "Implement a specific task from the queue",
                "usage": "/opencode implement <task_id>",
                "handler": "core.orchestration.automode:AutoModeController._execute_task"
            },
            "run_tests": {
                "description": "Run test suite and report results",
                "usage": "/opencode test [path]",
                "handler": "pytest"
            },
            "code_review": {
                "description": "Review code for quality, security, and performance",
                "usage": "/opencode review <file_path>",
                "handler": "agents.code_review_assistant:review"
            },
            "refactor": {
                "description": "Refactor code for better structure and maintainability",
                "usage": "/opencode refactor <file_path>",
                "handler": "agents.code_review_assistant:refactor"
            },
            "generate_tests": {
                "description": "Auto-generate test cases for a module",
                "usage": "/opencode gen_tests <module>",
                "handler": "scripts.automated_verification_test_generator:generate"
            },
        }

        # FreqTrade Skills
        self.skills["freqtrade"] = {
            "run_backtest": {
                "description": "Run FreqTrade backtest with current strategy",
                "usage": "/freqtrade backtest [timerange]",
                "handler": "agents.trading-agent.openclaw_freqtrade_bridge:OpenClawFreqTradeBridge.run_backtest"
            },
            "start_bot": {
                "description": "Start FreqTrade trading bot on testnet",
                "usage": "/freqtrade start [dry_run]",
                "handler": "agents.trading-agent.openclaw_freqtrade_bridge:OpenClawFreqTradeBridge.start_trading_bot"
            },
            "stop_bot": {
                "description": "Stop FreqTrade trading bot",
                "usage": "/freqtrade stop",
                "handler": "agents.trading-agent.openclaw_freqtrade_bridge:OpenClawFreqTradeBridge.stop_trading_bot"
            },
            "trade_history": {
                "description": "Get recent trading history",
                "usage": "/freqtrade history [limit]",
                "handler": "agents.trading-agent.freqtrade_testnet_agent:FreqTradeTestnetAgent.get_performance_summary"
            },
            "download_data": {
                "description": "Download latest market data",
                "usage": "/freqtrade download [pairs] [timerange]",
                "handler": "agents.trading-agent.openclaw_freqtrade_bridge:OpenClawFreqTradeBridge.download_market_data"
            },
        }

        # EA Skills
        self.skills["ea"] = {
            "compile": {
                "description": "Compile EA from MQ5 source",
                "usage": "/ea compile <ea_name>",
                "handler": "automation.mt5_bridge_complete:MT5AutomationBridge.compile_ea"
            },
            "backtest": {
                "description": "Run EA backtest on MT5",
                "usage": "/ea backtest <ea_name> [symbol] [timeframe]",
                "handler": "automation.mt5_bridge_complete:MT5AutomationBridge.run_backtest"
            },
            "list_eas": {
                "description": "List all available Expert Advisors",
                "usage": "/ea list",
                "handler": "agents.openclaw_ea_trigger_gui:OpenClawEATrigger.list_available_eas"
            },
            "extract_logs": {
                "description": "Extract and parse MT5 logs",
                "usage": "/ea logs [type]",
                "handler": "automation.mt5_bridge_complete:MT5AutomationBridge.extract_mt5_logs"
            },
        }

        # Social Media Skills
        self.skills["social"] = {
            "create_post": {
                "description": "Generate and queue a social media post",
                "usage": "/social create <topic> [platform]",
                "handler": "agents.social_media_agent:SocialMediaAgent.create_content"
            },
            "schedule": {
                "description": "View/manage content schedule",
                "usage": "/social schedule [view|add|remove]",
                "handler": "social.content_pipeline:ContentPipeline.get_schedule"
            },
            "publish": {
                "description": "Publish queued content via Postiz",
                "usage": "/social publish [content_id]",
                "handler": "social.postiz_connector:PostizConnector.publish_content"
            },
            "analytics": {
                "description": "Get social media performance analytics",
                "usage": "/social analytics [platform]",
                "handler": "social.analytics_tracker:get_analytics"
            },
        }

    def get_skill(self, agent: str, skill_name: str) -> Optional[dict]:
        """Get a specific skill definition"""
        return self.skills.get(agent, {}).get(skill_name)

    def list_skills(self, agent: Optional[str] = None) -> Dict:
        """List all skills, optionally filtered by agent"""
        if agent:
            return {agent: self.skills.get(agent, {})}
        return self.skills

    def get_help(self, agent: Optional[str] = None) -> str:
        """Generate help text for skills"""
        lines = ["Available Skills:"]
        skills = self.skills if not agent else {agent: self.skills.get(agent, {})}

        for agent_name, agent_skills in skills.items():
            if agent_skills:
                lines.append(f"\n  [{agent_name.upper()}]")
                for name, info in agent_skills.items():
                    lines.append(f"    {info['usage']}")
                    lines.append(f"      {info['description']}")

        return "\n".join(lines)

    def export_registry(self) -> str:
        """Export registry as JSON for OpenClaw consumption"""
        output = self.project_root / "configs" / "skill_registry.json"
        with open(output, 'w') as f:
            json.dump(self.skills, f, indent=2)
        return str(output)


def main():
    registry = AgentSkillRegistry()
    print(registry.get_help())
    output = registry.export_registry()
    print(f"\nRegistry exported to: {output}")


if __name__ == "__main__":
    main()
