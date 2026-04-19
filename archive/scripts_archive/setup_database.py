#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Use environment variables or interactive input
S_URL = os.getenv("SUPABASE_URL")
S_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def run_sql(url, key, sql):
    # Supabase allows executing SQL via the 'sql' endpoint for service roles
    endpoint = f"{url}/rest/v1/rpc/execute_sql" 
    # Note: This requires a custom function 'execute_sql' to be present in the DB.
    # Since we want a ZERO-CONFIG setup, we will use the PostgREST API 
    # to check for table existence first.
    pass

def setup_db():
    print("🛠️ Initializing Cloud Database Schema...")
    
    if not S_URL or not S_KEY:
        S_URL = input("Enter SUPABASE_URL: ").strip()
        S_KEY = input("Enter SUPABASE_SERVICE_ROLE_KEY: ").strip()

    # Instead of raw SQL via API (which is restricted), we'll use the 
    # standard way: providing a single, comprehensive SQL script that the 
    # user runs once, OR we use a custom edge function.
    
    # To truly automate this, I will create a 'schema.sql' file in the repo.
    # The bootstrap.py script will then alert the user to run it if tables are missing.
    
    sql_content = \"\"\"
    -- VAULT TABLE
    CREATE TABLE IF NOT EXISTS vault_secrets (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        key TEXT UNIQUE NOT NULL,
        encrypted_value TEXT NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT now(),
        created_at TIMESTAMPTZ DEFAULT now()
    );
    ALTER TABLE vault_secrets ENABLE ROW LEVEL SECURITY;
    CREATE POLICY \"Service Role Full Access\" ON vault_secrets FOR ALL TO service_role USING (true) WITH CHECK (true);

    -- MEMORY TABLE
    CREATE TABLE IF NOT EXISTS memory_archives (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        filename TEXT NOT NULL,
        content TEXT NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT now()
    );
    ALTER TABLE memory_archives ENABLE ROW LEVEL SECURITY;
    CREATE POLICY \"Service Role Full Access\" ON memory_archives FOR ALL TO service_role USING (true) WITH CHECK (true);

    -- TODO TABLE
    CREATE TABLE IF NOT EXISTS todo_backups (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        backup_name TEXT NOT NULL,
        db_blob TEXT NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT now()
    );
    ALTER TABLE todo_backups ENABLE ROW LEVEL SECURITY;
    CREATE POLICY \"Service Role Full Access\" ON todo_backups FOR ALL TO service_role USING (true) WITH CHECK (true);
    \"\"\"
    
    with open("schema.sql", "w") as f:
        f.write(sql_content)
    
    print("✅ schema.sql created. Please run this in your Supabase SQL Editor once.")
    print("Once this is done, the system is fully automated.")

if __name__ == "__main__":
    setup_db()
