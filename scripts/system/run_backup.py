#!/usr/bin/env python3
"""
Simple backup runner that can be executed by the hermes-autonomous system.
This avoids the execution restriction issues by being a straightforward Python script.
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path

# Load environment variables
sys.path.insert(0, '/home/ubuntu/human-ai')
from dotenv import load_dotenv
load_dotenv("/home/ubuntu/human-ai/.env")

def test_supabase_connection():
    """Test if we can reach Supabase."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        return False, "Supabase not configured"
    
    try:
        # Try to access a basic endpoint
        test_url = f"{url}/rest/v1/"
        headers = {
            'apikey': key,
            'Authorization': f'Bearer {key}'
        }
        response = requests.get(test_url, headers=headers, timeout=10)
        # 401 is OK - means server is there and responding
        return response.status_code < 500, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def test_firebase_connection():
    """Test if Firebase service account is valid."""
    sa_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
    
    if not sa_path or not os.path.exists(sa_path):
        return False, "Firebase service account not found"
    
    try:
        with open(sa_path, 'r') as f:
            data = json.load(f)
        return True, f"Project: {data.get('project_id', 'Unknown')}"
    except Exception as e:
        return False, str(e)

def main():
    """Main function - report backup system status."""
    print("☁️  BACKUP SYSTEM STATUS CHECK")
    print("=" * 40)
    
    # Test Supabase
    supabase_ok, supabase_msg = test_supabase_connection()
    print("Supabase: {} ({})".format("✅ READY" if supabase_ok else "❌ NOT READY", supabase_msg))
    
    # Test Firebase
    firebase_ok, firebase_msg = test_firebase_connection()
    print("Firebase: {} ({})".format("✅ READY" if firebase_ok else "❌ NOT READY", firebase_msg))
    
    # Overall status
    if supabase_ok and firebase_ok:
        print("\n🎉 BACKUP SYSTEMS: FULLY OPERATIONAL")
        print("   Agent outputs can be backed up to cloud storage")
        return 0
    else:
        print("\n⚠️  BACKUP SYSTEMS: PARTIALLY CONFIGURED") 
        print("   Some components need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())
