import asyncio
from agents.navigator.navigator_agent import NavigatorAgent

async def test_table_skill():
    agent = NavigatorAgent()
    await agent.navigator.start()
    print("Navigator started.")
    
    # Test the new skill on a simple, locally available element
    # We'll use the body tag as a mock "table" for safety
    try:
        # This is a safe test - we're not expecting a real table, just checking the method exists and runs
        result = await agent.skills.extract_dynamic_table_data(
            table_selector='body', 
            row_selector='div', 
            col_selector='span'
        )
        print(f"Table extraction test completed. Result type: {type(result)}, Length: {len(result)}")
        print(f"Skill is callable and integrated correctly.")
    except Exception as e:
        print(f"Error during skill test: {e}")
    finally:
        await agent.navigator.close()

if __name__ == "__main__":
    asyncio.run(test_table_skill())
