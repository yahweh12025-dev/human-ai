import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    # Inspect the columns of vault_secrets
    res = supabase.table('vault_secrets').select('*').limit(1).execute()
    if res.data and len(res.data) > 0:
        print(f"Columns in vault_secrets: {res.data[0].keys()}")
    else:
        print("Table vault_secrets is empty, cannot infer columns from data.")
except Exception as e:
    print(f"Error: {e}")
