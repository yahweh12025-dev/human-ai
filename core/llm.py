#!/usr/bin/env python3
"""
Shared LLM utility — NVIDIA NIM first, no OpenRouter dependency.
All agents should import from here rather than calling APIs directly.

Usage:
    from core.llm import complete
    response = complete("Write a trading signal summary for XAUUSD")
"""
import json
import logging
import os
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_env  = _ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

NVIDIA_KEY   = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/llama-3.1-nemotron-nano-8b-v1")
NVIDIA_BASE  = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

# Groq is a fast free fallback (no rate limit issues)
GROQ_KEY     = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama3-8b-8192"
GROQ_BASE    = "https://api.groq.com/openai/v1"


def complete(
    prompt: str,
    system: str = "You are a helpful assistant.",
    max_tokens: int = 512,
    temperature: float = 0.5,
    provider: str = "auto",   # "nvidia" | "groq" | "auto"
) -> str:
    """
    Call an LLM. Provider order: NVIDIA → Groq → hardcoded fallback.
    Never uses OpenRouter — avoids rate limit / cost issues.
    Returns response text or empty string on failure.
    """
    if provider in ("auto", "nvidia") and NVIDIA_KEY:
        result = _call(NVIDIA_BASE, NVIDIA_KEY, NVIDIA_MODEL,
                       prompt, system, max_tokens, temperature)
        if result:
            return result

    if provider in ("auto", "groq") and GROQ_KEY:
        result = _call(GROQ_BASE, GROQ_KEY, GROQ_MODEL,
                       prompt, system, max_tokens, temperature)
        if result:
            return result

    logger.warning("LLM unavailable — no NVIDIA_API_KEY or GROQ_API_KEY set")
    return ""


def _call(base: str, key: str, model: str, prompt: str, system: str,
          max_tokens: int, temperature: float) -> str:
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens":  max_tokens,
        "temperature": temperature,
    }).encode()
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.debug(f"LLM call failed ({base}): {e}")
        return ""
