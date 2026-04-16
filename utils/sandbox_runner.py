import subprocess
import os
import uuid
from typing import Tuple

class SandboxRunner:
    def __init__(self, image: str = "human-ai-sandbox:latest"):
        self.image = image

    def run_code(self, code: str) -> Tuple[int, str, str]:
        """Executes Python code in an isolated Docker container."""
        container_id = f"swarm-sandbox-{uuid.uuid4().hex[:8]}"
        
        # Write code to a temporary file
        tmp_file = f"/tmp/{container_id}.py"
        with open(tmp_file, "w") as f:
            f.write(code)
            
        print(f"🔒 Executing in Sandbox ({container_id})...")
        
        # Docker command:
        # - run: create and start
        # --rm: remove container after exit
        # -v: mount the code file
        # --network none: disable internet for security
        # --memory: limit RAM to 256MB
        # --cpus: limit CPU to 0.5
        cmd = [
            "docker", "run", "--rm", 
            "--network", "none", 
            "--memory", "256m", 
            "--cpus", "0.5", 
            "-v", f"{tmp_file}:/app/script.py:ro", 
            self.image, 
            "python", "/app/script.py"
        ]
        
        try:
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            return process.returncode, process.stdout, process.stderr
        except subprocess.TimeoutExpired:
            return 124, "", "Sandbox Timeout: Code took too long to execute."
        except Exception as e:
            return 1, "", str(e)
        finally:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

if __name__ == "__main__":
    runner = SandboxRunner()
    # Test Case: Basic calculation
    code = "print(1 + 1)"
    rc, out, err = runner.run_code(code)
    print(f"Result: {rc}, Out: {out}, Err: {err}")
