# Simple configuration for Trading Agent testing
# In a real deployment, you would fill in actual API keys

# Mixin configuration for fallback
mixin_config = {
    'llm_nos': ['test-model'],  # Simple test model
    'max_retries': 3,
    'base_delay': 0.5,
}

# Test configuration using environment variables or placeholders
native_oai_config = {
    'name': 'test-model',
    'apikey': 'test-key-for-development',  # In real use, this would come from env var
    'apibase': 'https://api.openai.com/v1',  # Placeholder - would be replaced with real endpoint
    'model': 'gpt-3.5-turbo',  # Using a common model for testing
    'api_mode': 'chat_completions',
    'max_retries': 3,
    'connect_timeout': 10,
    'read_timeout': 120,
    'temperature': 0.7,
    'max_tokens': 2048,
}
