def validate_free_model(model_name: str) -> bool:
    """
    Mandatory Guardrail: Ensures that only free models are used.
    Returns True if the model is free, False otherwise.
    """
    if not model_name:
        return False
    return model_name.endswith(':free') or model_name == 'openrouter/free'

def enforce_free_model(model_name: str, fallback_model: str = 'openrouter/free'):
    """
    Validates a model and returns the fallback if the requested model is paid.
    """
    if validate_free_model(model_name):
        return model_name
    return fallback_model
