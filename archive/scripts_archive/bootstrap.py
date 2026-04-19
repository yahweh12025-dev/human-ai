import os
import base64
from supabase import create_client
from dotenv import load_dotenv
from vault_core import decrypt_value

def bootstrap():
    print("🚀 --- Human-AI Cloud Bootstrap --- 🚀")
    
    s_url = input("Enter SUPABASE_URL: ").strip()
    s_key = input("Enter SUPABASE_SERVICE_ROLE_KEY: ").strip()
    m_key = input("Enter MASTER_KEY: ").strip()
    
    try:
        supabase = create_client(s_url, s_key)
        
        print("\n🔐 Restoring Secrets to .env...")
        secrets_res = supabase.table("vault_secrets").select("*").execute()
        
        with open(".env", "w") as env_file:
            for item in secrets_res.data:
                key = item["key"]
                enc_val = item["encrypted_value"]
                try:
                    dec_val = decrypt_value(m_key, enc_val)
                    env_file.write(f"{key}={dec_val}\n")
                    print(f"✅ Restored: {key}")
                except Exception as e:
                    print(f"⚠️ Could not decrypt {key}: {e}")
        
        print("\n💾 Restoring Memory Archives...")
        m_dir = "memory"
        os.makedirs(m_dir, exist_ok=True)
        m_res = supabase.table("memory_archives").select("*").execute()
        for item in m_res.data:
            fname = item["filename"]
            content = item["content"]
            with open(os.path.join(m_dir, fname), "w") as f:
                f.write(content)
            print(f"✅ Restored: {fname}")

        print("\n📦 Restoring Todo Database...")
        todo_db_path = "/home/ubuntu/.openclaw/workspace/skills/todo-management/todo.db"
        todo_res = supabase.table("todo_backups").select("*").eq("backup_name", "latest_todo_db").execute()
        if todo_res.data:
            db_blob = base64.b64decode(todo_res.data[0]["db_blob"])
            os.makedirs(os.path.dirname(todo_db_path), exist_ok=True)
            with open(todo_db_path, "wb") as f:
                f.write(db_blob)
            print("✅ Todo database restored.")
        else:
            print("⚠️ No todo backup found in cloud.")

        print("\n🎉 BOOTSTRAP COMPLETE!")
    except Exception as e:
        print(f"❌ Bootstrap failed: {e}")

if __name__ == "__main__":
    bootstrap()
