# EXPERT REASONING SKILL
# Goal: Force the LLM into a "Deep Thinking" mode for high-complexity problems.

from skills.openclaw_skill import OpenClawSkill

class ExpertSkill:
    def __init__(self):
        self.ocl = OpenClawSkill()

    def deep_think(self, prompt):
        """
        Triggers high-token, high-reasoning mode.
        Uses a specialized system prompt to force chain-of-thought and multi-step verification.
        """
        expert_system_prompt = (
            "You are in EXPERT MODE. Do not provide a quick answer. "
            "1. Break the problem into atomic components. "
            "2. Explore at least three different architectural approaches. "
            "3. Critique each approach for potential pitfalls and performance bottlenecks. "
            "4. Synthesize the final optimal solution with a detailed step-by-step implementation plan. "
            "Use extensive reasoning and do not skip steps. Take your time."
        )
        
        return self.ocl.prompt_openclaw(prompt, system_prompt=expert_system_prompt)

if __name__ == "__main__":
    print("Expert Reasoning Skill Loaded.")
