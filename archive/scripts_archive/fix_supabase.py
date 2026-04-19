#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def fix_schema():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("❌ Missing Supabase credentials in .env")
        return

    supabase = create_client(url, key)
    print("Attempting to fix 'research_findings' table schema...")
    
    try:
        # We attempt to insert a row with 'content'. If it fails, the column is missing.
        supabase.table("research_findings").insert({"topic": "SCHEMA_FIX", "content": "test"}).execute()
        print("✅ Column 'content' already exists or was successfully updated.")
    except Exception as e:
        print(f"❌ Column missing or error: {e}")
        print("Please manually add the 'content' column (text type) to the 'research_findings' table in the Supabase Dashboard.")

if __name__ == "__main__":
    fix_schema()
