import os
import random
import requests
from dotenv import load_dotenv

load_dotenv()

# List of prioritized models (Reasoning -> High Quality -> Free)
MODEL_QUEUE = [
    "openrouter/google/gemini-2.0-flash-thinking-exp:free",
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "openrouter/google/gemma-4-31b-it:free"
]

# Array of API keys (assuming multiple keys are stored in .env)
API_KEYS = [
    os.getenv("OPENROUTER_API_KEY"),
    os.getenv("OPENROUTER_API_KEY_2"),
    os.getenv("OPENROUTER_API_KEY_3"),
].filter(None) # Remove None values

class FreerideManager:
    def __init__(self):
        self.current_model_idx = 0
        self.current_key_idx = 0

    def get_next_fallback(self):
        """Rotates to the next model and key when a rate limit is hit."""
        self.current_model_idx = (self.current_model_idx + 1) % len(MODEL_QUEUE)
        self.current_key_idx = (self.current_key_idx + 1) % len(API_KEYS)
        return MODEL_QUEUE[self.current_model_idx], API_KEYS[self.current_key_idx]

    def get_current(self):
        return MODEL_QUEUE[self.current_model_idx], API_KEYS[self.current_key_idx]

# Singleton instance
manager = FreerideManager()
