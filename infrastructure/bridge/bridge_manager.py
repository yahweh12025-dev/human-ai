
import os
import json
import shutil
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/home/yahwehatwork/human-ai/infrastructure/bridge/bridge_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BridgeManager")

class BridgeMessage:
    """Standardized schema for all bus communications."""
    def __init__(self, sender: str, msg_type: str, subject: str, payload: Dict[str, Any], msg_id: str = None, status: str = "pending"):
        self.id = msg_id or str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()
        self.sender = sender
        self.type = msg_type  # INTENT | SIGNAL | RESULT | ERROR
        self.subject = subject
        self.payload = payload
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "sender": self.sender,
            "type": self.type,
            "subject": self.subject,
            "payload": self.payload,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BridgeMessage':
        return cls(
            sender=data['sender'],
            msg_type=data['type'],
            subject=data['subject'],
            payload=data['payload'],
            msg_id=data['id'],
            status=data.get('status', 'pending')
        )

class BridgeManager:
    """
    Man-in-the-middle orchestrator for the bidirectional communication bus.
    """
    def __init__(self, base_path: str = "/home/yahwehatwork/human-ai/memory/bus"):
        self.base_path = base_path
        self.dirs = {
            "inbound": os.path.join(base_path, "inbound"),
            "outbound": os.path.join(base_path, "outbound"),
            "processing": os.path.join(base_path, "processing"),
            "completed": os.path.join(base_path, "completed"),
            "failed": os.path.join(base_path, "failed")
        }
        self._ensure_dirs()

    def _ensure_dirs(self):
        for d in self.dirs.values():
            os.makedirs(d, exist_ok=True)

    async def post_message(self, direction: str, message: BridgeMessage) -> bool:
        """Posts a message to the specified direction (inbound or outbound)."""
        target_dir = self.dirs.get(direction)
        if not target_dir:
            logger.error(f"Invalid direction: {direction}")
            return False

        filename = f"{message.id}.json"
        filepath = os.path.join(target_dir, filename)
        
        try:
            # Atomic write: write to temp, then rename
            temp_path = f"{filepath}.tmp"
            with open(temp_path, 'w') as f:
                json.dump(message.to_dict(), f, indent=4)
            os.replace(temp_path, filepath)
            logger.info(f"📩 Posted {message.type} to {direction}: {message.subject} ({message.id})")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to post message: {e}")
            return False

    async def fetch_next_intent(self) -> Optional[BridgeMessage]:
        """Picks up the next pending intent from inbound and moves it to processing."""
        inbound_dir = self.dirs["inbound"]
        processing_dir = self.dirs["processing"]

        try:
            files = sorted(os.listdir(inbound_dir))
            if not files:
                return None

            target_file = files[0]
            src_path = os.path.join(inbound_dir, target_file)
            dest_path = os.path.join(processing_dir, target_file)

            # Atomic move to prevent multiple agents grabbing the same task
            os.replace(src_path, dest_path)
            
            with open(dest_path, 'r') as f:
                data = json.load(f)
            
            msg = BridgeMessage.from_dict(data)
            msg.status = "processing"
            
            logger.info(f"📥 Picked up intent: {msg.subject} ({msg.id})")
            return msg
        except Exception as e:
            logger.error(f"❌ Error fetching intent: {e}")
            return None

    async def complete_task(self, msg_id: str, result_payload: Dict[str, Any], success: bool = True):
        """Moves a message from processing to completed or failed with a result."""
        processing_dir = self.dirs["processing"]
        target_dir = self.dirs["completed"] if success else self.dirs["failed"]
        
        filename = f"{msg_id}.json"
        src_path = os.path.join(processing_dir, filename)
        dest_path = os.path.join(target_dir, filename)

        if not os.path.exists(src_path):
            logger.error(f"Task {msg_id} not found in processing.")
            return

        try:
            with open(src_path, 'r') as f:
                data = json.load(f)
            
            # Update status and payload
            data['status'] = "completed" if success else "failed"
            data['payload'].update(result_payload)
            data['timestamp_finished'] = datetime.utcnow().isoformat()

            # Atomic move with updated data
            temp_path = f"{dest_path}.tmp"
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=4)
            os.replace(temp_path, dest_path)
            
            # Clean up processing file
            os.remove(src_path)
            
            logger.info(f"🏁 Task {msg_id} marked as {'SUCCESS' if success else 'FAILED'}.")
        except Exception as e:
            logger.error(f"❌ Error completing task: {e}")

if __name__ == "__main__":
    # Quick manual test
    async def test():
        bm = BridgeManager()
        m = BridgeMessage(sender="test_user", msg_type="INTENT", subject="Test Subject", payload={"val": 1})
        await bm.post_message("inbound", m)
        print("Posted test message.")
        
        picked = await bm.fetch_next_intent()
        if picked:
            print(f"Picked up: {picked.subject}")
            await bm.complete_task(picked.id, {"result": "working"}, success=True)
            print("Completed test task.")
    
    asyncio.run(test())
