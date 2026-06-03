import requests
import json

url = "http://0.0.0.0:4000/v1/chat/completions"
headers = {
    "Authorization": "Bearer sk-1234",
    "Content-Type": "application/json"
}

# Read the trading strategy file
with open("./human-ai/agents/trading-agent/trading_strategy.py", "r") as f:
    code = f.read()

prompt = f"""Please review this trading strategy Python file and suggest improvements. Here is the code:

{code}

Please provide specific suggestions for improvement, focusing on code quality, potential bugs, performance optimizations, and trading logic enhancements."""

data = {
    "model": "gemini-3.1-pro-preview",
    "messages": [
        {
            "role": "user",
            "content": prompt
        }
    ]
}

response = requests.post(url, headers=headers, json=data)
print(response.json())