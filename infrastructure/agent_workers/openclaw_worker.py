#!/usr/bin/env python3
"""
OpenClaw Worker - Processes messages from OpenClaw's incoming directory
and sends responses to outgoing directory.
"""
import os
import time
import json
import asyncio
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
WORK_DIR = os.getenv("WORK_DIR", "/home/yahwehatwork/human-ai")
sys.path.insert(0, WORK_DIR)

from hermes_tools import delegate_task, terminal, send_message

class OpenClawWorker:
    def __init__(self):
        self.work_dir = Path(WORK_DIR)
        self.agent_name = "openclaw"
        self.incoming_dir = self.work_dir / "infrastructure" / "agent_comms" / self.agent_name / "incoming"
        self.outgoing_dir = self.work_dir / "infrastructure" / "agent_comms" / self.agent_name / "outgoing"
        self.archive_dir = self.work_dir / "infrastructure" / "agent_comms" / self.agent_name / "archive"
        self.status_dir = self.work_dir / "infrastructure" / "agent_comms" / self.agent_name / "status"
        
        # Ensure directories exist
        for dir_path in [self.incoming_dir, self.outgoing_dir, self.archive_dir, self.status_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        self.status_file = self.status_dir / "worker.status"
        self.update_status("starting")
        
    def update_status(self, status, details=None):
        """Update worker status file"""
        status_data = {
            "agent": self.agent_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "details": details or ""
        }
        with open(self.status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
            
    def process_message(self, message_file):
        """Process a single message file"""
        try:
            with open(message_file, 'r') as f:
                message_data = json.load(f)
                
            print(f"[{self.agent_name}] Processing message from {message_data.get('from', 'unknown')}: {message_data.get('content', '')[:100]}...")
            
            # Update status
            self.update_status("processing", f"Processing message from {message_data.get('from')}")
            
            # Extract message content
            content = message_data.get('content', '')
            from_agent = message_data.get('from', 'unknown')
            
            # Process based on message type or content
            if "review" in content.lower() or "improve" in content.lower() or "fix" in content.lower():
                # This is a request to review/improve the repo
                result = self.review_and_improve_repo(content, from_agent)
            elif "gateway" in content.lower() or "network" in content.lower() or "connection" in content.lower():
                # This is related to gateway/network tasks
                result = self.handle_gateway_task(content, from_agent)
            else:
                # General inquiry or status request
                result = self.handle_general_inquiry(content, from_agent)
                
            # Send response
            self.send_response(from_agent, result, message_data.get('id', 'unknown'))
            
            # Archive the processed message
            archive_file = self.archive_dir / f"{message_file.stem}_{int(time.time())}.json"
            message_file.rename(archive_file)
            
            self.update_status("idle")
            return True
            
        except Exception as e:
            print(f"[{self.agent_name}] Error processing message {message_file}: {e}")
            self.update_status("error", str(e))
            return False
            
    def review_and_improve_repo(self, content, from_agent):
        """Review the repository and suggest improvements"""
        try:
            # Use delegate_task to spawn a subagent for infrastructure/network review
            result = delegate_task(
                goal=f"Review the human-ai repository for infrastructure and networking improvements based on this request: {content}",
                context=f"""
                Repository: {WORK_DIR}
                Requesting agent: {from_agent}
                Current time: {datetime.utcnow().isoformat()}
                Focus areas: gateway configuration, network setup, proxy settings, connectivity, OpenClaw-specific improvements
                """,
                toolsets=["terminal", "file", "web"],
                role="orchestrator"
            )
            
            return f"OpenClaw review completed. Results: {str(result)[:500]}..."
        except Exception as e:
            return f"Error during review: {str(e)}"
            
    def handle_gateway_task(self, content, from_agent):
        """Handle gateway/network related tasks"""
        try:
            # Check OpenClaw gateway status
            cmd = "ps aux | grep openclaw | grep -v grep"
            result = terminal(cmd)
            
            gateway_status = "running" if result['exit_code'] == 0 and result['output'].strip() else "not running"
            
            response = f"""OpenClaw Gateway Status: {gateway_status}

Active OpenClaw processes:
{result['output']}

Task request: {content}

The OpenClaw gateway is currently {gateway_status}. For any gateway-specific tasks, please ensure the gateway remains running as requested."""
            
            return response
        except Exception as e:
            return f"Error handling gateway task: {str(e)}"
            
    def handle_general_inquiry(self, content, from_agent):
        """Handle general inquiries"""
        try:
            response = f"""OpenClaw agent received message from {from_agent}:
"{content}"

Current status: Operational
Repository: {WORK_DIR}
Time: {datetime.utcnow().isoformat()}

I am ready to assist with gateway management, network configuration, connectivity testing, and infrastructure improvements."""
            
            return response
        except Exception as e:
            return f"Error handling inquiry: {str(e)}"
            
    def send_response(self, to_agent, content, original_message_id):
        """Send a response message to another agent"""
        response_data = {
            "id": f"{self.agent_name}_{int(time.time())}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "from": self.agent_name,
            "to": to_agent,
            "content": content,
            "reply_to": original_message_id,
            "type": "response"
        }
        
        # Ensure target agent's incoming directory exists
        target_incoming = self.work_dir / "infrastructure" / "agent_comms" / to_agent / "incoming"
        target_incoming.mkdir(parents=True, exist_ok=True)
        
        response_file = target_incoming / f"{response_data['id']}.json"
        with open(response_file, 'w') as f:
            json.dump(response_data, f, indent=2)
            
        print(f"[{self.agent_name}] Sent response to {to_agent}: {response_file.name}")
        
    def run(self):
        """Main worker loop"""
        self.update_status("running", "Worker started and monitoring incoming directory")
        print(f"[{self.agent_name}] Worker started. Monitoring {self.incoming_dir}")
        
        processed_files = set()
        
        while True:
            try:
                # Check for new message files
                message_files = list(self.incoming_dir.glob("*.json"))
                
                for message_file in message_files:
                    if message_file not in processed_files:
                        if self.process_message(message_file):
                            processed_files.add(message_file)
                            
                # Clean up processed files set periodically (every 100 files)
                if len(processed_files) > 100:
                    processed_files = set()
                    
                # Sleep briefly to avoid excessive CPU usage
                time.sleep(1)
                
            except KeyboardInterrupt:
                print(f"[{self.agent_name}] Worker interrupted by user")
                self.update_status("stopped", "Worker stopped by user")
                break
            except Exception as e:
                print(f"[{self.agent_name}] Worker error: {e}")
                self.update_status("error", str(e))
                time.sleep(5)  # Wait longer on error
                
        self.update_status("stopped", "Worker terminated")

if __name__ == "__main__":
    worker = OpenClawWorker()
    worker.run()