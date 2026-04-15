#!/usr/bin/env python3
import asyncio
import os
import sys
from agents.researcher.researcher_agent import HumanAIResearcher

async def test_e2e():
    print("🚀 Starting End-to-End Verification: Login -> Prompt -> Supabase")
    researcher = HumanAIResearcher()
    topic = "The impact of fusion energy on global economics"
    
    try:
        # 1. Perform research (this covers login, prompt, and Supabase storage)
        print(f"🔍 Phase 1: Researching '{topic}'...")
        report = await researcher.research(topic)
        
        if not report or len(report) < 50:
            print("❌ FAILED: Received an empty or insufficient report.")
            return False

        print("✅ Phase 1: Research and LLM response successful.")

        # 2. Verify Supabase entry
        print("🔍 Phase 2: Verifying Supabase storage...")
        # We'll use a small hack to check the table directly via the agent's supabase client
        from supabase import create_client
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        
        response = supabase.table("research_findings")\
            .select("*")\
            .ilike("topic", f"%{topic}%")\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()

        if response.data and len(response.data) > 0:
            print(f"✅ Phase 2: Supabase verification SUCCESS (Found entry: {response.data[0]['topic']})")
            print("🎉 END-TO-END TEST PASSED!")
            return True
        else:
            print("❌ Phase 2: Supbase verification FAILED (No record found).")
            return False

    except Exception as e:
        print(f"❌ CRITICAL ERROR during E2E test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if asyncio.run(test_e2e()):
        sys.exit(0)
    else:
        sys.exit(1)
