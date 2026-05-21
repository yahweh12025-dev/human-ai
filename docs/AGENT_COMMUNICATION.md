# Agent Communication: A2A and MCP Design

## Overview

The human-ai swarm uses two complementary messaging patterns:

| Pattern | When to use | Coupling | Transport |
|---------|-------------|----------|-----------|
| **A2A** (Agent-to-Agent) | Direct RPC — sender needs result from specific agent | Tight | HTTP POST to MCP server → mailbox delivery + optional live HTTP |
| **MCP** (Model Context Protocol) | Tool/resource sharing, task queue, memory, signals | Loose | HTTP REST to openclaw's MCP server |

Both patterns use the same server (`core/mcp/mcp_server.py`, default port 8765) run by openclaw.

---

## A2A: Agent-to-Agent RPC

### When to use A2A

A2A is the right choice when:
- Hermes wants to dispatch a coding task **to opencode specifically** and wait for the result
- Opencode needs Pi.dev to **audit a specific file** before returning completion to Hermes
- Any agent needs a **response correlated to a specific request** (not broadcast)

A2A is **not** the right choice for broadcast signals (use the MCP signal bus) or when the requester doesn't care which agent handles the work (use the MCP task queue).

### How A2A works

1. Sender calls `POST /a2a/send` with `{sender, recipient, message}`.
2. The MCP server writes the envelope to `core/mcp/shared_memory.json` under key `a2a_inbox_{recipient}`.
3. If the recipient has registered a live HTTP endpoint, the server attempts immediate HTTP delivery.
4. The recipient polls its inbox via `GET /a2a/inbox?agent={name}` or receives the push.
5. The recipient calls `reply_a2a(original_message_id, sender, payload)` to close the loop.
6. The original sender's `send_a2a(wait_for_reply=True)` polls its own inbox for `reply_to_id` match.

### Example: Hermes → OpenCode task assignment

```python
from core.mcp.a2a_client import A2AClient

hermes = A2AClient("hermes")
response = hermes.send_a2a(
    recipient="opencode",
    message={
        "type": "task_request",
        "task": "Add RSI divergence filter to live_trading_ea.py",
        "file": "agents/trading-agent/live_trading_ea.py",
        "priority": 1,
    },
    wait_for_reply=True,
    timeout=120,
)

if response.ok:
    print("OpenCode result:", response.data)
else:
    print("A2A failed:", response.error)
```

OpenCode's reply side:

```python
opencode = A2AClient("opencode")
inbox = opencode.get_inbox()
for envelope in inbox.data.get("inbox", []):
    msg = envelope["message"]
    if msg.get("type") == "task_request":
        # ... do the work ...
        opencode.reply_a2a(
            original_message_id=envelope["id"],
            recipient=envelope["sender"],
            reply_payload={"status": "done", "diff": "...", "tests_passed": True},
        )
```

---

## MCP: Model Context Protocol (Shared Resources)

Openclaw runs the MCP server. All agents connect to it as clients using `A2AClient`.

### Core endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/tools` | GET | List available tools |
| `/tools/{name}` | POST | Invoke a tool |
| `/a2a/send` | POST | Dispatch A2A message |
| `/a2a/inbox` | GET | Read agent's A2A inbox |
| `/queue/pending` | GET | List pending tasks from `unified_tasks.json` |
| `/queue/submit` | POST | Add a task to the queue |
| `/memory/{key}` | GET/PUT | Read/write shared memory |
| `/signals/publish` | POST | Publish a swarm signal |
| `/signals/recent` | GET | Read recent signals |
| `/agents` | GET | List registered agents |
| `/agents/register` | POST | Register/heartbeat agent |
| `/health` | GET | Server health check |

### Built-in MCP tools

| Tool | Description |
|------|-------------|
| `queue_pending` | Return pending tasks, optionally filtered by agent |
| `memory_get` | Read a key from shared memory |
| `memory_set` | Write a key to shared memory |
| `signal_publish` | Publish a named signal |
| `agents_list` | List all registered agents |
| `nvidia_complete` | Call NVIDIA LLM API (key read server-side from `NVIDIA_API_KEY`) |

### Extending with custom tools

Register tools directly on the server's `ToolRegistry`:

```python
from core.mcp.mcp_server import registry

@registry.tool(
    name="backtest_summary",
    description="Run a quick FreqTrade backtest and return the P&L summary.",
    input_schema={
        "type": "object",
        "properties": {
            "strategy": {"type": "string"},
            "timerange": {"type": "string"},
        },
        "required": ["strategy"],
    },
)
def _backtest_summary(strategy: str, timerange: str = "20240101-20250101") -> dict:
    # ... implementation ...
    return {"win_rate": 0.62, "total_pnl": 1240.5}
```

### Example: OpenCode fetches its tasks via MCP

```python
from core.mcp.a2a_client import A2AClient

opencode = A2AClient("opencode")
result = opencode.queue_pending(agent="opencode")
for task in result.data.get("result", []):
    print(task["id"], task["task"][:80])
```

### Example: Pi.dev publishes a security alert signal

```python
pidev = A2AClient("pi.dev")
pidev.signal_publish("security_alert", {
    "severity": "HIGH",
    "file": "agents/trading-agent/live_trading_ea.py",
    "finding": "Hardcoded credential on line 42",
})
```

---

## Architecture Rationale

### Why two patterns?

**A2A is synchronous-style RPC.** When Hermes sends a code task to OpenCode, it needs the specific result back before it can continue planning. Routing through a generic queue would lose the correlation between request and response. A2A solves this with per-agent inboxes and `reply_to_id` correlation.

**MCP is asynchronous resource sharing.** The task queue, shared memory, and signal bus are infrastructure that no single agent "owns." Centralizing them in the MCP server (run by openclaw, the gateway) gives every agent a single authority for discovering tools and state without creating a mesh of direct connections.

### Why openclaw hosts the MCP server?

Openclaw's existing role is gateway coordinator and queue manager. The MCP server is a natural extension: it wraps the unified task queue, exposes shared memory, and provides the signal bus — all things openclaw already managed informally. This avoids a separate infrastructure process.

### Why not WebSockets or message queues (RabbitMQ/Kafka)?

The swarm currently runs as OS processes on a single host (or Docker containers on a single node). HTTP/JSON is:
- Zero additional dependencies (stdlib `http.server` + `urllib.request`)
- Easy to inspect with `curl` during debugging
- Trivially replaceable: swap the transport in `A2AClient._request` without touching agent logic

When the swarm grows to multi-node, replace `A2AClient._request` with an async WebSocket or NATS client — the API surface stays identical.

---

## File Layout

```
core/mcp/
    __init__.py          — public exports: MCPServer, A2AClient, A2AMessage, A2AResponse
    mcp_server.py        — openclaw's HTTP/JSON MCP gateway (stdlib only)
    a2a_client.py        — client library for all agents
    shared_memory.json   — runtime shared memory store (auto-created)
    agent_registry.json  — registered agents + endpoints (auto-created)
    signals.json         — signal bus ring buffer (auto-created)

agents/roles/
    openclaw.json        — Openclaw role + MCP server config
    hermes.json          — Hermes role + A2A patterns
    opencode.json        — OpenCode role + A2A patterns
    pidev.json           — Pi.dev role + A2A patterns
    researcher.json      — Researcher role + A2A patterns
```

---

## Starting the MCP Server

Openclaw should start the server on boot:

```bash
# Foreground
python -m core.mcp.mcp_server

# Background (as openclaw subprocess)
python -m core.mcp.mcp_server --host 0.0.0.0 --port 8765 &

# Health check
curl http://localhost:8765/health
```

Agents should call `A2AClient.register()` on startup (done automatically by default):

```python
client = A2AClient("hermes")   # registers automatically
client.health()                # verify server is reachable
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SERVER_URL` | `http://localhost:8765` | Override server URL for all clients |
| `NVIDIA_API_KEY` | — | NVIDIA NIM API key (server-side, never sent over wire) |
| `NVIDIA_MODEL` | `nvidia/nemotron-3-super-120b-a12b:free` | Model identifier |
| `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1` | NIM API base URL |
