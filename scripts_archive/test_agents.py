#!/usr/bin/env python3
import asyncio
import os
import time
from pathlib import Path
from datetime import datetime
import traceback
from researcher_agent import HumanAIResearcher, DeepSeekBrowserAgent

async def run_test():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    outputs_dir = Path('/home/ubuntu/human-ai/outputs')
    errors_dir = Path('/home/ubuntu/human-ai/errors')
    outputs_dir.mkdir(parents=True, exist_ok=True)
    errors_dir.mkdir(parents=True, exist_ok=True)
    
    prompt = 'Give me 3 XAU/USD scalping setups for the London session. Be specific with entry, stop loss and take profit levels.'
    results = {}

    # Test 1: DeepSeek Browser Agent
    print("\n--- Testing Agent 1: DeepSeek Browser Agent ---")
    try:
        ds_agent = DeepSeekBrowserAgent()
        # Check session
        session_file = Path('/home/ubuntu/human-ai/session/state.json')
        if not session_file.exists() or session_file.stat().st_size == 0:
            print("No valid session found. Attempting login...")
            await ds_agent.login()
        
        start_time = time.time()
        # Manually starting browser for the prompt
        await ds_agent.start_browser()
        response = await ds_agent.prompt(prompt)
        end_time = time.time()
        
        duration_ms = int((end_time - start_time) * 1000)
        results['deepseek'] = {'status': 'SUCCESS', 'time': duration_ms, 'chars': len(response)}
        
        out_path = outputs_dir / f'test_deepseek_{ts}.md'
        out_path.write_text(response)
        print(f"✅ DeepSeek SUCCESS: {duration_ms}ms")
        await ds_agent.close()
    except Exception as e:
        print(f"❌ DeepSeek FAILURE: {str(e)}")
        results['deepseek'] = {'status': 'FAIL', 'time': 0, 'chars': 0}
        with open(errors_dir / f'test_deepseek_{ts}.log', 'w') as f:
            f.write(traceback.format_exc())

    # Test 2: OpenClaw Research Agent
    print("\n--- Testing Agent 2: OpenClaw Research Agent ---")
    try:
        researcher = HumanAIResearcher()
        start_time = time.time()
        # The research method in researcher_agent.py is async
        response = await researcher.research(prompt)
        end_time = time.time()
        
        duration_ms = int((end_time - start_time) * 1000)
        results['openclaw'] = {'status': 'SUCCESS', 'time': duration_ms, 'chars': len(response)}
        
        out_path = outputs_dir / f'test_openclaw_{ts}.md'
        out_path.write_text(response)
        print(f"✅ OpenClaw SUCCESS: {duration_ms}ms")
    except Exception as e:
        print(f"❌ OpenClaw FAILURE: {str(e)}")
        results['openclaw'] = {'status': 'FAIL', 'time': 0, 'chars': 0}
        with open(errors_dir / f'test_openclaw_{ts}.log', 'w') as f:
            f.write(traceback.format_exc())

    # Final Comparison
    print("\n" + "="*30)
    print("AGENT COMPARISON:")
    ds = results.get('deepseek', {'status': 'FAIL', 'time': 0, 'chars': 0})
    oc = results.get('openclaw', {'status': 'FAIL', 'time': 0, 'chars': 0})
    print(f"DeepSeek Browser: {ds['status']} - {ds['time']}ms - {ds['chars']} chars returned")
    print(f"OpenClaw Research: {oc['status']} - {oc['time']}ms - {oc['chars']} chars returned")
    print("="*30)

    # Git update
    import subprocess
    try:
        subprocess.run(f"git add outputs/ errors/ && git commit -m 'Agent test results {ts}' && git push origin main", shell=True, check=True)
        print("\n✅ Test results pushed to git.")
    except subprocess.CalledProcessError as e:
        print(f"\n⚠️ Git push failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
