# pi-dify-schema-gen

Helps Pi automatically write the JSON payloads needed to trigger Dify workflows.

## Description

This skill provides utilities to generate JSON payloads for Dify workflow APIs, making it easier to integrate Pi with Dify-based automation.

## Usage

Import and use the provided functions in your Pi workflows.

## Functions

- `create_workflow_payload(inputs_dict, response_mode="blocking")`: Generates the JSON payload for a Dify workflow run.
- `add_file_to_payload(payload, file_path, file_type)`: Adds a file to the payload for workflows that accept file inputs.

## Example

```python
from skills.pi_dify_schema_gen import create_workflow_payload

payload = create_workflow_payload({"query": "What is the meaning of life?"})
# Then send payload to Dify API endpoint
```