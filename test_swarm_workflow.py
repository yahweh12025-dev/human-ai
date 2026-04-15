import asyncio
import os
from agents.navigator.navigator_agent import NavigatorAgent
from agents.ant_farm.orchestrator import AntFarmOrchestrator

async def run_intelligence_workflow():
    print("🚀 Starting Competitive Intelligence Workflow...")
    
    # 1. Initialize Agents
    navigator = NavigatorAgent()
    orchestrator = AntFarmOrchestrator()
    
    try:
        # --- STAGE 1: DATA EXTRACTION ---
        print("\\n--- Stage 1: Data Extraction ---")
        await navigator.navigator.start()
        
        # Target: A simple table for testing (using a public example site)
        target_url = "https://www.scrapethissite.com/pages/forms/"
        table_selector = "table"
        
        print(f"🌐 Extracting data from {target_url}...")
        await navigator.navigator.navigate_to(target_url)
        data = await navigator.skills.extract_dynamic_table_data(table_selector)
        
        if not data:
            print("❌ Data extraction failed.")
            return
        
        print(f"✅ Extracted {len(data)} rows of data.")
        
        # --- STAGE 2: SYNTHESIS & REVIEW ---
        print("\\n--- Stage 2: AntFarm Synthesis & Review ---")
        # Pass the raw data directly to the orchestrator so it detects the list structure
        task_description = str(data[:10])
        task = {"description": task_description}
        
        # The Orchestrator will handle Writer -> Reviewer -> Developer
        result = await orchestrator.execute_pipeline(task)
        
        if result["status"] == "success":
            print("✅ Workflow Successful!")
            print(f"Final Result:\n{result['result']}")
        else:
            print(f"❌ Workflow failed at Review stage: {result['reason']}")

    except Exception as e:
        print(f"❌ Critical Workflow Error: {e}")
    finally:
        await navigator.navigator.close()

if __name__ == "__main__":
    asyncio.run(run_intelligence_workflow())
