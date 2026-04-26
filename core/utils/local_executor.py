import subprocess
import os
import tempfile
from typing import Tuple

class LocalSafeExecutor:
    """
    A lightweight alternative to SandboxRunner for environments without Docker.
    Runs code in a separate process and captures output.
    """
    def run_code(self, code: str) -> Tuple[int, str, str]:
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
            tmp.write(code.encode('utf-8'))
            tmp_path = tmp.name

        try:
            # Run the code as a separate process
            process = subprocess.run(
                ["/home/yahwehatwork/human-ai/venv-kilo/bin/python", tmp_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            return process.returncode, process.stdout, process.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Execution timed out after 10 seconds."
        except Exception as e:
            return 1, "", str(e)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == "__main__":
    executor = LocalSafeExecutor()
    rc, out, err = executor.run_code("print('Local Safe Test')")
    print(f"RC: {rc}, Out: {out}, Err: {err}")
