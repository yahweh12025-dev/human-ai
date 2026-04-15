import requests
import os
import json

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "sk-proj-YOUR_OPENROUTER_API_KEY_HERE")
MODEL = "openrouter/google/gemma-4-31b-it:free"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

def test_openrouter_api():
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}", 
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "What is the capital of France?"}]
    }
    
    try:
        response = requests.post(
            API_URL,
            json=payload,
            headers=headers,
            timeout=60
        )
        
        if response.status_code == 429:
            print(f"⚠️ Rate limit hit. Please check your OpenRouter plan.")
            return
        
        response.raise_for_status()
        res_data = response.json()
        print(f"✅ API Response: {res_data['choices'][0]['message']['content']}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ API Request Error: {e}")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    test_openrouter_api()