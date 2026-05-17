# LLM Integration Guide

## Overview
This document describes how to integrate various LLM providers (including NVIDIA Nemotron via OpenRouter, AnythingLLM, and Vertex AI as fallback) into the workflow used by Opencode, Pi.dev, and Hermes.

## Prerequisites
- Docker installed and running
- Google Cloud SDK installed (`gcloud`)
- Python package `litellm` installed (via `pip install --break-system-packages litellm`)
- Environment variables stored in `/home/yahwehatwork/human-ai/.env` (already gitignored)

## Environment Variables
Add the following to `.env` (already present for NVIDIA_API_KEY; we added ANYTHING_LLM_API_KEY):

```dotenv
# NVIDIA API Key (for Nemotron models via OpenRouter)
NVIDIA_API_KEY=${NVIDIA_API_KEY}

# AnythingLLM API Key
ANYTHING_LLM_API_KEY=${ANYTHINGLLM_API_KEY}

# Optional: Vertex AI Application Default Credentials (ADC) are used automatically when gcloud auth is configured.
```

## Installing Dependencies

### Google Cloud SDK
```bash
# Already installed via apt; verify:
gcloud version
# If not present:
# sudo apt-get install -y apt-transport-https ca-certificates gnupg
# echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
# curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
# sudo apt-get update && sudo apt-get install -y google-cloud-sdk
```

### LiteLLM
```bash
pip install --break-system-packages litellm
# litellm provides a unified API to call OpenAI, Azure, HuggingFace, Vertex AI, etc.
```

### AnythingLLM (Docker)
```bash
# Pull the official AnythingLLM image
docker pull mintplexlabs/anythingllm:latest

# Run the container (example)
docker run -d \
  --name anythingllm \
  -p 3001:3001 \
  -v $(pwd)/anythingllm-data:/app/data \
  -e ANYTHINGLLM_API_KEY=$ANYTHING_LLM_API_KEY \
  mintplexlabs/anythingllm:latest
```

> The AnythingLLM container will be accessible at `http://localhost:3001`.  
> The API key set above is required for admin endpoints.

## Using the Models

### Via LiteLLM (Python)
```python
from litellm import completion
import os

# Example: Call NVIDIA Nemotron via OpenRouter (using NVIDIA API key as bearer)
response = completion(
    model="openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    messages=[{"role": "user", "content": "Hello, world!"}],
    api_key=os.getenv("NVIDIA_API_KEY"),
    api_base="https://openrouter.ai/api/v1"
)

print(response.choices[0].message["content"])
```

### Via AnythingLLM API
AnythingLLM exposes a REST API; you can use it to ingest documents, query, etc.
See the AnythingLLM documentation for details: https://github.com/Mintplex-Labs/anything-llm

### Vertex AI Fallback
When `litellm` is called with a model like `vertex_ai/<model-name>`, it will use Application Default Credentials (ADC) from `gcloud auth application-default login`. Ensure you have run:
```bash
gcloud auth application-default login
```
to set up ADC.

## Integration with Opencode, Pi.dev, and Hermes
- **Opencode**: Use the above Python snippets or shell commands to invoke LLMs for code generation.
- **Pi.dev**: Can call the same LiteLLM wrapper for any LLM‑based tasks.
- **Hermes**: Can delegate tasks to subagents that use these LLMs, or call them directly via the `execute_code` tool.

## Updating Mission Control (OpenClaw)
After installing the above components, restart the OpenClaw gateway so that Mission Control picks up the new environment and services:

```bash
openclaw gateway restart
```

## Verification
1. Check that `.env` contains both keys and is not committed (`git status` should show no changes to `.env`).
2. Test a quick LLM call via Python as shown.
3. Verify AnythingLLM container is running: `docker ps | grep anythingllm`.
4. Ensure `gcloud` is authenticated and ADC is set.

## Troubleshooting
- If `litellm` installation fails due to externally-managed environment, use `--break-system-packages` or create a virtual environment.
- If AnythingLLM fails to start, check logs: `docker logs anythingllm`.
- If Google Cloud SDK commands fail, re‑run `gcloud auth login` and `gcloud auth application-default login`.

---