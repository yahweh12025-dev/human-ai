#!/usr/bin/env python3
"""
Backup script to upload key development files to Supabase and Firebase Storage.
This ensures that agent outputs, logs, and progress tracking are preserved in the cloud.
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
import mimetypes

# Load environment variables
from dotenv import load_dotenv
load_dotenv("/home/ubuntu/human-ai/.env")

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")
FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

# Files to backup
BACKUP_FILES = [
    "/home/ubuntu/human-ai/master_log.json",
    "/home/ubuntu/human-ai/OUTCOME_LOG.md", 
    "/home/ubuntu/human-ai/todo.json",
    "/home/ubuntu/human-ai/ROADMAP.md",
    "/home/ubuntu/human-ai/README.md",
    "/home/ubuntu/human-ai/unified_plan.md",
    "/home/ubuntu/human-ai/improvement.log",
    "/home/ubuntu/human-ai/hermes-autonomous.log"
]

def backup_to_supabase(file_path):
    """Upload a file to Supabase Storage."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️  Supabase not configured, skipping...")
        return False
        
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return False
            
        # Determine storage bucket and path
        bucket_name = "agent-backups"
        file_name = f"{datetime.now().strftime('%Y/%m/%d')}/{file_path.name}"
        
        # Supabase Storage API endpoint
        url = f"{SUPABASE_URL}/storage/v1/object/{bucket_name}/{file_name}"
        
        # Read file content
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = 'application/octet-stream'
        
        # Headers
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": content_type
        }
        
        # Upload file
        response = requests.post(url, headers=headers, data=file_data)
        
        if response.status_code in [200, 201]:
            print(f"✅ Supabase backup successful: {file_path.name}")
            return True
        else:
            print(f"❌ Supabase backup failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"💥 Error uploading to Supabase: {e}")
        return False

def backup_to_firebase(file_path):
    """Upload a file to Firebase Storage."""
    try:
        # Try to import firebase admin
        try:
            import firebase_admin
            from firebase_admin import credentials, storage
        except ImportError:
            print("⚠️  Firebase admin not installed, installing...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "firebase-admin"])
            import firebase_admin
            from firebase_admin import credentials, storage
        
        # Initialize Firebase app if not already done
        try:
            firebase_admin.get_app()
        except ValueError:
            # App not initialized, initialize it
            cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred, {
                'storageBucket': FIREBASE_STORAGE_BUCKET
            })
        
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return False
            
        # Get bucket
        bucket = storage.bucket()
        
        # Create blob name with date structure
        blob_name = f"agent-backups/{datetime.now().strftime('%Y/%m/%d')}/{file_path.name}"
        blob = bucket.blob(blob_name)
        
        # Set content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type:
            blob.content_type = content_type
        
        # Upload file
        blob.upload_from_filename(str(file_path))
        
        # Make publicly readable (optional, for easy access)
        # blob.make_public()
        
        print(f"✅ Firebase backup successful: {file_path.name}")
        return True
        
    except Exception as e:
        print(f"💥 Error uploading to Firebase: {e}")
        return False

def main():
    """Main backup function."""
    print("☁️  STARTING CLOUD BACKUP PROCESS")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Check configuration
    print("🔧 CONFIGURATION CHECK:")
    print(f"   Supabase URL: {'✅ SET' if SUPABASE_URL else '❌ NOT SET'}")
    print(f"   Supabase Key: {'✅ SET' if SUPABASE_KEY else '❌ NOT SET'}")
    print(f"   Firebase Project: {'✅ SET' if FIREBASE_PROJECT_ID else '❌ NOT SET'}")
    print(f"   Firebase Bucket: {'✅ SET' if FIREBASE_STORAGE_BUCKET else '❌ NOT SET'}")
    print(f"   Firebase Service Account: {'✅ EXISTS' if os.path.exists(FIREBASE_SERVICE_ACCOUNT_PATH) else '❌ MISSING'}")
    print()
    
    # Backup each file
    success_count = 0
    total_files = len(BACKUP_FILES)
    
    for file_path in BACKUP_FILES:
        print(f"📁 Backing up: {os.path.basename(file_path)}")
        
        supabase_success = backup_to_supabase(file_path)
        firebase_success = backup_to_firebase(file_path)
        
        if supabase_success and firebase_success:
            print(f"   🎉 Both clouds: SUCCESS")
            success_count += 1
        elif supabase_success:
            print(f"   ☁️  Supabase only: SUCCESS")
            success_count += 0.5
        elif firebase_success:
            print(f"   🔥 Firebase only: SUCCESS")
            success_count += 0.5
        else:
            print(f"   ❌ Both clouds: FAILED")
        print()
    
    # Summary
    print("📊 BACKUP SUMMARY")
    print("=" * 50)
    print(f"   Files processed: {total_files}")
    print(f"   Successful backups: {success_count}/{total_files}")
    print(f"   Success rate: {(success_count/total_files)*100:.1f}%")
    
    if success_count == total_files:
        print("   🎉 ALL BACKUPS SUCCESSFUL")
    elif success_count > 0:
        print("   ⚠️  PARTIAL BACKUP SUCCESS")
    else:
        print("   ❌ NO BACKUPS SUCCESSFUL")
    
    return success_count == total_files

if __name__ == "__main__":
    main()
