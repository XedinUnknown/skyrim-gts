#!/usr/bin/env python3
"""MCP Gateway: bridges remote HTTP MCP clients to a single stdio SkyrimMCP.dll backend.

Runs on the WSL host side. Spawns one SkyrimMCP.dll child process via cmd.exe
and exposes a Streamable HTTP MCP endpoint on localhost. Multiple opencode sessions
and the progress poller can connect concurrently; the gateway serializes all backend
tool calls.

Usage:
    python3 scripts/mcp-gateway/gateway.py [--host 127.0.0.1] [--port 8765]
"""

import argparse
import json
import os
import queue
import sys
import threading
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn


# ---------------------------------------------------------------------------
# Stdio MCP Backend Client
# ---------------------------------------------------------------------------

class StdioMCPClient:
    """Manages a single SkyrimMCP.dll child process over stdin/stdout."""

    def __init__(self, cmd: str):
        self.cmd = cmd
        self.proc = None
        self._stdin = None
        self._stdout = None
        self._lock = threading.Lock()
        self._pending = {}
        self._request_id = 0
        self._id_lock = threading.Lock()
        self.tools = []
        self._alive = False
        self._restart_lock = threading.Lock()

    def is_alive(self):
        """Check if the backend process is running."""
        if self.proc is None:
            return False
        return self.proc.poll() is None

    def _cleanup_dead(self):
        """Clean up a dead process."""
        if self.proc and not self.is_alive():
            try:
                self._stdin.close()
            except Exception:
                pass
            try:
                self._stdout.close()
            except Exception:
                pass
            self._stdin = None
            self._stdout = None
            self.proc = None
            self._alive = False
            # Fail all pending requests
            with self._lock:
                for req_id, (holder, is_notif) in list(self._pending.items()):
                    if not is_notif and not holder["done"]:
                        holder["error"] = {"code": -32603, "message": "Backend process died"}
                        holder["done"] = True
                self._pending.clear()
            print("[gateway] Backend process died", flush=True)

    def restart(self):
        """Restart the backend process. Thread-safe, only one restart at a time."""
        with self._restart_lock:
            # Double-check after acquiring lock
            if self.is_alive():
                return True

            self._cleanup_dead()
            print("[gateway] Restarting backend...", flush=True)

            try:
                self.start()
                return True
            except Exception as e:
                print(f"[gateway] Backend restart failed: {e}", flush=True)
                return False

    def start(self):
        """Start the backend process and run MCP initialize handshake."""
        import subprocess
        print(f"[gateway] Starting backend: {self.cmd}", flush=True)
        self.proc = subprocess.Popen(
            ["cmd.exe", "/c", self.cmd],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._stdin = self.proc.stdin
        self._stdout = self.proc.stdout
        self._alive = True

        # Start reader thread BEFORE the handshake so responses are consumed
        self.start_reader()

        result = self._send_request("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "skyrim-mcp-gateway", "version": "1.0.0"},
        })
        if result is None:
            stderr_out = ""
            try:
                stderr_out = self.proc.stderr.read(4096).decode(errors="replace")
            except Exception:
                pass
            self._alive = False
            raise RuntimeError(f"Backend initialize failed. stderr: {stderr_out}")

        self._send_notification("notifications/initialized", {})

        tools_result = self._send_request("tools/list", {})
        if tools_result and "tools" in tools_result:
            self.tools = tools_result["tools"]
        print(f"[gateway] Backend ready, {len(self.tools)} tools", flush=True)

    def _next_id(self):
        with self._id_lock:
            self._request_id += 1
            return str(self._request_id)

    def _send_request(self, method: str, params: dict, timeout: float = 30):
        req_id = self._next_id()
        msg = json.dumps({
            "jsonrpc": "2.0", "id": req_id,
            "method": method, "params": params,
        }) + "\n"

        holder = {"result": None, "done": False}
        with self._lock:
            self._pending[req_id] = (holder, False)
            self._stdin.write(msg.encode())
            self._stdin.flush()

        deadline = time.monotonic() + timeout
        while not holder["done"]:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                with self._lock:
                    self._pending.pop(req_id, None)
                return None
            time.sleep(0.01)

        return holder["result"]

    def _send_notification(self, method: str, params: dict):
        msg = json.dumps({
            "jsonrpc": "2.0",
            "method": method, "params": params,
        }) + "\n"
        with self._lock:
            self._stdin.write(msg.encode())
            self._stdin.flush()

    def queue_request(self, method: str, params: dict):
        # If backend is dead, try to restart
        if not self.is_alive():
            if not self.restart():
                req_id = self._next_id()
                holder = {"result": None, "done": True, "error": {
                    "code": -32603,
                    "message": "Skyrim is not running. Start the game and try again.",
                }}
                return req_id, holder

        req_id = self._next_id()
        msg = json.dumps({
            "jsonrpc": "2.0", "id": req_id,
            "method": method, "params": params,
        }) + "\n"

        holder = {"result": None, "done": False, "error": None}
        with self._lock:
            self._pending[req_id] = (holder, False)
            try:
                self._stdin.write(msg.encode())
                self._stdin.flush()
            except (BrokenPipeError, OSError) as e:
                # Backend died mid-write
                self._pending.pop(req_id, None)
                holder["error"] = {"code": -32603, "message": f"Backend pipe broken: {e}"}
                holder["done"] = True
                self._alive = False

        return req_id, holder

    def queue_notification(self, method: str, params: dict):
        msg = json.dumps({
            "jsonrpc": "2.0",
            "method": method, "params": params,
        }) + "\n"
        with self._lock:
            self._stdin.write(msg.encode())
            self._stdin.flush()

    def _reader_loop(self):
        try:
            for line in self._stdout:
                line = line.decode().strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                req_id = msg.get("id")
                if req_id is None:
                    continue

                with self._lock:
                    entry = self._pending.pop(req_id, None)
                if entry is None:
                    continue

                holder, is_notif = entry
                if is_notif:
                    continue

                if "error" in msg:
                    holder["error"] = msg["error"]
                else:
                    holder["result"] = msg.get("result")
                holder["done"] = True
        except Exception:
            pass
        finally:
            # Backend pipe closed — fail all pending requests
            self._alive = False
            with self._lock:
                for req_id, (holder, is_notif) in list(self._pending.items()):
                    if not is_notif and not holder["done"]:
                        holder["error"] = {"code": -32603, "message": "Backend pipe closed"}
                        holder["done"] = True
            print("[gateway] Backend pipe closed", flush=True)

    def start_reader(self):
        t = threading.Thread(target=self._reader_loop, daemon=True)
        t.start()

    def shutdown(self):
        self._alive = False
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Streamable HTTP MCP Server
# ---------------------------------------------------------------------------

class MCPHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class MCPHandler(BaseHTTPRequestHandler):
    gateway: "MCPGateway"

    def log_message(self, fmt, *args):
        print(f"[http] {fmt % args}", flush=True)

    def do_POST(self):
        if self.path != "/mcp":
            self.send_error(404)
            return

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len)
        try:
            msg = json.loads(body)
        except json.JSONDecodeError:
            self._jsonrpc_error(None, -32700, "Parse error")
            return

        if isinstance(msg, list):
            self._handle_batch(msg)
            return

        self._handle_message(msg)

    def _handle_batch(self, messages):
        has_request = any(m.get("method") for m in messages)
        if not has_request:
            for m in messages:
                self._route_message(m)
            self._respond(202, b"")
            return

        results = []
        for m in messages:
            r = self._route_message(m)
            if r is not None:
                results.append(r)

        if len(results) == 1:
            self._respond_json(results[0])
        else:
            self._respond_json(results)

    def _handle_message(self, msg):
        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params", {})

        if method in ("initialize", "ping", "tools/list"):
            result = self._route_message(msg)
            if result is not None:
                self._respond_json(result, session_id=result.pop("_mcp_session_id", None))
            else:
                self._respond(202, b"")

        elif method == "tools/call":
            result = self._route_message(msg)
            if result is not None:
                self._respond_json(result)
            else:
                self._respond(202, b"")

        elif req_id is None:
            self._route_message(msg)
            self._respond(202, b"")

        else:
            result = self._route_message(msg)
            if result is not None:
                self._respond_json(result)
            else:
                self._respond(202, b"")

    def _route_message(self, msg) -> dict | None:
        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params", {})
        is_notification = req_id is None

        if method == "initialize":
            return self.gateway.handle_initialize(req_id, params)

        if method == "ping":
            if is_notification:
                return None
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        if method == "tools/list":
            if is_notification:
                return None
            return self.gateway.handle_tools_list(req_id)

        if method == "tools/call":
            if is_notification:
                self.gateway.queue_request(msg)
                return None
            return self.gateway.handle_tools_call(req_id, params)

        if is_notification:
            return None

        return self._jsonrpc_error_dict(req_id, -32601, f"Method not found: {method}")

    def do_GET(self):
        if self.path != "/mcp":
            self.send_error(404)
            return

        session_id = self.headers.get("Mcp-Session-Id")
        if not session_id or session_id not in self.gateway.sessions:
            self.send_error(400, "Missing or invalid Mcp-Session-Id")
            return

        session = self.gateway.sessions[session_id]
        msg_queue = session.setdefault("_queue", queue.Queue())

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        try:
            while True:
                try:
                    event = msg_queue.get(timeout=30)
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    continue

                if event is None:
                    break

                self.wfile.write(f"event: message\ndata: {json.dumps(event)}\n\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _respond(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _respond_json(self, obj, session_id=None):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if session_id:
            self.send_header("Mcp-Session-Id", session_id)
        self.end_headers()
        self.wfile.write(body)

    def _jsonrpc_error(self, req_id, code, message):
        self._respond_json({
            "jsonrpc": "2.0", "id": req_id,
            "error": {"code": code, "message": message},
        })

    @staticmethod
    def _jsonrpc_error_dict(req_id, code, message):
        return {
            "jsonrpc": "2.0", "id": req_id,
            "error": {"code": code, "message": message},
        }


# ---------------------------------------------------------------------------
# Gateway Logic
# ---------------------------------------------------------------------------

class MCPGateway:
    def __init__(self, host, port, backend_cmd):
        self.host = host
        self.port = port
        self.backend = StdioMCPClient(backend_cmd)
        self.sessions = {}

    def start(self):
        self.backend.start()
        self._start_server()

    def handle_initialize(self, req_id, params):
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "_initialized": True,
            "_client_info": params.get("clientInfo", {}),
        }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "skyrim-mcp-gateway", "version": "1.0.0"},
            },
            "_mcp_session_id": session_id,
        }

    def handle_tools_list(self, req_id):
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": self.backend.tools},
        }

    def handle_tools_call(self, req_id, params):
        tool = params.get("name", "?")
        req_id_back, holder = self.backend.queue_request("tools/call", params)
        deadline = time.monotonic() + 60
        while not holder["done"]:
            if time.monotonic() > deadline:
                print(f"[gateway] tools/call {tool} → timeout", flush=True)
                return self._error(req_id, -32603, "Backend timeout")
            time.sleep(0.01)

        if holder["error"]:
            print(f"[gateway] tools/call {tool} → error: {holder['error'].get('message','?')}", flush=True)
            return {"jsonrpc": "2.0", "id": req_id, "error": holder["error"]}

        result = holder["result"]
        # Log truncated response body for debugging
        try:
            body_str = json.dumps(result)
            preview = body_str[:200] + "..." if len(body_str) > 200 else body_str
            print(f"[gateway] tools/call {tool} → {len(body_str)} bytes: {preview}", flush=True)
        except Exception:
            pass
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def queue_request(self, msg):
        method = msg.get("method")
        params = msg.get("params", {})
        self.backend.queue_request(method, params)

    def _error(self, req_id, code, message):
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    def _start_server(self):
        MCPHandler.gateway = self
        server = MCPHTTPServer((self.host, self.port), MCPHandler)

        def _serve():
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass

        t = threading.Thread(target=_serve, daemon=True)
        t.start()
        print(f"[gateway] Listening on {self.host}:{self.port}", flush=True)

        def _shutdown():
            self.backend.shutdown()
            server.shutdown()

        import atexit
        atexit.register(_shutdown)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[gateway] Shutting down...", flush=True)
            _shutdown()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Skyrim MCP Gateway")
    parser.add_argument("--host", default=os.environ.get("GATEWAY_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("GATEWAY_PORT", "8765")))
    args = parser.parse_args()

    backend_cmd = os.environ.get(
        "SKYRIM_MCP_CMD",
        r"E: && cd \Games\GTSAV\mods\SkyLinkAI\SKSE\Plugins\SkyLinkAI_Server && dotnet.exe SkyrimMCP.dll",
    )

    gw = MCPGateway(args.host, args.port, backend_cmd)
    gw.start()


if __name__ == "__main__":
    main()
