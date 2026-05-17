#!/usr/bin/env python3
"""
Backup script — three-tier backup strategy:
  1. Self-hosted Supabase (PostgreSQL via Docker on localhost:3000) — PRIMARY
  2. Cloud Supabase (hijtzdbzruqyikwzwnca.supabase.co) — CLOUD REDUNDANCY
  3. Firebase Firestore REST API — SECONDARY CLOUD
  4. GDrive (via rclone) — COLD BACKUP of DB dump

Self-hosted Supabase is always primary — it's local, fast, and owns the data.
Cloud Supabase and Firebase are redundant backups only.
GDrive: pg_dump of human_ai DB copied to gdrive:backups/supabase/ every 6h via cron.
"""

import os
import json
import subprocess
import requests
from datetime import datetime
from pathlib import Path
import mimetypes

from dotenv import load_dotenv
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

# Self-hosted Supabase (PostgREST on Docker)
LOCAL_SUPABASE_URL = "http://localhost:3000"   # PostgREST port
def _get_local_jwt() -> str:
    """Always read fresh JWT from .env — avoids stale token on module reload."""
    load_dotenv(_PROJECT_ROOT / ".env", override=True)
    return os.getenv("SUPABASE_LOCAL_KEY", "")
LOCAL_SUPABASE_KEY = _get_local_jwt()

# Cloud Supabase (redundant backup only)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Firebase
FIREBASE_PROJECT_ID          = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_STORAGE_BUCKET       = os.getenv("FIREBASE_STORAGE_BUCKET")
FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv(
    "FIREBASE_SERVICE_ACCOUNT_PATH",
    str(_PROJECT_ROOT / "config" / "firebase_service_account.json")
)

# Docker container name for DB operations
DB_CONTAINER = "supabase-selfhosted-db-1"
DB_NAME      = "human_ai"
DB_USER      = "postgres"

def _p(rel):
    return str(_PROJECT_ROOT / rel)

# Files to backup — uses portable project root
BACKUP_FILES = [
    _p("docs/roadmap.md"),
    _p("README.md"),
    _p("unified_tasks.json"),
    _p("docs/ROADMAP.md"),
    _p("data/logs/automode.log"),
    _p("agents/trading-agent/trades/binance/state.json"),
    _p("agents/trading-agent/trades/mt5/state.json"),
    # Legacy files (back-compat, may not exist)
    _p("master_log.json"),
    _p("OUTCOME_LOG.md"),
    _p("improvement.log"),
]

def backup_to_local_supabase(file_path):
    """
    PRIMARY backup: insert file content into self-hosted Supabase (Docker PostgREST).
    Table agent_backups must exist in human_ai database.
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return False
        with open(file_path, 'r', errors='replace') as f:
            content = f.read()

        headers = {
            "Content-Type": "application/json",
            "Prefer":       "return=minimal"
        }
        jwt = _get_local_jwt()
        if jwt:
            headers["Authorization"] = f"Bearer {jwt}"

        payload = {"path": str(file_path.name), "content": content[:50000], "agent": "backup"}
        r = requests.post(f"{LOCAL_SUPABASE_URL}/agent_backups", headers=headers, json=payload, timeout=5)
        if r.status_code in (200, 201):
            print(f"  ✅ Local Supabase: {file_path.name}")
            return True
        else:
            print(f"  ⚠️  Local Supabase {r.status_code}: {r.text[:80]}")
            return False
    except Exception as e:
        print(f"  ⚠️  Local Supabase error: {e}")
        return False


def backup_db_to_gdrive():
    """
    Dump the human_ai PostgreSQL database and copy to GDrive via rclone.
    Called on demand; scheduled every 6h via cron in scripts/backup_supabase_to_gdrive.sh.
    """
    try:
        dump_path = Path(f"/tmp/human_ai_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql.gz")
        result = subprocess.run(
            ["docker", "exec", DB_CONTAINER,
             "pg_dump", "-U", DB_USER, DB_NAME],
            capture_output=True, timeout=60
        )
        if result.returncode != 0:
            print(f"  ❌ pg_dump failed: {result.stderr.decode()[:100]}")
            return False

        # Compress
        import gzip
        with gzip.open(dump_path, 'wb') as gz:
            gz.write(result.stdout)

        # Copy to GDrive
        gdrive_path = Path.home() / "gdrive" / "backups" / "supabase"
        gdrive_path.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(dump_path, gdrive_path / dump_path.name)
        dump_path.unlink(missing_ok=True)

        # Cleanup: keep only last 30 dumps
        dumps = sorted(gdrive_path.glob("human_ai_*.sql.gz"))
        for old in dumps[:-30]:
            old.unlink()

        print(f"  ✅ DB dump → GDrive: {dump_path.name} ({gdrive_path / dump_path.name})")
        return True
    except Exception as e:
        print(f"  ⚠️  DB dump error: {e}")
        return False


def backup_to_supabase(file_path):
    """
    Insert file content into Supabase database table 'agent_backups'.
    Uses REST API — no Storage bucket needed.
    Table must exist: CREATE TABLE agent_backups (id bigserial primary key, path text, content text, ts timestamptz default now());
    Enable anon insert: ALTER TABLE agent_backups ENABLE ROW LEVEL SECURITY;
                        CREATE POLICY "allow anon insert" ON agent_backups FOR INSERT TO anon WITH CHECK (true);
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️  Supabase not configured, skipping...")
        return False
        
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return False

        with open(file_path, 'r', errors='replace') as f:
            content = f.read()

        # Use Supabase REST database API — no Storage bucket needed
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        payload = {
            "path": str(file_path.name),
            "content": content[:50000],  # max 50KB per row
            "ts": datetime.now().isoformat()
        }
        url = f"{SUPABASE_URL}/rest/v1/agent_backups"
        response = requests.post(url, headers=headers, json=payload, timeout=10)

        if response.status_code in [200, 201]:
            print(f"✅ Supabase backup successful: {file_path.name}")
            return True
        elif response.status_code == 404 and "agent_backups" in response.text:
            print(f"⚠️  Supabase table 'agent_backups' not found.")
            print(f"   Create it in Supabase dashboard SQL editor:")
            print(f"   CREATE TABLE agent_backups (id bigserial primary key, path text, content text, ts timestamptz default now());")
            print(f"   CREATE POLICY \"anon insert\" ON agent_backups FOR INSERT TO anon WITH CHECK (true);")
            return False
        else:
            print(f"❌ Supabase backup failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"💥 Error uploading to Supabase: {e}")
        return False

def backup_to_firebase(file_path):
    """
    Write file content to Firestore via REST API — no service account needed.
    Uses Firestore REST API with the project ID only.
    Firestore must have public read/write rules OR the Firebase API key must be set.
    NOTE: Service account is only needed for Firebase Admin SDK (Storage/Auth).
          For simple Firestore logging, the REST API + project ID is sufficient.
    """
    if not FIREBASE_PROJECT_ID:
        print("⚠️  FIREBASE_PROJECT_ID not set, skipping Firebase backup...")
        return False

    try:
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return False

        with open(file_path, 'r', errors='replace') as f:
            content = f.read()

        # Firestore REST API — no service account needed for public collections
        # Collection: agent_backups, document: auto-generated
        firestore_url = (
            f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}"
            f"/databases/(default)/documents/agent_backups"
        )
        payload = {
            "fields": {
                "path":    {"stringValue": str(file_path.name)},
                "content": {"stringValue": content[:50000]},
                "ts":      {"stringValue": datetime.now().isoformat()},
            }
        }
        response = requests.post(firestore_url, json=payload, timeout=10)

        if response.status_code in [200, 201]:
            print(f"✅ Firebase (Firestore) backup successful: {file_path.name}")
            return True
        else:
            print(f"❌ Firebase backup failed: {response.status_code} - {response.text[:100]}")
            if response.status_code == 403:
                print("   → Set Firestore rules to allow writes, or add FIREBASE_API_KEY to .env")
            return False

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
    sa_exists = FIREBASE_SERVICE_ACCOUNT_PATH and os.path.exists(FIREBASE_SERVICE_ACCOUNT_PATH)
    print(f"   Firebase Service Account: {'✅ EXISTS' if sa_exists else '❌ MISSING'}")
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
