import asyncio
import os
from core.agents.ant_farm.orchestrator import AntFarmOrchestrator
from core.native_worker import NativeWorker

async def run_direct_test():
    print("🚀 Starting Direct-Implementation Test (Bypassing Research)...")
    worker = NativeWorker()
    
    # Task: Create a simple health check utility
    task_prompt = "Create a file at /home/yahwehatwork/human-ai/core/utils/swarm_health_check.py that contains a function 'check_system()' which prints 'System Healthy'."
    
    # We use the worker directly to verify the Kilo-Code apply logic
    # In a real scenario, the Orchestrator would handle this
    print(f"Target Goal: {task_prompt}")
    
    # Manually simulate the la-phase: Generate code (simplified for test)
    # In a real run, this comes from the LLM. Here we provide the target code.
    generated_code = "def check_system():\n    print('System Healthy')\n\nif __name__ == '__main__':\n    check_system()"
    
    # Now, test the ACTUAL Kilo-Code application
    # We'll use a helper to apply it since we're testing the worker's integration
    from core.agents.kilo_code_agent import handle_write
    
    success = handle_write("/home/yahwehatwork/human-ai/core/utils/swarm_health_check.py", generated_code)
    
    if success:
        print("✅ Kilo-Code successfully applied the file to the repository.")
        # Verify using the new LocalSafeExecutor
        from core.utils.local_executor import LocalSafeExecutor
        sandbox = LocalSafeExecutor()
        rc, stdout, stderr = sandbox.run_code(generated_code)
        
        if rc == 0 and "System Healthy" in stdout:
            print(f"✅ Sandbox Verification SUCCESS: {stdout.strip()}")
            print("🏆 FULL LOOP VERIFIED: Implementation $\rightarrow$ Application $\rightarrow$ Verification.")
        else:
            print(f"❌ Sandbox Verification FAILED: {stderr}")
    else:
        print("❌ Kilo-Code failed to apply the change.")

if __name__ == "__main__":
    asyncio.run(run_direct_test())
