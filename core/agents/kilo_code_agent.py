import os
import requests
import json

# Load API key from environment or use fallback
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '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')

def call_free_model(prompt):
    """
    Calls a free model via OpenRouter API.
    Ensures only free models are used.
    """
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY not found in environment.")
        return None
    
    # Using a stable free model identifier
    model_id = "meta-llama/llama-3-8b-instruct:free"
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "http://localhost:3000", # Required by some OpenRouter models
        "X-Title": "KiloCode-Integration",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error calling free model: {e}")
        return None

def handle_read(file_path):
    """
    Reads a file and uses the free model to summarize or analyze its content.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Use the free model to provide a brief analysis of the read content
        prompt = f"Analyze this code/text and provide a very brief summary: \n\n{content}"
        summary = call_free_model(prompt)
        
        return f"Content: {content}\n\nSummary: {summary}" if summary else content
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def handle_write(file_path, content):
    """
    Writes content to a file after optimizing it with the free model.
    """
    try:
        # Use free model to optimize/clean the content before writing
        prompt = f"Optimize this content for clarity and correctness. Return ONLY the optimized content without any commentary: \n\n{content}"
        optimized_content = call_free_model(prompt)
        
        final_content = optimized_content if optimized_content else content
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        return True
    except Exception as e:
        print(f"Error writing file: {e}")
        return False

def handle_edit(file_path, old_text, new_text):
    """
    Edits a file by replacing old_text with new_text, ensuring the change is validated by the free model.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if old_text not in content:
            print(f"Error: old_text not found in {file_path}")
            return False
        
        # Use free model to validate the edit
        prompt = f"Validate this change. Old: {old_text}\nNew: {new_text}\nDoes this change make sense? Reply ONLY with YES or NO."
        validation = call_free_model(prompt)
        
        if validation and "YES" in validation.upper():
            new_content = content.replace(old_text, new_text)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        else:
            print(f"Edit rejected by free model validation: {validation}")
            return False
    except Exception as e:
        print(f"Error editing file: {e}")
        return False

print("Kilo-Code Integration Agent initialized with OpenRouter Free Models")
