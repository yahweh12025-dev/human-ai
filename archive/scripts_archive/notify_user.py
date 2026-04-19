import requests
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = "8306402529:AAHs_WPPZv1wsxDEIgU0P0Twc6PRm_8A_xA"
CHAT_ID = "8412298553"

def send_alert(message: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": f"🚨 *Human-AI Action Required* 🚨\n\n{message}",
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"Notification failed: {e}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
        send_alert(msg)
