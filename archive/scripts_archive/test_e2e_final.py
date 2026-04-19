#!/usr/bin/env python3
import asyncio
import os
import sys
sys.path.append('.')
from agents.researcher.researcher_agent import HumanAIResearcher

async def test_e2e():
    print('🚀 Starting End-to-End Verification: Login -> Prompt -> Supabase...')
    researcher = HumanAIResearcher()
    try:
        print('🔍 Phase 1: Researching...')
        report = await researcher.research('The impact of fusion energy on global economics')
        if report and len(report) > 50:
            print('✅ Phase 1: Research successful.')
            print('🔍 Phase 2: Verifying Supabase storage...')
            from supabase import create_client
            supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
            res = supabase.table('research_findings').select('*').ilike('topic', '%fusion%').execute()
            if res.data:
                print(f'✅ Phase 2: Supabase verification SUCCESS (Found entry: {res.data[0]["topic"]})')
                return True
            else:
                print('❌ Phase 2: Supbase verification FAILED (No record found).')
                return False
        else:
            print('❌ Phase 1: Research failed (empty report).')
            return False
    except Exception as e:
        print(f'❌ CRITICAL ERROR: {str(e)}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if asyncio.run(test_e2e()):
        print('🎉 ALL TESTS PASSED!')
        sys.exit(0)
    else:
        print('❌ TESTS FAILED.')
        sys.exit(1)
