import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
try:
    res = supabase.table('research_findings').select('*').limit(5).execute()
    print(f"Findings: {res.data}")
except Exception as e:
    print(f"Error: {e}")
