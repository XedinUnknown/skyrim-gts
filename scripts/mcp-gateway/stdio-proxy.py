#!/usr/bin/env python3
"""Stdio-to-HTTP MCP proxy. Auto-starts the skyrim-mcp-gateway if needed.

OpenCode spawns this as a local MCP server (stdio transport). The proxy:
1. Starts the gateway daemon if it's not already running
2. Bridges stdin → HTTP POST → stdout for every JSON-RPC message

This gives transparent multi-client access: each OpenCode session gets its
own wrapper process, all talking to one shared gateway backend.

Logs go to /tmp/skyrim-proxy.log (append mode) for debugging.
"""

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

LOG_FILE = "/tmp/skyrim-proxy.log"

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] {msg}\n"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line)
    except Exception:
        pass

GATEWAY_HOST = os.environ.get("GATEWAY_HOST", "127.0.0.1")
GATEWAY_PORT = int(os.environ.get("GATEWAY_PORT", "8765"))
GATEWAY_URL = f"http://{GATEWAY_HOST}:{GATEWAY_PORT}/mcp"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GATEWAY_SCRIPT = os.path.join(SCRIPT_DIR, "gateway.py")
PID_FILE = os.path.join(SCRIPT_DIR, ".gateway.pid")
STARTUP_TIMEOUT = 10


def gateway_alive():
    """Check if the gateway is already running and responding."""
    try:
        req = urllib.request.Request(
            GATEWAY_URL,
            data=json.dumps({
                "jsonrpc": "2.0", "id": "_ping",
                "method": "ping", "params": {},
            }).encode(),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=3)
        return resp.status == 200
    except Exception:
        return False


def start_gateway():
    """Start the gateway as a background daemon."""
    log("Starting gateway daemon...")
    subprocess.Popen(
        [sys.executable, GATEWAY_SCRIPT,
         "--host", GATEWAY_HOST, "--port", str(GATEWAY_PORT)],
        stdout=open("/tmp/skyrim-mcp-gateway.log", "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if gateway_alive():
            log("Gateway is alive")
            return True
        time.sleep(0.3)
    log("Gateway startup timed out")
    return False


def ensure_gateway():
    """Make sure the gateway is running, start it if not."""
    if gateway_alive():
        log("Gateway already running")
        return True
    return start_gateway()


def proxy_message(line: str) -> str | None:
    """Forward one JSON-RPC message to the gateway, return response or None."""
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        log(f"PARSE ERROR: {line[:200]}")
        return None

    method = msg.get("method", "?")
    msg_id = msg.get("id", "(notif)")
    log(f" >> {method} id={msg_id}")

    data = json.dumps(msg).encode()
    req = urllib.request.Request(
        GATEWAY_URL,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 202:
            log(f" << 202 (notification accepted)")
            return None
        log(f" << HTTP {e.code}: {body[:200]}")
        return body if body else None
    except Exception as e:
        log(f" << ERROR: {e}")
        return None

    raw = resp.read().decode()
    if resp.status == 202 or not raw:
        log(f" << 202 empty")
        return None

    # Truncate large tool/list responses for log readability
    preview = raw[:300] + "..." if len(raw) > 300 else raw
    log(f" << {len(raw)} bytes: {preview}")
    return raw


def main():
    log(f"=== Proxy started (pid={os.getpid()}) ===")
    log(f"Gateway URL: {GATEWAY_URL}")

    if not ensure_gateway():
        log("FATAL: Gateway failed to start")
        print("[proxy] Gateway failed to start", file=sys.stderr, flush=True)
        sys.exit(1)

    # Forward each line from stdin to the gateway
    line_count = 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        line_count += 1
        response = proxy_message(line)
        if response is not None:
            sys.stdout.write(response + "\n")
            sys.stdout.flush()

    log(f"=== Stdin closed after {line_count} messages, exiting ===")


if __name__ == "__main__":
    main()
