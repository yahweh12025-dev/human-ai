# CRITIC AGENT TEMPLATE
# Goal: Error elimination and reasoning verification.
# This agent does not "do" work; it reviews the work of others.

class CriticAgent:
    def review_output(self, agent_name, output, goal):
        # logic to check for hallucinations, missing data, or logic errors
        print(f"Reviewing output from {agent_name}...")
        return {"status": "APPROVED" if "Success" in output else "REJECTED", "feedback": "Add more details on X."}

async def main():
    agent = CriticAgent()
    print("Critic Agent active (Reasoning Guard).")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
