#!/usr/bin/env python3
"""
core/mcp/mcp_server.py — MCP Gateway Server for the human-ai swarm.

Openclaw runs this server as the central Model Context Protocol gateway.
All agents connect here for:
  - Tool discovery and invocation (GET /tools, POST /tools/{tool_name})
  - A2A message dispatch      (POST /a2a/send)
  - Unified task queue access  (GET /queue/pending, POST /queue/submit)
  - Shared memory store        (GET /memory/{key}, PUT /memory/{key})
  - Signal publishing          (POST /signals/publish, GET /signals/subscribe)
  - Agent registry             (GET /agents, POST /agents/register)

LLM calls (e.g. tool summarization) use NVIDIA_API_KEY from the environment.
Never hardcode keys.

Usage:
    python -m core.mcp.mcp_server              # default: 0.0.0.0:8765
    python -m core.mcp.mcp_server --port 9000
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

# ── Paths ─────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TASKS_FILE   = _PROJECT_ROOT / "unified_tasks.json"
_MEMORY_FILE  = _PROJECT_ROOT / "core" / "mcp" / "shared_memory.json"
_AGENTS_FILE  = _PROJECT_ROOT / "core" / "mcp" / "agent_registry.json"
_SIGNALS_FILE = _PROJECT_ROOT / "core" / "mcp" / "signals.json"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("mcp_server")


# ── File helpers (thread-safe with a global lock) ─────────────────────────────
_fs_lock = threading.Lock()


def _read_json(path: Path, default: Any = None) -> Any:
    with _fs_lock:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return default


def _write_json(path: Path, data: Any) -> None:
    with _fs_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))


def _init_storage() -> None:
    """Ensure all storage files exist with sane defaults."""
    if not _MEMORY_FILE.exists():
        _write_json(_MEMORY_FILE, {"store": {}, "updated_at": datetime.now().isoformat()})
    if not _AGENTS_FILE.exists():
        _write_json(_AGENTS_FILE, {
            "agents": {},
            "updated_at": datetime.now().isoformat(),
        })
    if not _SIGNALS_FILE.exists():
        _write_json(_SIGNALS_FILE, {"signals": [], "updated_at": datetime.now().isoformat()})


# ── Tool registry ──────────────────────────────────────────────────────────────

class ToolRegistry:
    """
    Holds callable tools that agents can discover (GET /tools) and invoke
    (POST /tools/{name}).

    Register custom tools with @registry.tool(name, description, schema).
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Dict[str, Any]] = {}

    def tool(
        self,
        name: str,
        description: str,
        input_schema: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """Decorator — registers a function as an MCP tool."""
        def decorator(fn: Callable) -> Callable:
            self._tools[name] = {
                "name": name,
                "description": description,
                "input_schema": input_schema or {"type": "object", "properties": {}},
                "handler": fn,
            }
            return fn
        return decorator

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {k: v for k, v in t.items() if k != "handler"}
            for t in self._tools.values()
        ]

    def call(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self._tools:
            return {"error": f"Tool '{name}' not found", "available": list(self._tools)}
        try:
            result = self._tools[name]["handler"](**params)
            return {"result": result, "tool": name, "ts": datetime.now().isoformat()}
        except TypeError as exc:
            return {"error": f"Bad parameters for tool '{name}': {exc}"}
        except Exception as exc:  # noqa: BLE001
            logger.exception("Tool '%s' raised: %s", name, exc)
            return {"error": str(exc), "tool": name}


# ── Global registry (tools registered at module level) ────────────────────────
registry = ToolRegistry()


# Built-in tools ---------------------------------------------------------------

@registry.tool(
    name="queue_pending",
    description="Return all pending tasks from unified_tasks.json.",
    input_schema={"type": "object", "properties": {"agent": {"type": "string"}}},
)
def _tool_queue_pending(agent: Optional[str] = None) -> List[Dict]:
    data = _read_json(_TASKS_FILE, {"task_queue": {"pending": []}})
    pending = data.get("task_queue", {}).get("pending", [])
    if agent:
        pending = [t for t in pending if t.get("agent", "").lower() == agent.lower()]
    return pending


@registry.tool(
    name="memory_get",
    description="Read a value from the shared swarm memory store.",
    input_schema={
        "type": "object",
        "properties": {"key": {"type": "string"}},
        "required": ["key"],
    },
)
def _tool_memory_get(key: str) -> Any:
    store = _read_json(_MEMORY_FILE, {"store": {}})
    return store.get("store", {}).get(key)


@registry.tool(
    name="memory_set",
    description="Write a value to the shared swarm memory store.",
    input_schema={
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "value": {},
        },
        "required": ["key", "value"],
    },
)
def _tool_memory_set(key: str, value: Any) -> bool:
    store = _read_json(_MEMORY_FILE, {"store": {}})
    store.setdefault("store", {})[key] = value
    store["updated_at"] = datetime.now().isoformat()
    _write_json(_MEMORY_FILE, store)
    return True


@registry.tool(
    name="signal_publish",
    description="Publish a named signal with a payload to all subscribers.",
    input_schema={
        "type": "object",
        "properties": {
            "signal": {"type": "string"},
            "payload": {},
            "source_agent": {"type": "string"},
        },
        "required": ["signal", "payload"],
    },
)
def _tool_signal_publish(signal: str, payload: Any, source_agent: str = "unknown") -> str:
    store = _read_json(_SIGNALS_FILE, {"signals": []})
    entry = {
        "id": str(uuid.uuid4()),
        "signal": signal,
        "payload": payload,
        "source_agent": source_agent,
        "published_at": datetime.now().isoformat(),
        "consumed_by": [],
    }
    store.setdefault("signals", []).append(entry)
    # Keep last 200 signals
    store["signals"] = store["signals"][-200:]
    store["updated_at"] = datetime.now().isoformat()
    _write_json(_SIGNALS_FILE, store)
    return entry["id"]


@registry.tool(
    name="agents_list",
    description="List all registered agents and their last heartbeat.",
    input_schema={"type": "object", "properties": {}},
)
def _tool_agents_list() -> List[Dict]:
    data = _read_json(_AGENTS_FILE, {"agents": {}})
    return list(data.get("agents", {}).values())


@registry.tool(
    name="nvidia_complete",
    description="Call NVIDIA's LLM API (model set via NVIDIA_MODEL env var) with a prompt. "
                "Uses NVIDIA_API_KEY from environment — key is never logged or returned.",
    input_schema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "system": {"type": "string"},
            "max_tokens": {"type": "integer"},
        },
        "required": ["prompt"],
    },
)
def _tool_nvidia_complete(
    prompt: str,
    system: str = "You are a helpful swarm agent assistant.",
    max_tokens: int = 512,
) -> str:
    """Invoke NVIDIA NIM / OpenRouter compatible endpoint using env keys."""
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    model   = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
    base_url = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

    if not api_key:
        return "[NVIDIA_API_KEY not set — LLM unavailable]"

    try:
        import urllib.request
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
        }).encode()
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001
        logger.warning("nvidia_complete error: %s", exc)
        return f"[LLM error: {exc}]"


# ── A2A dispatch ───────────────────────────────────────────────────────────────

class A2ADispatcher:
    """
    Routes direct agent-to-agent messages.

    Messages are stored in shared_memory under key 'a2a_inbox_{recipient}'
    and optionally forwarded to a live HTTP endpoint if the recipient has
    registered one in the agent registry.
    """

    def dispatch(self, sender: str, recipient: str, message: Dict[str, Any]) -> str:
        msg_id = str(uuid.uuid4())
        envelope = {
            "id": msg_id,
            "sender": sender,
            "recipient": recipient,
            "message": message,
            "sent_at": datetime.now().isoformat(),
            "delivered": False,
        }

        # Persist to recipient's inbox in shared memory
        inbox_key = f"a2a_inbox_{recipient.lower()}"
        store = _read_json(_MEMORY_FILE, {"store": {}})
        inbox = store.setdefault("store", {}).setdefault(inbox_key, [])
        inbox.append(envelope)
        # Keep last 100 per inbox
        store["store"][inbox_key] = inbox[-100:]
        store["updated_at"] = datetime.now().isoformat()
        _write_json(_MEMORY_FILE, store)

        # Try live HTTP delivery if agent has a registered endpoint
        self._try_live_delivery(envelope)

        logger.info("A2A %s → %s  [%s]", sender, recipient, msg_id[:8])
        return msg_id

    def _try_live_delivery(self, envelope: Dict[str, Any]) -> None:
        recipient = envelope["recipient"]
        agents = _read_json(_AGENTS_FILE, {"agents": {}}).get("agents", {})
        agent_info = agents.get(recipient, {})
        endpoint = agent_info.get("endpoint", "")

        if not endpoint.startswith("http"):
            return  # No live endpoint registered

        try:
            import urllib.request
            payload = json.dumps({"type": "a2a_delivery", "envelope": envelope}).encode()
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
            logger.debug("Live A2A delivered to %s @ %s", recipient, endpoint)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Live A2A delivery failed for %s: %s", recipient, exc)

    def get_inbox(self, recipient: str) -> List[Dict]:
        inbox_key = f"a2a_inbox_{recipient.lower()}"
        store = _read_json(_MEMORY_FILE, {"store": {}})
        return store.get("store", {}).get(inbox_key, [])


_a2a = A2ADispatcher()


# ── HTTP request handler ───────────────────────────────────────────────────────

class MCPRequestHandler(BaseHTTPRequestHandler):
    """
    Routes MCP and A2A HTTP endpoints.

    Routes
    ------
    GET  /tools                     List available tools.
    POST /tools/{tool_name}         Invoke a tool with JSON body params.
    POST /a2a/send                  Dispatch an A2A message.
    GET  /a2a/inbox?agent=<name>    Read A2A inbox for an agent.
    GET  /queue/pending             List pending tasks (optional ?agent=).
    POST /queue/submit              Submit a new task to unified_tasks.json.
    GET  /memory/{key}              Read from shared memory.
    PUT  /memory/{key}              Write to shared memory.
    POST /signals/publish           Publish a signal.
    GET  /signals/recent            Get recent signals.
    GET  /agents                    List registered agents.
    POST /agents/register           Register or update an agent.
    GET  /health                    Server health check.
    """

    server_version = "MCPServer/1.0"
    log_format = "[%(asctime)s] %(address)s %(method)s %(path)s %(code)d"

    def log_message(self, fmt: str, *args) -> None:  # silence default logging
        pass

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _parse_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _send_json(self, data: Any, code: int = 200) -> None:
        body = json.dumps(data, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message: str, code: int = 400) -> None:
        self._send_json({"error": message, "code": code}, code)

    def _parsed_url(self):
        return urlparse(self.path)

    # ── GET ────────────────────────────────────────────────────────────────────

    def do_GET(self) -> None:  # noqa: N802
        parsed = self._parsed_url()
        path   = parsed.path.rstrip("/")
        qs     = parse_qs(parsed.query)

        logger.info("GET %s", path)

        # GET /health
        if path == "/health":
            self._send_json({
                "status": "ok",
                "server": "MCPServer/1.0",
                "ts": datetime.now().isoformat(),
                "tools": len(registry._tools),
            })

        # GET /tools
        elif path == "/tools":
            self._send_json({"tools": registry.list_tools()})

        # GET /queue/pending
        elif path == "/queue/pending":
            agent = qs.get("agent", [None])[0]
            result = registry.call("queue_pending", {"agent": agent} if agent else {})
            self._send_json(result)

        # GET /memory/{key}
        elif path.startswith("/memory/"):
            key = path[len("/memory/"):]
            result = registry.call("memory_get", {"key": key})
            self._send_json(result)

        # GET /a2a/inbox
        elif path == "/a2a/inbox":
            agent = qs.get("agent", [None])[0]
            if not agent:
                self._send_error("?agent= parameter required")
                return
            self._send_json({"inbox": _a2a.get_inbox(agent)})

        # GET /signals/recent
        elif path == "/signals/recent":
            limit = int(qs.get("limit", [20])[0])
            store = _read_json(_SIGNALS_FILE, {"signals": []})
            signals = store.get("signals", [])[-limit:]
            self._send_json({"signals": signals})

        # GET /agents
        elif path == "/agents":
            result = registry.call("agents_list", {})
            self._send_json(result)

        else:
            self._send_error(f"Unknown route: {path}", 404)

    # ── POST ───────────────────────────────────────────────────────────────────

    def do_POST(self) -> None:  # noqa: N802
        parsed = self._parsed_url()
        path   = parsed.path.rstrip("/")
        body   = self._parse_body()

        logger.info("POST %s", path)

        # POST /tools/{tool_name}
        if path.startswith("/tools/"):
            tool_name = path[len("/tools/"):]
            result = registry.call(tool_name, body)
            code = 400 if "error" in result else 200
            self._send_json(result, code)

        # POST /a2a/send
        elif path == "/a2a/send":
            sender    = body.get("sender")
            recipient = body.get("recipient")
            message   = body.get("message")
            if not all([sender, recipient, message]):
                self._send_error("sender, recipient, and message are required")
                return
            msg_id = _a2a.dispatch(sender, recipient, message)
            self._send_json({"id": msg_id, "status": "dispatched"})

        # POST /queue/submit
        elif path == "/queue/submit":
            task = body.get("task")
            if not task or not isinstance(task, dict):
                self._send_error("'task' object required in body")
                return
            task.setdefault("id", f"MCP-{uuid.uuid4().hex[:8].upper()}")
            task.setdefault("created_at", datetime.now().isoformat())
            task.setdefault("status", "pending")
            data = _read_json(_TASKS_FILE, {"task_queue": {"pending": []}})
            data.setdefault("task_queue", {}).setdefault("pending", []).append(task)
            _write_json(_TASKS_FILE, data)
            self._send_json({"id": task["id"], "status": "queued"})

        # POST /signals/publish
        elif path == "/signals/publish":
            signal  = body.get("signal")
            payload = body.get("payload")
            source  = body.get("source_agent", "unknown")
            if not signal or payload is None:
                self._send_error("signal and payload are required")
                return
            sig_id = registry.call("signal_publish", {
                "signal": signal, "payload": payload, "source_agent": source
            })
            self._send_json({"id": sig_id, "status": "published"})

        # POST /agents/register
        elif path == "/agents/register":
            agent_id = body.get("agent_id")
            if not agent_id:
                self._send_error("agent_id required")
                return
            data = _read_json(_AGENTS_FILE, {"agents": {}})
            data["agents"][agent_id] = {
                "agent_id": agent_id,
                "capabilities": body.get("capabilities", []),
                "endpoint": body.get("endpoint", ""),
                "registered_at": body.get(
                    "registered_at",
                    data["agents"].get(agent_id, {}).get("registered_at",
                                                          datetime.now().isoformat())
                ),
                "last_heartbeat": datetime.now().isoformat(),
                "status": "active",
            }
            data["updated_at"] = datetime.now().isoformat()
            _write_json(_AGENTS_FILE, data)
            self._send_json({"status": "registered", "agent_id": agent_id})

        # PUT /memory/{key} — also reachable via POST for proxy-friendly clients
        elif path.startswith("/memory/"):
            key   = path[len("/memory/"):]
            value = body.get("value")
            if value is None:
                self._send_error("'value' required in body")
                return
            result = registry.call("memory_set", {"key": key, "value": value})
            self._send_json(result)

        else:
            self._send_error(f"Unknown route: {path}", 404)

    # PUT /memory/{key}
    do_PUT = do_POST  # type: ignore[assignment]


# ── Server class ───────────────────────────────────────────────────────────────

class MCPServer:
    """
    Openclaw's MCP gateway.  Start with MCPServer().serve().

    Parameters
    ----------
    host : str
        Bind address (default "0.0.0.0").
    port : int
        Listening port (default 8765).
    """

    DEFAULT_HOST = "0.0.0.0"
    DEFAULT_PORT = 8765

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self._server: Optional[HTTPServer] = None
        _init_storage()

        # Register core agents on startup (if not already present)
        self._bootstrap_agents()

    def _bootstrap_agents(self) -> None:
        data = _read_json(_AGENTS_FILE, {"agents": {}})
        defaults = {
            "openclaw":  {"capabilities": ["gateway", "task_queue", "coordination"], "endpoint": ""},
            "hermes":    {"capabilities": ["architect", "strategy", "orchestration"], "endpoint": ""},
            "opencode":  {"capabilities": ["coding", "refactoring", "implementation"], "endpoint": ""},
            "pi.dev":    {"capabilities": ["security", "audit", "verification"], "endpoint": ""},
            "researcher": {"capabilities": ["research", "deepseek", "analysis"], "endpoint": ""},
        }
        changed = False
        for agent_id, info in defaults.items():
            if agent_id not in data["agents"]:
                data["agents"][agent_id] = {
                    "agent_id": agent_id,
                    "capabilities": info["capabilities"],
                    "endpoint": info["endpoint"],
                    "registered_at": datetime.now().isoformat(),
                    "last_heartbeat": datetime.now().isoformat(),
                    "status": "active",
                }
                changed = True
        if changed:
            data["updated_at"] = datetime.now().isoformat()
            _write_json(_AGENTS_FILE, data)

    def serve(self, background: bool = False) -> None:
        """Start the HTTP server."""
        self._server = HTTPServer((self.host, self.port), MCPRequestHandler)
        addr = f"http://{self.host}:{self.port}"
        logger.info("MCPServer listening on %s", addr)
        logger.info("  GET  %s/tools", addr)
        logger.info("  POST %s/tools/<name>", addr)
        logger.info("  POST %s/a2a/send", addr)
        logger.info("  GET  %s/queue/pending", addr)
        logger.info("  GET  %s/agents", addr)

        if background:
            t = threading.Thread(target=self._server.serve_forever, daemon=True)
            t.start()
        else:
            try:
                self._server.serve_forever()
            except KeyboardInterrupt:
                logger.info("MCPServer shutting down...")
            finally:
                self._server.server_close()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            logger.info("MCPServer stopped.")


# ── __main__ entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MCP Gateway Server for the human-ai swarm")
    parser.add_argument("--host", default=MCPServer.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=MCPServer.DEFAULT_PORT)
    args = parser.parse_args()

    MCPServer(host=args.host, port=args.port).serve()
