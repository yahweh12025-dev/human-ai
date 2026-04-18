import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv('/home/ubuntu/human-ai/.env')
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

try:
    # This is a trick to get the columns of a table
    res = supabase.table('research_findings').select('*').limit(1).execute()
    if res.data:
        print("Columns found:", res.data[0].keys())
    else:
        print("Table is empty, but exists.")
except Exception as e:
    print(f"Error: {e}")
