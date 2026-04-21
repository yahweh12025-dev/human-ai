
import asyncio
import sys
import os
sys.path.append('/home/ubuntu/human-ai/core/agents/dr_claw_worker')

from dr_claw_worker_agent import NativeWorker

async def test_native_worker():
    worker = NativeWorker()
    try:
        print("🧪 Testing NativeWorker with hardened browser agent...")
        # Test with a simple code generation task
        result = await worker.execute_task("Create a Python function that calculates factorial of a number")
        print(f"Result: {result}")
        
        if result.get("status") == "success":
            print("✅ NativeWorker test passed!")
            # Try to execute the generated code
            code = result.get("result", "")
            if code:
                print("\n📝 Generated code:")
                print(code)
                # Try to compile it to check for syntax errors
                try:
                    compile(code, '<generated>', 'exec')
                    print("✅ Generated code compiles successfully")
                except SyntaxError as e:
                    print(f"❌ Syntax error in generated code: {e}")
            return True
        else:
            print(f"❌ NativeWorker test failed: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ NativeWorker test error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup is handled internally
        pass

if __name__ == "__main__":
    success = asyncio.run(test_native_worker())
    sys.exit(0 if success else 1)
