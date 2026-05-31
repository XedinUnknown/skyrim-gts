#!/usr/bin/env python3
"""Progress Poller: captures Skyrim character state snapshots via MCP gateway.

Connects to the skyrim-mcp-gateway, calls read-only tools to capture player state,
normalizes responses, and commits snapshots to a git repo for historical analysis.
"""

import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# MCP HTTP Client (connects through stdio-proxy or directly to gateway)
# ---------------------------------------------------------------------------

class MCPClient:
    """Minimal HTTP MCP client."""

    def __init__(self, url):
        self.url = url
        self.session_id = None

    def _post(self, body: dict, extra_headers: dict = None) -> dict:
        data = json.dumps(body).encode()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if extra_headers:
            headers.update(extra_headers)

        req = urllib.request.Request(self.url, data=data, headers=headers, method="POST")
        try:
            resp = urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"MCP HTTP error {e.code}: {e.read().decode()}")

        # Capture session ID from response
        sid = resp.headers.get("Mcp-Session-Id")
        if sid:
            self.session_id = sid

        content_type = resp.headers.get("Content-Type", "")
        raw = resp.read().decode()

        if resp.status == 202 or not raw:
            return {}

        if "text/event-stream" in content_type:
            last_data = None
            for line in raw.split("\n"):
                if line.startswith("data: "):
                    last_data = json.loads(line[6:])
            return last_data or {}
        else:
            return json.loads(raw)

    def initialize(self, retries=3, retry_delay=5):
        """Initialize MCP session with retry for gateway startup."""
        for attempt in range(retries):
            try:
                result = self._post({
                    "jsonrpc": "2.0",
                    "id": "1",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "progress-poller", "version": "1.0.0"},
                    },
                })
                # Send initialized notification
                self._post({
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                })
                return result
            except Exception as e:
                if attempt < retries - 1:
                    print(f"[poller] Gateway not ready (attempt {attempt+1}/{retries}): {e}", flush=True)
                    time.sleep(retry_delay)
                else:
                    raise

    def call_tool(self, name: str, arguments: dict = None) -> dict:
        return self._post({
            "jsonrpc": "2.0",
            "id": f"call-{name}",
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments or {},
            },
        })


# ---------------------------------------------------------------------------
# Snapshot Builder
# ---------------------------------------------------------------------------

def extract_text(result: dict) -> str:
    """Extract text content from an MCP tools/call result."""
    content = result.get("result", {}).get("content", [])
    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
    return "\n".join(texts)


def safe_float(val, default=0.0):
    try:
        return round(float(val), 2)
    except (TypeError, ValueError):
        return default


def build_snapshot(client: MCPClient) -> dict:
    """Call MCP tools and build a canonical snapshot dict."""
    snap = {"snapshot_version": 1}

    # PlayerInfo — flat dict: {name, race, level, health, healthMax, magicka, ...}
    r = client.call_tool("get_player_info")
    text = extract_text(r)
    try:
        info = json.loads(text)
    except json.JSONDecodeError:
        info = {}
    snap["player"] = {
        "name": info.get("name", ""),
        "race": info.get("race", ""),
        "level": info.get("level", 0),
        "location": info.get("cellName", ""),
        "worldspace": info.get("worldspaceName", ""),
        "coordinates": [
            safe_float(info.get("posX", 0)),
            safe_float(info.get("posY", 0)),
            safe_float(info.get("posZ", 0)),
        ],
        "health": safe_float(info.get("health", 0)),
        "health_max": safe_float(info.get("healthMax", 0)),
        "magicka": safe_float(info.get("magicka", 0)),
        "magicka_max": safe_float(info.get("magickaMax", 0)),
        "stamina": safe_float(info.get("stamina", 0)),
        "stamina_max": safe_float(info.get("staminaMax", 0)),
    }

    # Gold
    r = client.call_tool("get_gold_count")
    text = extract_text(r)
    try:
        gold_info = json.loads(text)
        snap["player"]["gold"] = int(gold_info.get("gold", 0))
    except (json.JSONDecodeError, ValueError):
        snap["player"]["gold"] = 0

    # Skills — {playerLevel, skills: [{name, level, baseLevel}, ...]}
    r = client.call_tool("get_skill_levels")
    text = extract_text(r)
    try:
        skills_info = json.loads(text)
        snap["player"]["level"] = skills_info.get("playerLevel", snap["player"]["level"])
        raw_skills = skills_info.get("skills", [])
        snap["skills"] = {s["name"]: safe_float(s.get("level", 0)) for s in raw_skills if isinstance(s, dict)}
    except (json.JSONDecodeError, ValueError):
        snap["skills"] = {}

    # Perks
    r = client.call_tool("get_perks")
    text = extract_text(r)
    try:
        perks_info = json.loads(text)
        perks_list = perks_info.get("perks", [])
        snap["perk_count"] = len(perks_list)
        snap["perks"] = [
            p.get("name", str(p)) if isinstance(p, dict) else str(p)
            for p in perks_list
        ]
    except (json.JSONDecodeError, ValueError):
        snap["perk_count"] = 0
        snap["perks"] = []

    # Equipment — {equipped: [{name, slot, formId}, ...]}
    r = client.call_tool("get_equipped_items")
    text = extract_text(r)
    try:
        equip_info = json.loads(text)
        items = equip_info.get("equipped", [])
        if isinstance(items, list):
            snap["equipment"] = {item.get("slot", ""): item.get("name", "") for item in items if isinstance(item, dict)}
        else:
            snap["equipment"] = {}
    except (json.JSONDecodeError, ValueError):
        snap["equipment"] = {}

    # CellInfo — flat: {posX, posY, posZ, worldspace, name, ...}
    r = client.call_tool("get_cell_info")
    text = extract_text(r)
    try:
        cell_info = json.loads(text)
        snap["player"]["coordinates"] = [
            safe_float(cell_info.get("posX", 0)),
            safe_float(cell_info.get("posY", 0)),
            safe_float(cell_info.get("posZ", 0)),
        ]
        snap["location_detail"] = {
            "cell": cell_info.get("name", ""),
            "worldspace": cell_info.get("worldspace", ""),
        }
    except (json.JSONDecodeError, ValueError):
        pass

    # KnownShouts
    r = client.call_tool("get_known_shouts")
    text = extract_text(r)
    try:
        shouts_info = json.loads(text)
        shouts_list = shouts_info.get("shouts", [])
        snap["shouts_count"] = len(shouts_list)
        snap["shouts"] = [
            s.get("name", str(s)) if isinstance(s, dict) else str(s)
            for s in shouts_list
        ]
    except (json.JSONDecodeError, ValueError):
        snap["shouts_count"] = 0
        snap["shouts"] = []

    return snap


def compute_hash(snapshot: dict) -> str:
    """Hash all game state — excludes only metadata (timestamp, poll_duration_ms, hash)."""
    snap_copy = {k: v for k, v in snapshot.items()
                 if k not in ("hash", "timestamp", "poll_duration_ms")}
    canonical = json.dumps(snap_copy, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Git Operations
# ---------------------------------------------------------------------------

def git_commit(snapshots_dir: str, snapshot: dict, snapshot_hash: str) -> bool:
    """Write snapshot to file and git commit if changed. Returns True if committed."""
    import subprocess

    repo_dir = os.path.dirname(snapshots_dir)
    filepath = os.path.join(repo_dir, "current.json")

    with open(filepath, "w") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True)

    # Check if content actually changed vs HEAD
    try:
        prev = subprocess.run(
            ["git", "show", "HEAD:current.json"],
            capture_output=True, text=True, cwd=repo_dir,
        )
        if prev.returncode == 0:
            prev_snap = json.loads(prev.stdout)
            if prev_snap.get("hash") == snapshot_hash:
                return False  # no change
    except Exception:
        pass

    # Git add + commit
    subprocess.run(["git", "add", "current.json"], cwd=repo_dir)

    player = snapshot.get("player", {})
    loc = player.get("location") or player.get("worldspace", "unknown")
    lvl = player.get("level", 0)
    name = player.get("name", "unknown")
    ts = datetime.now(timezone.utc).strftime("%H:%M")
    msg = f"snapshot {lvl} {name} @ {loc} [{ts}]"
    subprocess.run(["git", "commit", "-m", msg], cwd=repo_dir)
    return True


# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------

def ensure_gateway(url, retries=5, retry_delay=3):
    """Check if gateway is reachable, wait if not."""
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                base + parsed.path,
                data=json.dumps({"jsonrpc": "2.0", "id": "_ping", "method": "ping", "params": {}}).encode(),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=5)
            if resp.status == 200:
                return True
        except Exception:
            pass
        if attempt < retries - 1:
            print(f"[poller] Waiting for gateway (attempt {attempt+1}/{retries})...", flush=True)
            time.sleep(retry_delay)
    return False


def main():
    poll_interval = int(os.environ.get("POLL_INTERVAL", "60"))
    mcp_url = os.environ.get("SKYRIM_MCP_URL", "http://host.docker.internal:8765/mcp")
    progress_repo = os.environ.get("PROGRESS_REPO", "/progress")

    snapshots_dir = os.path.join(progress_repo, "snapshots")
    os.makedirs(snapshots_dir, exist_ok=True)

    # Initialize git repo if needed
    import subprocess
    if not os.path.exists(os.path.join(progress_repo, ".git")):
        subprocess.run(["git", "init"], cwd=progress_repo)
        subprocess.run(["git", "config", "user.email", "poller@gts"], cwd=progress_repo)
        subprocess.run(["git", "config", "user.name", "GTS Progress Poller"], cwd=progress_repo)

    # Wait for gateway to be available
    print(f"[poller] Waiting for gateway at {mcp_url}", flush=True)
    if not ensure_gateway(mcp_url):
        print("[poller] Gateway not available, exiting", flush=True)
        sys.exit(1)

    client = MCPClient(mcp_url)

    print(f"[poller] Initializing MCP connection", flush=True)
    try:
        client.initialize()
    except Exception as e:
        print(f"[poller] Failed to initialize: {e}", flush=True)
        sys.exit(1)

    print(f"[poller] Ready. Polling every {poll_interval}s", flush=True)

    prev_hash = None
    while True:
        try:
            t0 = time.monotonic()
            snapshot = build_snapshot(client)
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            snapshot["timestamp"] = datetime.now(timezone.utc).isoformat()
            snapshot["poll_duration_ms"] = elapsed_ms
            snapshot["hash"] = compute_hash(snapshot)

            if snapshot["hash"] != prev_hash:
                committed = git_commit(snapshots_dir, snapshot, snapshot["hash"])
                if committed:
                    player = snapshot.get("player", {})
                    print(
                        f"[poller] Committed: {player.get('name', '?')} "
                        f"Lv{player.get('level', '?')} @ {player.get('location', '?')}",
                        flush=True,
                    )
                prev_hash = snapshot["hash"]
            else:
                print("[poller] No change", flush=True)

        except Exception as e:
            print(f"[poller] Error: {e}", flush=True)

        time.sleep(poll_interval)


if __name__ == "__main__":
    main()
