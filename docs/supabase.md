# Human-AI Supabase Reference
## Overview
All persistent structured data for the `human-ai` swarm lives in the **Hermes-managed**
self-hosted Supabase stack running on `127.0.0.1`.

- Database: `human_ai`
- PostgREST: `http://localhost:3001` (RLS disabled — `anon` can read; writes via `psql`)
- Adminer: `http://localhost:3100`
- MCP binary: `gclone/selfhosted-supabase-mcp/dist/index.js`

## Credentials
Source of truth: `credentials/supabase.env`
Synced to: `.env` (for `load_dotenv()` consumers)

Key variables:
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_ANON_KEY` — Public-facing API key (1-yr expiry, regenerate manually)
- `SUPABASE_SERVICE_ROLE_KEY` — Server-side JWT (regenerated via `bun` + `jose`)
- `DATABASE_URL` — `postgresql://postgres:<password>@127.0.0.1:5432/human_ai`
- `SUPABASE_JWT_SECRET` — `super-secret-jwt-key-for-human-ai-swarm`

Rotate secrets:
```bash
cd /home/yahweh1_2025
bun -e '
const tj=require("jose");
const secret=new TextEncoder().encode("super-secret-jwt-key-for-human-ai-swarm");
const now=Math.floor(Date.now()/1000);
const token=await new tj.SignJWT({
  aud:"authenticated",
  role:"service_role"
}).setIssuer("http://localhost:8000/auth/v1")
  .setSubject("anon")
  .setIssuedAt(now)
  .setExpirationTime(now+365*24*3600*1000)
  .setProtectedHeader({alg:"HS256"})
  .sign(secret);
console.log(token);
'
```
Then update both `credentials/supabase.env` and `.env` with the new token.

## Schema (public schema)

### trades
Executed trades from MT5 (and other agents). Primary table.

| Column | Type | Notes |
|--------|------|-------|
| id | integer | PK, serial |
| agent | varchar(50) | `mt5_ea`, `hermes`, etc. |
| symbol | varchar(20) | e.g. `BTCUSD` |
| side | varchar(10) | `BUY` / `SELL` |
| amount | numeric | Position size |
| price | numeric | Execution price |
| pnl | numeric | Realized P&L (nullable until trade closes) |
| data | jsonb | `{deal_id, source, logged_at, log_file, ...}` |
| timestamp | timestamptz | Default `now()` |

### agent_events
Generic event log for agents.

| Column | Type |
|--------|------|
| id | integer PK |
| agent | varchar(50) |
| event_type | varchar(100) |
| data | jsonb |
| timestamp | timestamptz |

### model_scores
AI model prediction scores / confidence per trade signal.

| Column | Type |
|--------|------|
| id | integer PK |
| agent | varchar(50) |
| model_name | varchar(100) |
| symbol | varchar(20) |
| score | numeric |
| prediction | jsonb |
| timestamp | timestamptz |

### trade_embeddings
Free-text search index for trade descriptions (GIN on `text` + `metadata` jsonb).
pgvector was deferred (Alpine/PG15 incompatibility).

| Column | Type |
|--------|------|
| id | integer PK |
| trade_id | integer FK → trades |
| text | text | Executable trade description / narrative |
| metadata | jsonb | Tags, agent, timestamp snapshot |
| embedding | vector(1536) | **PLACEHOLDER** — pgvector not yet enabled |

### secrets_backup
Redundant backup layer for credential metadata (NOT secret values).

| Column | Type |
|--------|------|
| id | integer PK |
| service | varchar(100) | e.g. `supabase`, `mt5_agent` |
| key_name | varchar(100) | e.g. `SUPABASE_SERVICE_ROLE_KEY` |
| metadata | jsonb | Rotated dates, expiry, contact |
| timestamp | timestamptz |

### balance_agent_logs
Hermes/Balance agent equity/balance snapshots.

| Column | Type |
|--------|------|
| id | integer PK |
| agent | varchar(100) |
| balance | numeric |
| currency | varchar(10) | Default `USD` |
| equity | numeric |
| margin | numeric |
| free_margin | numeric |
| data | jsonb | Extra context |
| timestamp | timestamptz |

## Writer Conventions

### Writes: use `psql`
PostgREST role mapping on the Hermes stack returns 404 on POST for anon/service_role
despite the table being visible in the API schema. The robust path is `docker exec ... psql`.

Canonical write helper pattern (Python):
```python
import subprocess, json

def _sanitize(s: str) -> str:
    return s.replace("'", "''")

def insert_trade(agent, symbol, side, amount, price, data):
    sql = (
        "INSERT INTO public.trades (agent,symbol,side,amount,price,data,timestamp) "
        f"VALUES ('{_sanitize(agent)}','{_sanitize(symbol)}','{_sanitize(side)}',"
        f"{amount},{price},'{_sanitize(json.dumps(data))}'::jsonb,now());"
    )
    subprocess.run(
        ["docker","exec","supabase-selfhosted-db-1",
         "psql","-U","postgres","-d","human_ai","-c",sql],
        check=True, capture_output=True, text=True, timeout=30,
    )
```

### Reads: use PostgREST
```bash
curl -s "http://localhost:3001/trades?agent=eq.mt5_ea&limit=10" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY"
```

### Idempotency
- MT5 trade log: dedupe by `(symbol, side, price, deal_id, logged_at)` per run
- Balance snapshots: dedupe by `(agent, timestamp)` if called per-minute
- Never `DELETE FROM ...` without an explicit `WHERE` clause

## MCP
`gclone/selfhosted-supabase-mcp` exposes `execute_sql` for Pg-style queries.
Useful for ad-hoc inspection; avoid for bulk inserts (parameterized `$1` style not
supported by the Hermes-managed `public.execute_sql`).

```python
# Example: count rows this week
import requests, json
key = open('credentials/supabase.env').read().split('SUPABASE_SERVICE_ROLE_KEY=')[1].split('\n')[0]
headers = {'apikey': key, 'Authorization': f'Bearer {key}'}
r = requests.post(
    'http://localhost:3001/rpc/execute_sql',
    headers=headers, json={
        'query': 'SELECT count(*) FROM public.trades WHERE timestamp > now() - interval 7 days;'
    }
)
print(r.json())
```

## Rclone Sync
GDrive backup path (same remote used by Obsidian vault):
```bash
rclone sync /home/yahweh1_2025/human-ai gdrive:backups/human-ai --progress
rclone sync /home/yahweh1_2025/mt5_node gdrive:backups/mt5_node --progress
```
