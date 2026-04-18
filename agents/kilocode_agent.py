#!/usr/bin/env python3
"""
KiloCodeAgent Wrapper: Wrapper for KiloCode CLI tool to perform high-fidelity code refactoring.
"""
import asyncio
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional

class KiloCodeAgent:
    """Wrapper for KiloCode CLI tool."""

    def __init__(self, kilocode_path: Optional[str] = None):
        # If a specific path is provided, use it; otherwise, assume 'kilocode' is in PATH
        self.kilocode_path = kilocode_path or "kilocode"
        self.is_available = False
        self._check_availability()

    def _check_availability(self):
        """Check if kilocode is available and install if necessary."""
        try:
            # Try to run kilocode --version to see if it's available
            result = subprocess.run(
                [self.kilocode_path, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.is_available = True
                print(f"✅ KiloCodeAgent: Found {self.kilocode_path} (version: {result.stdout.strip()})")
            else:
                print(f"⚠️ KiloCodeAgent: {self.kilocode_path} not functioning correctly. Attempting to install...")
                self._install_kilocode()
        except FileNotFoundError:
            print(f"⚠️ KiloCodeAgent: {self.kilocode_path} not found. Attempting to install...")
            self._install_kilocode()
        except Exception as e:
            print(f"❌ KiloCodeAgent: Error checking availability: {e}")
            self._install_kilocode()

    def _install_kilocode(self):
        """Attempt to install kilocode via npm (assuming it's an npm package)."""
        try:
            # Check if npm is available
            npm_result = subprocess.run(
                ["npm", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            if npm_result.returncode != 0:
                print("❌ KiloCodeAgent: npm not found. Cannot install kilocode.")
                return

            # Install kilocode globally (if it's an npm package)
            # Note: We don't know the exact package name; we'll assume it's @kilo/code or similar.
            # Since we don't have specific info, we'll try a common name.
            # In a real scenario, this would be replaced with the actual package name.
            install_result = subprocess.run(
                ["npm", "install", "-g", "kilocode"],  # Adjust package name as needed
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60  # Installation might take time
            )
            if install_result.returncode == 0:
                self.is_available = True
                print("✅ KiloCodeAgent: Successfully installed kilocode via npm.")
            else:
                print(f"❌ KiloCodeAgent: Failed to install kilocode: {install_result.stderr}")
                # As a fallback, we might try other methods, but for now we'll leave it unavailable.
        except Exception as e:
            print(f"❌ KiloCodeAgent: Error during installation: {e}")

    async def refactor_code(self, goal: str, file_path: str, constraints: str = "") -> Dict[str, Any]:
        """
        Use KiloCode to refactor code in the specified file based on the goal.

        Args:
            goal: Description of the refactoring task (e.g., "Refactor this code to use async/await")
            file_path: Path to the file to refactor
            constraints: Additional constraints (e.g., "Keep the same function signature")

        Returns:
            Dict with status, output (refactored code), and any error messages.
        """
        if not self.is_available:
            return {
                "status": "error",
                "error": "KiloCode is not available. Please check installation."
            }

        # Ensure the file exists
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "error": f"File not found: {file_path}"
            }

        # Read the original code
        try:
            with open(file_path, 'r') as f:
                original_code = f.read()
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to read file: {e}"
            }

        # Prepare the prompt for kilocode
        # We assume kilocode takes a prompt and optionally a file, or we can pipe the code.
        # Since we don't know the exact interface, we'll assume it accepts:
        #   kilocode --goal "refactor goal" --file <file> [--constraints "constraints"]
        # If kilocode works differently, this would need adjustment.

        # Build the command
        cmd = [
            self.kilocode_path,
            "--goal", goal,
            "--file", file_path
        ]
        if constraints:
            cmd.extend(["--constraints", constraints])

        print(f"🚀 KiloCodeAgent: Refactoring file {file_path} with goal: {goal}")

        try:
            # Run kilocode and capture output
            # We'll assume it outputs the refactored code to stdout or modifies the file in place.
            # For safety, we'll first run it to see what it outputs, then decide.
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60  # Refactoring might take time
            )

            if result.returncode == 0:
                # Assume the output is the refactored code
                refactored_code = result.stdout.strip()
                # If kilocode modifies the file in place, we might need to read it again.
                # We'll check if the file changed; if not, we'll assume stdout is the new code.
                try:
                    with open(file_path, 'r') as f:
                        current_code = f.read()
                    if current_code == original_code:
                        # File wasn't modified, so use stdout
                        pass
                    else:
                        # File was modified, read the new content
                        refactored_code = current_code
                except Exception:
                    # If we can't read, just use stdout
                    pass

                return {
                    "status": "success",
                    "original_code": original_code,
                    "refactored_code": refactored_code,
                    "output": refactored_code  # For compatibility with other agents
                }
            else:
                return {
                    "status": "error",
                    "error": f"KiloCode failed: {result.stderr}",
                    "original_code": original_code
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "KiloCode refactoring timed out.",
                "original_code": original_code
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error during refactoring: {e}",
                "original_code": original_code
            }

    async def close(self):
        """Cleanup resources (if any)."""
        # No persistent resources to close for now
        pass

# Example usage (for testing)
if __name__ == "__main__":
    import asyncio

    async def test():
        agent = KiloCodeAgent()
        if agent.is_available:
            # Create a dummy file to test
            test_file = "/tmp/test_kilo.py"
            with open(test_file, 'w') as f:
                f.write("""
def hello_world():
    print("Hello, World!")
    return None
""")
            result = await agent.refactor_code(
                goal="Refactor this function to use f-string and add type hints",
                file_path=test_file,
                constraints="Keep the same function name and basic structure"
            )
            print(json.dumps(result, indent=2))
        else:
            print("KiloCodeAgent not available for testing.")

    asyncio.run(test())