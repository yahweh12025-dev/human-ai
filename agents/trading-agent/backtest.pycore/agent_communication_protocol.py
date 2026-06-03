#!/usr/bin/env python3
"""
Standardized Cross-Agent Communication Protocol System
Provides message validation, routing, and guaranteed delivery for reliable inter-agent coordination
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import enum

class MessageType(enum.Enum):
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    RESOURCE_REQUEST = "resource_request"
    RESOURCE_RESPONSE = "resource_response"
    ERROR_REPORT = "error_report"
    HEARTBEAT = "heartbeat"
    COORDINATION = "coordination"
    VERIFICATION_REQUEST = "verification_request"
    VERIFICATION_RESPONSE = "verification_response"

class MessagePriority(enum.Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class MessageStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    EXPIRED = "expired"

class AgentCommunicationProtocol:
    def __init__(self, data_dir: str = "/home/yahwehatwork/human-ai"):
        self.data_dir = data_dir
        self.protocol_dir = os.path.join(data_dir, "core/communication_protocol")
        self.messages_file = os.path.join(self.protocol_dir, "messages.json")
        self.routes_file = os.path.join(self.protocol_dir, "routing_table.json")
        self.agents_file = os.path.join(self.protocol_dir, "registered_agents.json")
        self.history_file = os.path.join(self.protocol_dir, "message_history.json")
        
        # Ensure directories exist
        os.makedirs(self.protocol_dir, exist_ok=True)
        
        # Initialize protocol files
        self._initialize_protocol_files()
    
    def _initialize_protocol_files(self):
        """Initialize all protocol-related files"""
        if not os.path.exists(self.messages_file):
            with open(self.messages_file, 'w') as f:
                json.dump({"messages": [], "pending": [], "sent": []}, f, indent=2)
        
        if not os.path.exists(self.routes_file):
            default_routes = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "routes": {
                    "Hermes": ["OpenCode", "Researcher"],
                    "OpenCode": ["Hermes"],
                    "Researcher": ["Hermes"]
                }
            }
            with open(self.routes_file, 'w') as f:
                json.dump(default_routes, f, indent=2)
        
        if not os.path.exists(self.agents_file):
            with open(self.agents_file, 'w') as f:
                json.dump({"agents": {}, "last_updated": datetime.now().isoformat()}, f, indent=2)
        
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w') as f:
                json.dump({"history": []}, f, indent=2)
    
    def register_agent(self, agent_id: str, capabilities: List[str] = None, 
                      endpoint: str = None) -> bool:
        """Register an agent in the communication protocol"""
        with open(self.agents_file, 'r') as f:
            agents_data = json.load(f)
        
        agent_info = {
            "agent_id": agent_id,
            "registered_at": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat(),
            "capabilities": capabilities or [],
            "endpoint": endpoint or f"agent://{agent_id}",
            "status": "active",
            "message_count": 0
        }
        
        agents_data["agents"][agent_id] = agent_info
        agents_data["last_updated"] = datetime.now().isoformat()
        
        with open(self.agents_file, 'w') as f:
            json.dump(agents_data, f, indent=2)
        
        return True
    
    def send_message(self, sender: str, recipient: str, 
                    message_type: MessageType, content: Dict[str, Any],
                    priority: MessagePriority = MessagePriority.MEDIUM,
                    requires_ack: bool = True) -> str:
        """Send a message through the protocol"""
        message_id = str(uuid.uuid4())
        
        message = {
            "message_id": message_id,
            "sender": sender,
            "recipient": recipient,
            "type": message_type.value,
            "priority": priority.value,
            "requires_ack": requires_ack,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "status": MessageStatus.PENDING.value,
            "attempts": 0,
            "max_attempts": 3,
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        # Validate recipient
        if not self._can_send_to(sender, recipient):
            message["status"] = MessageStatus.FAILED.value
            message["error"] = f"Cannot send message from {sender} to {recipient} - routing not allowed"
        else:
            # Add to pending messages
            with open(self.messages_file, 'r') as f:
                messages_data = json.load(f)
            
            messages_data["pending"].append(message)
            messages_data["messages"].append(message)  # Keep in main list for history
            
            with open(self.messages_file, 'w') as f:
                json.dump(messages_data, f, indent=2)
            
            # Update sender's message count
            self._update_agent_message_count(sender, 1)
        
        # Add to history
        self._add_to_history(message)
        
        return message_id
    
    def _can_send_to(self, sender: str, recipient: str) -> bool:
        """Check if sender can send to recipient based on routing rules"""
        with open(self.routes_file, 'r') as f:
            routes_data = json.load(f)
        
        routes = routes_data.get("routes", {})
        allowed_recipients = routes.get(sender, [])
        
        # Allow sending to self for testing/notifications
        if sender == recipient:
            return True
        
        return recipient in allowed_recipients
    
    def receive_message(self, recipient: str) -> List[Dict]:
        """Get pending messages for a recipient"""
        with open(self.messages_file, 'r') as f:
            messages_data = json.load(f)
        
        pending_messages = [
            msg for msg in messages_data["pending"]
            if msg["recipient"] == recipient and 
            msg["status"] == MessageStatus.PENDING.value
        ]
        
        # Mark messages as sent when retrieved
        for msg in pending_messages:
            msg["status"] = MessageStatus.SENT.value
            msg["sent_at"] = datetime.now().isoformat()
        
        if pending_messages:
            with open(self.messages_file, 'w') as f:
                json.dump(messages_data, f, indent=2)
        
        return pending_messages
    
    def acknowledge_message(self, message_id: str, recipient: str) -> bool:
        """Acknowledge receipt of a message"""
        with open(self.messages_file, 'r') as f:
            messages_data = json.load(f)
        
        for msg in messages_data["messages"]:
            if msg["message_id"] == message_id and msg["recipient"] == recipient:
                msg["status"] = MessageStatus.ACKNOWLEDGED.value
                msg["acknowledged_at"] = datetime.now().isoformat()
                
                # Remove from pending if it was there
                messages_data["pending"] = [
                    m for m in messages_data["pending"] 
                    if m["message_id"] != message_id
                ]
                
                with open(self.messages_file, 'w') as f:
                    json.dump(messages_data, f, indent=2)
                
                self._add_to_history(msg)
                return True
        
        return False
    
    def _update_agent_message_count(self, agent_id: str, increment: int):
        """Update an agent's message count"""
        with open(self.agents_file, 'r') as f:
            agents_data = json.load(f)
        
        if agent_id in agents_data["agents"]:
            agents_data["agents"][agent_id]["message_count"] += increment
            agents_data["agents"][agent_id]["last_heartbeat"] = datetime.now().isoformat()
            
            with open(self.agents_file, 'w') as f:
                json.dump(agents_data, f, indent=2)
    
    def _add_to_history(self, message: Dict):
        """Add a message to the history"""
        with open(self.history_file, 'r') as f:
            history_data = json.load(f)
        
        history_data["history"].append(message)
        
        # Keep last 1000 messages
        if len(history_data["history"]) > 1000:
            history_data["history"] = history_data["history"][-1000:]
        
        with open(self.history_file, 'w') as f:
            json.dump(history_data, f, indent=2)
    
    def get_protocol_status(self) -> Dict[str, Any]:
        """Get the current status of the communication protocol"""
        with open(self.messages_file, 'r') as f:
            messages_data = json.load(f)
        
        with open(self.agents_file, 'r') as f:
            agents_data = json.load(f)
        
        with open(self.routes_file, 'r') as f:
            routes_data = json.load(f)
        
        pending_count = len([m for m in messages_data["pending"] 
                           if m["status"] == MessageStatus.PENDING.value])
        sent_count = len([m for m in messages_data["pending"] 
                         if m["status"] == MessageStatus.SENT.value])
        acked_count = len([m for m in messages_data["messages"] 
                          if m["status"] == MessageStatus.ACKNOWLEDGED.value])
        
        return {
            "timestamp": datetime.now().isoformat(),
            "protocol_version": "1.0",
            "registered_agents": len(agents_data.get("agents", {})),
            "message_stats": {
                "total_messages": len(messages_data.get("messages", [])),
                "pending": pending_count,
                "sent": sent_count,
                "acknowledged": acked_count,
                "failed": len([m for m in messages_data.get("messages", [])
                              if m.get("status") == MessageStatus.FAILED.value])
            },
            "routing_rules": len(routes_data.get("routes", {})),
            "recent_activity": self._get_recent_activity()
        }
    
    def _get_recent_activity(self) -> List[Dict]:
        """Get recent message activity"""
        with open(self.history_file, 'r') as f:
            history_data = json.load(f)
        
        history = history_data.get("history", [])
        # Get last 10 messages
        recent = history[-10:] if len(history) >= 10 else history
        
        # Format for output
        formatted = []
        for msg in recent:
            formatted.append({
                "message_id": msg["message_id"][:8] + "...",
                "sender": msg["sender"],
                "recipient": msg["recipient"],
                "type": msg["type"],
                "timestamp": msg["timestamp"],
                "status": msg["status"]
            })
        
        return formatted

def main():
    """Main entry point for the Agent Communication Protocol"""
    protocol = AgentCommunicationProtocol()
    
    # Register default agents if not already registered
    default_agents = ["Hermes", "OpenCode", "Researcher"]
    for agent in default_agents:
        protocol.register_agent(agent, 
                               capabilities=["task_execution", "communication"],
                               endpoint=f"agent://{agent}")
    
    # Send a test message to demonstrate functionality
    test_message_id = protocol.send_message(
        sender="Hermes",
        recipient="OpenCode",
        message_type=MessageType.TASK_REQUEST,
        content={
            "task": "Verify communication protocol functionality",
            "details": "This is a test message to verify the communication protocol is working correctly"
        },
        priority=MessagePriority.HIGH
    )
    
    # Check for messages for OpenCode
    messages = protocol.receive_message("OpenCode")
    
    # Acknowledge the message if received
    if messages:
        protocol.acknowledge_message(messages[0]["message_id"], "OpenCode")
    
    # Get protocol status
    status = protocol.get_protocol_status()
    
    print(f"Agent Communication Protocol Initialized")
    print(f"Registered Agents: {status['registered_agents']}")
    print(f"Total Messages: {status['message_stats']['total_messages']}")
    print(f"Pending Messages: {status['message_stats']['pending']}")
    print(f"Test Message Sent: {test_message_id}")
    
    # Save protocol status
    status_file = os.path.join(protocol.protocol_dir, "protocol_status.json")
    with open(status_file, 'w') as f:
        json.dump(status, f, indent=2)
    
    print(f"Protocol status saved to: {status_file}")
    return True

if __name__ == "__main__":
    main()