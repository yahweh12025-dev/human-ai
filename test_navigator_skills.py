import asyncio
from agents.navigator.navigator_agent import NavigatorAgent

async def test_skills():
    agent = NavigatorAgent()
    await agent.navigator.start()
    print("Testing Login Skill...")
    # Using a fake URL for testing purposes
    success = await agent.skills.perform_login("https://example.com/login", {"email": "test@example.com", "password": "password123"})
    print(f"Login Skill Result: {success}")
    await agent.navigator.close()

if __name__ == "__main__":
    asyncio.run(test_skills())
