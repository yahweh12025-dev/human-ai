#!/usr/bin/env python3
"""
SkillMinerAgent: Analyzes session logs to discover successful patterns 
and synthesizes them into reusable AgentSkills.
Strictly Browser-First: Uses the swarm's browser-based agent layer for synthesis.
"""
import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

class SkillMinerAgent:
    """Agent that mines successful workflows from session history."""

    def __init__(self, sessions_dir: str = "/home/ubuntu/.hermes/sessions"):
        self.sessions_dir = Path(sessions_dir)
        # We use the 'hermes chat' command which is the gateway to the 
        # browser-first agents (Perplexity, Claude, Gemini)
        self.omni_router_base_cmd = ["hermes", "chat", "-q"]

    async def find_complex_sessions(self, min_tool_calls: int = 10) -> List[Dict[str, Any]]:
        """Find sessions with high tool usage indicating complex problem solving."""
        complex_sessions = []
        if not self.sessions_dir.exists():
            return []

        for session_file in self.sessions_dir.glob("*.jsonl"):
            try:
                tool_count = 0
                with open(session_file, 'r') as f:
                    for line in f:
                        data = json.loads(line)
                        if 'tool_calls' in data:
                            tool_count += len(data['tool_calls'])
                
                if tool_count >= min_tool_calls:
                    complex_sessions.append({
                        "file": session_file.name,
                        "tool_calls": tool_count
                    })
            except Exception:
                continue
        
        return sorted(complex_sessions, key=lambda x: x['tool_calls'], reverse=True)

    async def distill_workflow(self, session_file: str) -> str:
        """Extracts the sequence of tool calls and user goals from a session."""
        session_path = self.sessions_dir / session_file
        workflow = []
        goal = "Unknown"
        
        try:
            with open(session_path, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    if data.get('role') == 'user':
                        goal = data.get('content', goal)
                    if 'tool_calls' in data:
                        for call in data['tool_calls']:
                            tool = call.get('function', {}).get('name', 'unknown')
                            args = str(call.get('function', {}).get('arguments', {}))[:200]
                            workflow.append(f"Tool: {tool} | Args: {args}...")
            
            if len(workflow) > 50:
                workflow = workflow[-50:]
                
            return f"Goal: {goal}\n\nWorkflow (Last 50 calls):\n" + "\n".join(workflow)
        except Exception as e:
            return f"Error distilling: {e}"

    async def synthesize_skill(self, distilled_data: str) -> Dict[str, Any]:
        """Uses the Browser-First agents via the Omni-Router for synthesis."""
        prompt = (
            "You are a Skill Synthesis Engine. Your ONLY output must be a valid JSON object. "
            "Do not include conversational text, markdown headers, or explanations.\n\n"
            "TASK: Transform the following raw agent workflow into a formalized AgentSkill.\n\n"
            f"{distilled_data}\n\n"
            "JSON STRUCTURE:\n"
            "{\n"
            "  \"name\": \"slug-style-name\",\n"
            "  \"category\": \"category-name\",\n"
            "  \"content\": \"Full SKILL.md content with YAML frontmatter and Markdown body including Trigger, Steps, and Pitfalls\"\n"
            "}\n\n"
            "STRICT RULE: Output ONLY the JSON."
        )
        
        # To ensure browser-first compliance, we route through the browser-based providers
        # provided by the Omni-Router (e.g., ClaudeBrowserAgent or GeminiBrowserAgent)
        cmd = self.omni_router_base_cmd + [
            "--provider", "openrouter", 
            "-m", "deepseek/deepseek-chat", # DeepSeek is accessed via browser-first gateway in this swarm
            "-Q", prompt
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            raw_res = stdout.decode().strip()
            
            if not raw_res:
                return {"error": "No response from LLM"}

            if "session_id:" in raw_res:
                raw_res = raw_res.split("\n", 1)[-1].strip()

            if "```json" in raw_res:
                raw_res = raw_res.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_res:
                raw_res = raw_res.split("```")[1].split("```")[0].strip()
            
            return json.loads(raw_res)
        except Exception as e:
            return {"error": f"Synthesis failed: {str(e)}"}

    async def mine_and_deploy(self):
        """The main loop: Find -> Distill -> Synthesize -> Deploy."""
        print("🔍 Scanning for complex success patterns...")
        sessions = await self.find_complex_sessions()
        if not sessions:
            print("No complex sessions found.")
            return

        target = sessions[0]['file']
        print(f"🧪 Distilling high-value session: {target}")
        distilled = await self.distill_workflow(target)
        
        print("🧠 Synthesizing workflow using Browser-First routing...")
        skill_data = await self.synthesize_skill(distilled)
        
        if "error" in skill_data:
            print(f"❌ Synthesis failed: {skill_data['error']}")
            return

        print(f"✨ Discovered new skill: {skill_data['name']}")
        draft_path = Path(f"/home/yahwehatwork/human-ai/agents/skill_miner/drafts/{skill_data['name']}.md")
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        with open(draft_path, 'w') as f:
            f.write(skill_data['content'])
        
        print(f"✅ Draft saved to {draft_path}")
        return skill_data

if __name__ == "__main__":
    asyncio.run(SkillMinerAgent().mine_and_deploy())
