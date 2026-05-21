import json

def create_workflow_payload(inputs_dict, response_mode="blocking"):
    """
    Generates the JSON payload for a Dify workflow run.
    """
    return {
        "inputs": inputs_dict,
        "response_mode": response_mode,
        "user": "pi-dev"
    }

def add_file_to_payload(payload, file_path, file_type="text"):
    """
    Adds a file to the payload for workflows that accept file inputs.
    (This typically requires a prior upload to Dify's /files endpoint).
    """
    if "files" not in payload:
        payload["files"] = []
    
    payload["files"].append({
        "transfer_method": "local",
        "upload_file_id": file_path,
        "type": file_type
    })
    return payload

if __name__ == "__main__":
    # Simple test
    inputs = {"query": "Hello Dify!"}
    payload = create_workflow_payload(inputs)
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    payload = add_file_to_payload(payload, "file_123", "image")
    print(f"Payload with file: {json.dumps(payload, indent=2)}")
