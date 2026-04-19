import os
from dotenv import load_dotenv
load_dotenv()

# STRICTLY FREE MODELS ONLY
WORKING_MODELS = [
    "openrouter/google/gemma-4-31b-it:free",
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    "openrouter/free"
]

class FreerideManager:
    MODEL_QUEUE = [
        "openrouter/google/gemma-4-31b-it:free",
        "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
        "openrouter/free"
    ]
    def __init__(self):
        self.current_model_index = 0

    def get_current(self):
        model = self.MODEL_QUEUE[self.current_model_index]
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        return model, api_key

    def get_next_fallback(self):
        self.current_model_index = (self.current_model_index + 1) % len(self.MODEL_QUEUE)
        return self.get_current()

manager = FreerideManager()
