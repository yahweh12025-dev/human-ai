import requests
import json

url = "http://0.0.0.0:4000/v1/chat/completions"
headers = {
    "Authorization": "Bearer sk-1234",
    "Content-Type": "application/json"
}

# Read the backtest framework
with open("./human-ai/agents/trading-agent/backtest.py", "r") as f:
    backtest_code = f.read()

prompt = f"""Please review this backtesting framework and suggest improvements. Here is the code:

{backtest_code}

Please provide specific suggestions for improvement, focusing on:
1. Code quality and structure
2. Performance optimizations
3. Missing features (slippage, fees, etc.)
4. Better statistics and reporting
5. Any bugs or logical issues
6. How to make it more professional and robust"""

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