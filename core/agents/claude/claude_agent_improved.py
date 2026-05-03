#!/usr/bin/env python3
"""
Robust Claude Agent using clipboard-paste and extreme bottom-left extraction.
"""

import asyncio
import os
import subprocess
import time
import json
from typing import Optional, Dict, Any
import signal
from core.utils.response_logger import response_logger


class ClaudeAgentImproved:
    """
    Robust Agent for interacting with Claude Desktop application using clipboard-paste 
    and extreme bottom-left extraction strategies.
    """

    def __init__(self, claude_executable: str = "/usr/bin/claude-desktop"):
        self.claude_executable = claude_executable
        self.claude_window_id: Optional[str] = None
        self.calibrated_coords: Optional[Dict[str, int]] = None
        self._load_calibration()

    def _load_calibration(self):
        """Load calibrated coordinates from the config directory."""
        config_path = "/home/yahwehatwork/human-ai/agents/freqtrade/user_data/claude_copy_button_coords.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.calibrated_coords = json.load(f)
                print(f"✅ Loaded calibrated coordinates: {self.calibrated_coords}")
            except Exception as e:
                print(f"❌ Failed to load calibration file: {e}")
        else:
            print("⚠️ No calibration file found. Agent will use default (guessing) mode.")

    def _run_command(self, cmd: str, timeout: int = 5) -> tuple[bool, str, str]:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, '', 'Timeout'
        except Exception as e:
            return False, '', str(e)

    def _find_claude_window(self) -> Optional[str]:
        success, output, _ = self._run_command('wmctrl -l -p')
        if not success:
            return None

        for line in output.split('\n'):
            if line.strip():
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    win_id, desktop, pid, title = parts
                    if 'claude' in title.lower() or 'Claude' in title:
                        return win_id
        return None

    def _activate_window(self, window_id: str) -> bool:
        success, _, _ = self._run_command(f'wmctrl -i -a {window_id}')
        return success

    def _clear_clipboard(self) -> bool:
        success, _, _ = self._run_command('echo -n "" | xclip -selection clipboard')
        return success

    def _copy_to_clipboard(self, text: str) -> bool:
        try:
            process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=text)
            return process.returncode == 0
        except Exception as e:
            print(f"❌ Clipboard copy failed: {e}")
            return False

    def _get_clipboard(self) -> Optional[str]:
        success, output, _ = self._run_command('xclip -selection clipboard -o')
        return output if success else None

    def _get_window_geometry(self, window_id: str) -> Optional[dict]:
        success, output, _ = self._run_command(f'xwininfo -id {window_id}')
        if not success: return None
        geometry = {}
        for line in output.split('\n'):
            if 'Absolute upper-left X:' in line: geometry['x'] = int(line.split(':')[1].strip())
            elif 'Absolute upper-left Y:' in line: geometry['y'] = int(line.split(':')[1].strip())
            elif 'Width:' in line: geometry['width'] = int(line.split(':')[1].strip())
            elif 'Height:' in line: geometry['height'] = int(line.split(':')[1].strip())
        return geometry if len(geometry) == 4 else None

    def _send_keys(self, window_id: str, keys: str) -> bool:
        if not self._activate_window(window_id):
            return False
        time.sleep(0.2)
        success, _, _ = self._run_command(f'xdotool windowactivate --sync {window_id} key {keys}')
        return success

    def _clean_response(self, response: str) -> str:
        disclaimers = [
            "Claude is AI and can make mistakes. Please double-check responses.",
            "Claude is an AI and can make mistakes",
            "AI can make mistakes",
            "Please double-check responses"
        ]
        cleaned = response
        for d in disclaimers:
            cleaned = cleaned.replace(d, "")
        return cleaned.strip()

    async def _try_extract_via_copy_button(self, prompt: str) -> Optional[str]:
        """Strategy 1: Use calibrated coordinates or fallback to bottom-left guessing."""
        if not self.claude_window_id: return None
        
        print("🔄 Scrolling to bottom of window to ensure button is visible...")
        self._send_keys(self.claude_window_id, 'End')
        await asyncio.sleep(1.5)

        if self.calibrated_coords:
            tx, ty = self.calibrated_coords['x'], self.calibrated_coords['y']
            print(f"🎯 Using CALIBRATED coordinates: ({tx}, {ty})")
        else:
            geo = self._get_window_geometry(self.claude_window_id)
            if not geo: return None
            tx, ty = geo['x'] + int(geo['width'] * 0.10), geo['y'] + int(geo['height'] * 0.95)
            print(f"⚠️ No calibration found. Using fallback guess: ({tx}, {ty})")

        # Perform the click
        self._run_command(f'xdotool windowactivate --sync {self.claude_window_id} mousemove {tx} {ty}')
        time.sleep(0.3)
        self._run_command(f'xdotool windowactivate --sync {self.claude_window_id} click 1')
        time.sleep(0.8)

        content = self._get_clipboard()
        
        # Validation: Ensure it's not just the prompt
        if content and prompt.strip() in content and len(content.strip()) < len(prompt.strip()) + 20:
            return None # Trigger fallback
            
        return content

    async def _try_extract_via_select_all(self, prompt: str) -> Optional[str]:
        """Strategy 2: Select-All and Copy as fallback."""
        if not self.claude_window_id: return None
        
        print("🖱️ Attempting fallback: Select All (Ctrl+A) and Copy (Ctrl+C)...")
        if not self._activate_window(self.claude_window_id):
            return None
            
        time.sleep(0.2)
        self._send_keys(self.claude_window_id, 'ctrl+a')
        time.sleep(0.3)
        self._send_keys(self.claude_window_id, 'ctrl+c')
        time.sleep(0.8)
        
        # Click somewhere safe to deselect text (e.g. top center)
        geo = self._get_window_geometry(self.claude_window_id)
        if geo:
            tx, ty = geo['x'] + geo['width'] // 2, geo['y'] + 50
            self._run_command(f'xdotool windowactivate --sync {self.claude_window_id} mousemove {tx} {ty}')
            self._run_command(f'xdotool windowactivate --sync {self.claude_window_id} click 1')

        content = self._get_clipboard()
        if not content: return None
        
        # In Claude Desktop, copying everything usually results in alternating "You" and "Claude" headers.
        # Try to find the last response.
        parts = content.split("Claude")
        if len(parts) > 1:
            last_response = parts[-1]
            # It might have a prompt at the end if the user typed something but didn't send, 
            # but usually the last "Claude" block is the response.
            # Clean up leading/trailing whitespace
            last_response = last_response.strip()
            
            # If it's too short and we know the prompt, we might have caught it mid-generation or failed.
            if len(last_response) < 5:
                return None
                
            return last_response
            
        # If we didn't find "Claude", return the raw content just in case
        if content and prompt.strip() in content and len(content.strip()) < len(prompt.strip()) + 20:
            return None
        return content

    async def start(self) -> bool:
        window_id = self._find_claude_window()
        if not window_id:
            print("❌ Claude Desktop window not found")
            return False
        self.claude_window_id = window_id
        print(f"✅ Found Claude Desktop window: {window_id}")
        return self._activate_window(window_id)

    async def close(self) -> None:
        self.claude_window_id = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def send_prompt(self, prompt: str) -> str:
        if not self.claude_window_id:
            return "Error: Agent not started. Call start() first."

        try:
            print(f"📝 Preparing prompt of length {len(prompt)}...")
            self._clear_clipboard()
            
            # Write prompt to a temp file for xdotool to type robustly
            prompt_file = "/tmp/claude_prompt.txt"
            with open(prompt_file, 'w') as f:
                f.write(prompt)

            # Focus and Paste
            geo = self._get_window_geometry(self.claude_window_id)
            if geo:
                print(f"🪟 Window geometry: {geo}")
                # Click center first (hits the input box on the home screen)
                cx, cy = geo['x'] + geo['width'] // 2, geo['y'] + geo['height'] // 2
                self._run_command(f'xdotool windowactivate --sync {self.claude_window_id} mousemove {cx} {cy} click 1')
                time.sleep(0.2)
                # Click bottom second (hits the input box on an active chat)
                tx, ty = geo['x'] + geo['width'] // 2, geo['y'] + geo['height'] - 80
                self._run_command(f'xdotool windowactivate --sync {self.claude_window_id} mousemove {tx} {ty} click 1')
                await asyncio.sleep(0.5)
            
            print("⌨️ Typing prompt...")
            # Use xdotool type --file to reliably insert text without clipboard issues
            self._run_command(f'xdotool windowactivate --sync {self.claude_window_id} type --delay 2 --clearmodifiers --file {prompt_file}')
            await asyncio.sleep(0.5)
            self._send_keys(self.claude_window_id, 'Return')
            await asyncio.sleep(0.5)
            self._send_keys(self.claude_window_id, 'KP_Enter')

            print("⏳ Waiting for Claude to respond (max 90s)...")
            max_wait = 90
            elapsed = 0
            last_content = ""

            while elapsed < max_wait:
                await asyncio.sleep(5)
                elapsed += 5

                content = await self._try_extract_via_copy_button(prompt)
                if not content:
                    content = await self._try_extract_via_select_all(prompt)

                if content:
                    if content != last_content:
                        last_content = content
                    else:
                        cleaned = self._clean_response(content)
                        if len(cleaned) > 5:
                            print(f"✅ Successfully extracted response ({len(cleaned)} chars).")
                            await response_logger.log_response(
                                agent_name="ClaudeAgentImproved",
                                prompt=prompt,
                                raw_response=content,
                                cleaned_response=cleaned,
                                metadata={"status": "success"}
                            )
                            return cleaned
                else:
                    print(f"... still waiting ({elapsed}s elapsed) ...")

            return f"Error: Response timeout. Last seen: {last_content[:50]}..."

        except Exception as e:
            return f"Error during send_prompt: {e}"

    def _read_file_for_prompt(self, file_path: str, max_lines: int = 200) -> str:
        """Read a file and return its contents, truncating large files with head/tail."""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            filename = os.path.basename(file_path)
            total_lines = len(lines)
            
            if total_lines <= max_lines:
                content = ''.join(lines)
            else:
                # Show head and tail with a truncation notice
                head_lines = max_lines // 2
                tail_lines = max_lines // 2
                head = ''.join(lines[:head_lines])
                tail = ''.join(lines[-tail_lines:])
                skipped = total_lines - head_lines - tail_lines
                content = f"{head}\n... [{skipped} lines truncated] ...\n{tail}"
            
            return f"\n--- FILE: {filename} ({total_lines} lines) ---\n{content}\n--- END FILE: {filename} ---\n"
        except Exception as e:
            return f"\n--- FILE: {file_path} (ERROR: {e}) ---\n"

    def _collect_directory_files(self, dir_path: str, extensions: list = None, max_files: int = 20) -> list:
        """Collect file paths from a directory, optionally filtering by extension."""
        if extensions is None:
            extensions = ['.py', '.csv', '.json', '.txt', '.log', '.html']
        
        collected = []
        try:
            for root, dirs, files in os.walk(dir_path):
                for fname in sorted(files):
                    if any(fname.endswith(ext) for ext in extensions):
                        collected.append(os.path.join(root, fname))
                        if len(collected) >= max_files:
                            return collected
        except Exception as e:
            print(f"⚠️ Error scanning directory {dir_path}: {e}")
        return collected

    async def send_prompt_with_files(self, prompt: str, file_paths: list = None, 
                                      directories: list = None, max_lines_per_file: int = 200,
                                      max_wait: int = 120) -> str:
        """
        Send a prompt to Claude with file contents embedded inline.
        
        Args:
            prompt: The instruction/question for Claude
            file_paths: List of individual file paths to include
            directories: List of directories to scan for relevant files
            max_lines_per_file: Maximum lines per file (large files get head/tail truncated)
            max_wait: Maximum seconds to wait for Claude's response
        """
        if not self.claude_window_id:
            return "Error: Agent not started. Call start() first."

        # Build the composite prompt with embedded files
        parts = [prompt, "\n\n=== ATTACHED FILES ===\n"]
        
        all_files = []
        if file_paths:
            all_files.extend(file_paths)
        if directories:
            for d in directories:
                all_files.extend(self._collect_directory_files(d))
        
        if not all_files:
            parts.append("(No files found to attach)\n")
        else:
            print(f"📎 Attaching {len(all_files)} files...")
            for fpath in all_files:
                print(f"   📄 {os.path.basename(fpath)}")
                parts.append(self._read_file_for_prompt(fpath, max_lines_per_file))
        
        parts.append("\n=== END ATTACHED FILES ===\n")
        composite_prompt = ''.join(parts)
        
        print(f"📝 Total prompt size: {len(composite_prompt)} chars")
        
        # Use send_prompt but override max_wait
        # We temporarily monkey-patch the wait time for long responses
        return await self._send_prompt_internal(composite_prompt, max_wait=max_wait)

    async def _send_prompt_internal(self, prompt: str, max_wait: int = 90) -> str:
        """Internal send_prompt with configurable max_wait."""
        if not self.claude_window_id:
            return "Error: Agent not started. Call start() first."

        try:
            print(f"📝 Preparing prompt of length {len(prompt)}...")
            self._clear_clipboard()
            
            # Write prompt to a temp file for xdotool to type robustly
            prompt_file = "/tmp/claude_prompt.txt"
            with open(prompt_file, 'w') as f:
                f.write(prompt)

            # Focus and Paste
            geo = self._get_window_geometry(self.claude_window_id)
            if geo:
                print(f"🪟 Window geometry: {geo}")
                # Click center first (hits the input box on the home screen)
                cx, cy = geo['x'] + geo['width'] // 2, geo['y'] + geo['height'] // 2
                self._run_command(f'xdotool windowactivate --sync {self.claude_window_id} mousemove {cx} {cy} click 1')
                time.sleep(0.2)
                # Click bottom second (hits the input box on an active chat)
                tx, ty = geo['x'] + geo['width'] // 2, geo['y'] + geo['height'] - 80
                self._run_command(f'xdotool windowactivate --sync {self.claude_window_id} mousemove {tx} {ty} click 1')
                await asyncio.sleep(0.5)
            
            print("⌨️ Typing prompt...")
            # Use xdotool type --file to reliably insert text without clipboard issues
            self._run_command(f'xdotool windowactivate --sync {self.claude_window_id} type --delay 2 --clearmodifiers --file {prompt_file}')
            await asyncio.sleep(0.5)
            self._send_keys(self.claude_window_id, 'Return')
            await asyncio.sleep(0.5)
            self._send_keys(self.claude_window_id, 'KP_Enter')

            print(f"⏳ Waiting for Claude to respond (max {max_wait}s)...")
            elapsed = 0
            last_content = ""

            while elapsed < max_wait:
                await asyncio.sleep(5)
                elapsed += 5

                content = await self._try_extract_via_copy_button(prompt)
                if not content:
                    content = await self._try_extract_via_select_all(prompt)

                if content:
                    if content != last_content:
                        last_content = content
                    else:
                        cleaned = self._clean_response(content)
                        if len(cleaned) > 5:
                            print(f"✅ Successfully extracted response ({len(cleaned)} chars).")
                            await response_logger.log_response(
                                agent_name="ClaudeAgentImproved",
                                prompt=prompt[:500],
                                raw_response=content,
                                cleaned_response=cleaned,
                                metadata={"status": "success"}
                            )
                            return cleaned
                else:
                    print(f"... still waiting ({elapsed}s elapsed) ...")

            return f"Error: Response timeout. Last seen: {last_content[:50]}..."

        except Exception as e:
            return f"Error during send_prompt: {e}"

    async def run(self, payload: Dict[str, Any]) -> Any:
        """Standard entry point for BridgeWorker."""
        prompt = payload.get("prompt", "")
        if not prompt:
            return "Error: No prompt provided in payload"
        file_paths = payload.get("file_paths", [])
        directories = payload.get("directories", [])
        if file_paths or directories:
            return await self.send_prompt_with_files(prompt, file_paths=file_paths, directories=directories)
        return await self.send_prompt(prompt)
