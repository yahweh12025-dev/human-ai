#!/usr/bin/env python3
"""
Integration Verification Suite
Tests all external service connections and reports status.
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / '.env')


def verify_supabase() -> Dict:
    """Verify Supabase connection"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return {"status": "not_configured", "service": "Supabase"}
    try:
        resp = requests.get(
            f"{url}/rest/v1/",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=10
        )
        return {
            "status": "connected" if resp.status_code in (200, 404) else "error",
            "service": "Supabase",
            "url": url,
            "http_code": resp.status_code
        }
    except Exception as e:
        return {"status": "error", "service": "Supabase", "error": str(e)}


def verify_dify() -> Dict:
    """Verify Dify RAG connection"""
    key = os.getenv("DIFY_API_KEY")
    base = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1")
    if not key:
        return {"status": "not_configured", "service": "Dify"}
    try:
        resp = requests.get(
            f"{base}/parameters",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10
        )
        return {
            "status": "connected" if resp.status_code == 200 else "auth_error",
            "service": "Dify",
            "url": base,
            "http_code": resp.status_code
        }
    except Exception as e:
        return {"status": "error", "service": "Dify", "error": str(e)}


def verify_openrouter() -> Dict:
    """Verify OpenRouter LLM connection"""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return {"status": "not_configured", "service": "OpenRouter"}
    try:
        resp = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10
        )
        data = resp.json() if resp.status_code == 200 else {}
        return {
            "status": "connected" if resp.status_code == 200 else "error",
            "service": "OpenRouter",
            "models_available": len(data.get("data", [])),
            "http_code": resp.status_code
        }
    except Exception as e:
        return {"status": "error", "service": "OpenRouter", "error": str(e)}


def verify_groq() -> Dict:
    """Verify Groq API connection"""
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return {"status": "not_configured", "service": "Groq"}
    try:
        resp = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10
        )
        return {
            "status": "connected" if resp.status_code == 200 else "error",
            "service": "Groq",
            "http_code": resp.status_code
        }
    except Exception as e:
        return {"status": "error", "service": "Groq", "error": str(e)}


def verify_telegram() -> Dict:
    """Verify Telegram bot connection"""
    token = os.getenv("OPENCLAW_BOT_TOKEN")
    if not token:
        return {"status": "not_configured", "service": "Telegram"}
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=10
        )
        data = resp.json()
        return {
            "status": "connected" if data.get("ok") else "error",
            "service": "Telegram",
            "bot_name": data.get("result", {}).get("username", "unknown")
        }
    except Exception as e:
        return {"status": "error", "service": "Telegram", "error": str(e)}


def verify_binance_testnet() -> Dict:
    """Verify Binance testnet connectivity"""
    try:
        resp = requests.get(
            "https://testnet.binancefuture.com/fapi/v1/time",
            timeout=10
        )
        return {
            "status": "connected" if resp.status_code == 200 else "error",
            "service": "Binance Testnet",
            "server_time": resp.json().get("serverTime") if resp.status_code == 200 else None
        }
    except Exception as e:
        return {"status": "error", "service": "Binance Testnet", "error": str(e)}


def verify_n8n() -> Dict:
    """Verify n8n workflow engine"""
    key = os.getenv("N8N_API_KEY")
    if not key:
        return {"status": "not_configured", "service": "n8n"}
    return {"status": "configured", "service": "n8n", "key_present": True}


def verify_firebase() -> Dict:
    """Verify Firebase configuration"""
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    if not project_id:
        return {"status": "not_configured", "service": "Firebase"}
    sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "")
    sa_exists = Path(sa_path).exists() if sa_path else False
    return {
        "status": "configured" if project_id else "not_configured",
        "service": "Firebase",
        "project_id": project_id,
        "service_account_exists": sa_exists,
        "storage_bucket": os.getenv("FIREBASE_STORAGE_BUCKET")
    }


def run_all_verifications() -> Dict:
    """Run all integration verifications"""
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "integrations": []
    }

    checks = [
        verify_supabase,
        verify_dify,
        verify_openrouter,
        verify_groq,
        verify_telegram,
        verify_binance_testnet,
        verify_n8n,
        verify_firebase,
    ]

    for check in checks:
        result = check()
        results["integrations"].append(result)

    # Summary
    connected = sum(1 for r in results["integrations"] if r["status"] == "connected")
    configured = sum(1 for r in results["integrations"] if r["status"] == "configured")
    errors = sum(1 for r in results["integrations"] if r["status"] == "error")
    not_configured = sum(1 for r in results["integrations"] if r["status"] == "not_configured")

    results["summary"] = {
        "total": len(results["integrations"]),
        "connected": connected,
        "configured": configured,
        "errors": errors,
        "not_configured": not_configured
    }

    return results


def main():
    print("=" * 60)
    print("Integration Verification Suite")
    print("=" * 60)

    results = run_all_verifications()

    for integration in results["integrations"]:
        status_icon = {
            "connected": "✅",
            "configured": "⚙️",
            "error": "❌",
            "not_configured": "⚠️",
            "auth_error": "🔑"
        }.get(integration["status"], "❓")

        print(f"  {status_icon} {integration['service']}: {integration['status']}")
        if "error" in integration:
            print(f"      Error: {integration['error'][:80]}")

    print(f"\n{'=' * 60}")
    summary = results["summary"]
    print(f"  Connected: {summary['connected']} | Configured: {summary['configured']} | Errors: {summary['errors']} | Missing: {summary['not_configured']}")
    print(f"{'=' * 60}")

    # Save results
    output_file = Path.home() / "human-ai" / "data" / "data" / "logs" / "integration_verification.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to: {output_file}")

    return results


if __name__ == "__main__":
    main()
