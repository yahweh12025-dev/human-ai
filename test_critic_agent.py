import asyncio
from agents.critic.critic_agent import CriticAgent

async def test_critic():
    critic = CriticAgent()
    print("Critic agent initialized.")
    
    # Test with a simple, correct statement
    test_content = "The sky is blue due to Rayleigh scattering of sunlight in the atmosphere."
    print(f"Testing with content: '{test_content}'")
    
    result = await critic.review(test_content)
    print(f"Review result: {result}")
    
    # Test with an incorrect statement
    test_content_wrong = "The sky is green because plants reflect green light."
    print(f"Testing with incorrect content: '{test_content_wrong}'")
    
    result_wrong = await critic.review(test_content_wrong)
    print(f"Review result for incorrect content: {result_wrong}")

if __name__ == "__main__":
    asyncio.run(test_critic())
