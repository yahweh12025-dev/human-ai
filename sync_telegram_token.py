import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Use service role for write access
TOKEN = "8306402529:AAHs_WPPZv1wsxDEIgU0P0Twc6PRm_8A_xA"

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Missing Supabase credentials")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    # Upsert the token into a secrets table
    # Assuming a table 'system_secrets' with columns 'key' and 'value'
    supabase.table('vault_secrets').upsert({'key': 'TELEGRAM_BOT_TOKEN', 'value': TOKEN}).execute()
    print("✅ Telegram Bot Token synced to Supabase.")
except Exception as e:
    print(f"❌ Supabase sync failed: {e}")
