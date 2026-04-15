import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Missing Supabase credentials.")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# SQL to create the vault table
# We use a simple key-value store with encrypted values
sql = \"\"\"
CREATE TABLE IF NOT EXISTS vault_secrets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    encrypted_value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable Row Level Security (RLS)
ALTER TABLE vault_secrets ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows the service role to do everything
CREATE POLICY \"Service Role Full Access\" 
ON vault_secrets 
FOR ALL 
TO service_role 
USING (true) 
WITH CHECK (true);
\"\"\"

try:
    # Using the rpc call to execute raw SQL via a helper function 
    # (Since Supabase Python client doesn't support raw SQL directly without a custom function)
    # We will use the 'postgres' extension or a custom function if available.
    # For this setup, we'll assume the user has a function 'execute_sql' or we can use a temporary method.
    
    # Alternative: Since I'm the agent, I'll use a direct SQL executor if I have the key.
    # But for safety and cleanliness, I will attempt to use a helper.
    
    # Since I cannot run raw SQL easily via the JS-like SDK, I will use the 
    # 'supabase.table().upsert()' logic later, but first I'll create the table.
    
    # I will output the SQL for the user or try to use a custom endpoint if configured.
    print(\"SQL for Vault Setup:\")
    print(sql)
except Exception as e:
    print(f\"Error: {e}\")
