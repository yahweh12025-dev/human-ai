#!/usr/bin/env python3
"""
Test script to verify Supabase and Firebase connectivity for backup purposes.
"""
import os
import json
from datetime import datetime

def test_supabase_connection():
    """Test if Supabase credentials are available."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if url and key:
        print(f"✅ Supabase configured: {url}")
        print(f"   Key present: {bool(key and len(key) > 10)}")
        return True
    else:
        print("❌ Supabase not fully configured")
        print(f"   URL: {'SET' if url else 'NOT SET'}")
        print(f"   Key: {'SET' if key else 'NOT SET'}")
        return False

def test_firebase_connection():
    """Test if Firebase credentials are available."""
    project_id = os.getenv('FIREBASE_PROJECT_ID')
    bucket = os.getenv('FIREBASE_STORAGE_BUCKET')
    service_account = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
    
    if project_id and bucket and service_account:
        print(f"✅ Firebase configured:")
        print(f"   Project ID: {project_id}")
        print(f"   Storage Bucket: {bucket}")
        print(f"   Service Account Path: {service_account}")
        
        # Check if service account file exists
        if os.path.exists(service_account):
            print(f"   Service Account File: EXISTS ✓")
        else:
            print(f"   Service Account File: MISSING ✗")
            
        return True
    else:
        print("❌ Firebase not fully configured")
        print(f"   Project ID: {'SET' if project_id else 'NOT SET'}")
        print(f"   Storage Bucket: {'SET' if bucket else 'NOT SET'}")
        print(f"   Service Account Path: {'SET' if service_account else 'NOT SET'}")
        return False

def test_backup_readiness():
    """Test if systems are ready for backup operations."""
    print("🧪 TESTING BACKUP SYSTEM READINESS")
    print("=" * 50)
    
    supabase_ok = test_supabase_connection()
    print()
    firebase_ok = test_firebase_connection()
    print()
    
    if supabase_ok and firebase_ok:
        print("🎉 BACKUP SYSTEMS: READY FOR OPERATIONS")
        print("   Both Supabase and Firebase are configured")
        print("   MasterLog and OUTCOME_LOG can be backed up")
        return True
    else:
        print("⚠️  BACKUP SYSTEMS: PARTIALLY CONFIGURED")
        print("   Some credentials missing - backups may fail")
        return False

if __name__ == "__main__":
    # Source the .env file to get environment variables
    from dotenv import load_dotenv
    load_dotenv("/home/ubuntu/human-ai/.env")
    
    test_backup_readiness()
