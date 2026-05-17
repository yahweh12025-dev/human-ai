#!/usr/bin/env python3
"""
core/mcp/a2a_client.py — A2A (Agent-to-Agent) + MCP client library.

Every agent in the swarm can import this to:
  1. Send direct RPC messages to other agents      (A2A)
  2. Discover and call tools on the MCP server     (MCP)
  3. Read/write shared memory                      (MCP)
  4. Publish / subscribe to signals                (MCP)
  5. Submit tasks to the unified queue             (MCP)

Usage
-----
    from core.mcp.a2a_client import A2AClient

    client = A2AClient(agent_id="hermes")
    client.register()                          # announce to MCP server

    # Send task directly to opencode (A2A — tight coupling, awaitable)
    response = client.send_a2a(
        recipient="opencode",
        message={"type": "task_request", "task": "refactor X", "priority": 1},
        wait_for_reply=True,
        timeout=30,
    )

    # Call a shared MCP tool
    pending = client.call_tool("queue_pending", {"agent": "hermes"})

    # Write to shared memory
    client.memory_set("hermes_state", {"phase": "planning"})

    # Publish a signal
    client.signal_publish("strategy_updated", {"strategy": "breakout_v2"})

Environment
-----------
    MCP_SERVER_URL  — override server base URL (default http://localhost:8765)
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("a2a_client")

_DEFAULT_MCP_URL = "http://localhost:8765"


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class A2AMessage:
    """A structured A2A message envelope."""
    sender: str
    recipient: str
    message: Dict[str, Any]
    reply_to_id: Optional[str] = None


@dataclass
class A2AResponse:
    """Response/result from an A2A or tool call."""
    ok: bool
    data: Any = None
    error: Optional[str] = None
    message_id: Optional[str] = None
    latency_ms: float = 0.0

    @classmethod
    def success(cls, data: Any, message_id: Optional[str] = None,
                latency_ms: float = 0.0) -> "A2AResponse":
        return cls(ok=True, data=data, message_id=message_id, latency_ms=latency_ms)

    @classmethod
    def failure(cls, error: str, latency_ms: float = 0.0) -> "A2AResponse":
        return cls(ok=False, error=error, latency_ms=latency_ms)


# ── Client ─────────────────────────────────────────────────────────────────────

class A2AClient:
    """
    Unified MCP + A2A client for swarm agents.

    Parameters
    ----------
    agent_id : str
        Identity of the calling agent (e.g. "hermes", "opencode").
    mcp_url : str, optional
        Base URL of the MCP server.  Falls back to env MCP_SERVER_URL,
        then to "http://localhost:8765".
    timeout : int
        Default HTTP timeout in seconds.
    auto_register : bool
        If True (default), register this agent on construction.
    """

    def __init__(
        self,
        agent_id: str,
        mcp_url: Optional[str] = None,
        timeout: int = 15,
        auto_register: bool = True,
    ) -> None:
        self.agent_id = agent_id
        self.mcp_url  = (
            mcp_url
            or os.environ.get("MCP_SERVER_URL", _DEFAULT_MCP_URL)
        ).rstrip("/")
        self.timeout = timeout
        self._logger = logging.getLogger(f"a2a_client.{agent_id}")

        if auto_register:
            try:
                self.register()
            except Exception:
                pass  # Server may not be running yet; agent can retry later

    # ── HTTP plumbing ──────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict] = None,
        timeout: Optional[int] = None,
    ) -> A2AResponse:
        url = f"{self.mcp_url}{path}"
        t0  = time.monotonic()
        try:
            data    = json.dumps(body).encode() if body is not None else None
            headers = {"Content-Type": "application/json"} if data else {}
            req     = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                raw = json.loads(resp.read())
            latency = (time.monotonic() - t0) * 1000
            return A2AResponse.success(raw, latency_ms=latency)
        except urllib.error.HTTPError as exc:
            latency = (time.monotonic() - t0) * 1000
            try:
                detail = json.loads(exc.read()).get("error", str(exc))
            except Exception:
                detail = str(exc)
            return A2AResponse.failure(detail, latency_ms=latency)
        except Exception as exc:  # noqa: BLE001
            latency = (time.monotonic() - t0) * 1000
            return A2AResponse.failure(str(exc), latency_ms=latency)

    def _get(self, path: str) -> A2AResponse:
        return self._request("GET", path)

    def _post(self, path: str, body: Dict) -> A2AResponse:
        return self._request("POST", path, body)

    def _put(self, path: str, body: Dict) -> A2AResponse:
        return self._request("PUT", path, body)

    # ── Agent registration ─────────────────────────────────────────────────────

    def register(
        self,
        capabilities: Optional[List[str]] = None,
        endpoint: str = "",
    ) -> A2AResponse:
        """
        Register or refresh this agent's presence in the MCP server.
        Call periodically as a heartbeat.
        """
        resp = self._post("/agents/register", {
            "agent_id": self.agent_id,
            "capabilities": capabilities or [],
            "endpoint": endpoint,
        })
        if resp.ok:
            self._logger.debug("Registered with MCP server.")
        else:
            self._logger.warning("Registration failed: %s", resp.error)
        return resp

    # ── A2A messaging ──────────────────────────────────────────────────────────

    def send_a2a(
        self,
        recipient: str,
        message: Dict[str, Any],
        wait_for_reply: bool = False,
        timeout: int = 30,
        poll_interval: float = 0.5,
    ) -> A2AResponse:
        """
        Send a direct agent-to-agent message (A2A — tight coupling).

        If wait_for_reply=True the method polls the recipient's inbox for a
        reply that references the dispatched message ID (or a reply_to field).
        This simulates synchronous RPC over the async mailbox model.

        Parameters
        ----------
        recipient : str
            Target agent identity.
        message : dict
            Arbitrary payload.
        wait_for_reply : bool
            Block until recipient sends a reply message.
        timeout : int
            Seconds to wait for reply (only relevant when wait_for_reply=True).
        poll_interval : float
            Seconds between inbox polls when waiting.
        """
        resp = self._post("/a2a/send", {
            "sender": self.agent_id,
            "recipient": recipient,
            "message": message,
        })
        if not resp.ok:
            return resp

        msg_id: str = resp.data.get("id", "")
        self._logger.info("A2A sent → %s  [%s]", recipient, msg_id[:8])

        if not wait_for_reply:
            return A2AResponse.success(resp.data, message_id=msg_id)

        # Poll own inbox for a reply referencing msg_id
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            inbox_resp = self._get(f"/a2a/inbox?agent={self.agent_id}")
            if inbox_resp.ok:
                for envelope in inbox_resp.data.get("inbox", []):
                    m = envelope.get("message", {})
                    if m.get("reply_to_id") == msg_id or m.get("in_reply_to") == msg_id:
                        return A2AResponse.success(
                            m,
                            message_id=envelope.get("id"),
                            latency_ms=inbox_resp.latency_ms,
                        )
            time.sleep(poll_interval)

        return A2AResponse.failure(f"A2A reply timeout after {timeout}s (msg_id={msg_id[:8]})")

    def reply_a2a(
        self,
        original_message_id: str,
        recipient: str,
        reply_payload: Dict[str, Any],
    ) -> A2AResponse:
        """
        Send a reply to an A2A message, marking it as a reply.
        """
        payload = dict(reply_payload)
        payload["reply_to_id"] = original_message_id
        return self.send_a2a(recipient, payload)

    def get_inbox(self) -> A2AResponse:
        """Fetch all A2A messages addressed to this agent."""
        return self._get(f"/a2a/inbox?agent={self.agent_id}")

    # ── MCP tool calls ─────────────────────────────────────────────────────────

    def list_tools(self) -> A2AResponse:
        """Discover all tools available on the MCP server."""
        return self._get("/tools")

    def call_tool(self, tool_name: str, params: Optional[Dict[str, Any]] = None) -> A2AResponse:
        """Invoke a named MCP tool with optional parameters."""
        return self._post(f"/tools/{tool_name}", params or {})

    # ── Shared memory ──────────────────────────────────────────────────────────

    def memory_get(self, key: str) -> A2AResponse:
        """Read a value from the swarm's shared memory."""
        return self._get(f"/memory/{key}")

    def memory_set(self, key: str, value: Any) -> A2AResponse:
        """Write a value to the swarm's shared memory."""
        return self._put(f"/memory/{key}", {"value": value})

    # ── Task queue ─────────────────────────────────────────────────────────────

    def queue_pending(self, agent: Optional[str] = None) -> A2AResponse:
        """
        Fetch pending tasks.  If agent is None, fetches all pending tasks;
        otherwise filters to the named agent.
        """
        path = "/queue/pending"
        if agent:
            path += f"?agent={agent}"
        return self._get(path)

    def queue_submit(self, task: Dict[str, Any]) -> A2AResponse:
        """Submit a task to the unified queue."""
        return self._post("/queue/submit", {"task": task})

    # ── Signal bus ─────────────────────────────────────────────────────────────

    def signal_publish(self, signal: str, payload: Any) -> A2AResponse:
        """Publish a named signal to the swarm signal bus."""
        return self._post("/signals/publish", {
            "signal": signal,
            "payload": payload,
            "source_agent": self.agent_id,
        })

    def signals_recent(self, limit: int = 20) -> A2AResponse:
        """Fetch the most recent signals from the bus."""
        return self._get(f"/signals/recent?limit={limit}")

    # ── Agents ─────────────────────────────────────────────────────────────────

    def agents_list(self) -> A2AResponse:
        """List all registered agents and their status."""
        return self._get("/agents")

    def health(self) -> A2AResponse:
        """Check MCP server health."""
        return self._get("/health")

    # ── LLM shortcut ───────────────────────────────────────────────────────────

    def nvidia_complete(
        self,
        prompt: str,
        system: str = "You are a helpful swarm agent assistant.",
        max_tokens: int = 512,
    ) -> A2AResponse:
        """
        Route a completion request through the NVIDIA LLM tool on the MCP server.
        The key is read server-side from NVIDIA_API_KEY — never sent over the wire.
        """
        return self.call_tool("nvidia_complete", {
            "prompt": prompt,
            "system": system,
            "max_tokens": max_tokens,
        })

    # ── Convenience repr ───────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"A2AClient(agent_id={self.agent_id!r}, mcp_url={self.mcp_url!r})"


# ── Quick smoke-test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    agent = sys.argv[1] if len(sys.argv) > 1 else "test_agent"
    client = A2AClient(agent_id=agent)

    print(f"A2AClient smoke-test for '{agent}'")
    print(f"  MCP server: {client.mcp_url}")

    h = client.health()
    if h.ok:
        print(f"  Health: OK  ({h.data})")
    else:
        print(f"  Health: FAIL — {h.error}")
        print("  (Is the MCP server running?  python -m core.mcp.mcp_server)")
        sys.exit(1)

    tools = client.list_tools()
    if tools.ok:
        names = [t["name"] for t in tools.data.get("tools", [])]
        print(f"  Tools: {names}")

    agents = client.agents_list()
    if agents.ok:
        ids = [a["agent_id"] for a in (agents.data or [])]
        print(f"  Agents: {ids}")

    print("Smoke-test passed.")
