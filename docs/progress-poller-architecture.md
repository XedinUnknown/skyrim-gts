# GTS Progress Poller Architecture

Automated character progress tracking via MCP tools, with git-based time-series history.

## Overview

A Docker container polls the Skyrim MCP gateway every 60 seconds, captures character state snapshots, and commits them to a git subrepo for historical analysis. The gateway (`skyrim-mcp-gateway` service) is a separate container that owns the single backend `SkyrimMCP.dll` process and exposes a Streamable HTTP MCP endpoint.

## Architecture

```
┌────────────────────────────────────────────┐
│  Docker container (progress-poller)         │
│  ┌─────────────────────────────────────┐   │
│  │  Python poller + MCP client         │   │
│  │  - Connects to gateway HTTP MCP     │   │
│  │  - Calls MCP tools via JSON-RPC     │   │
│  │  - Normalizes to canonical JSON     │   │
│  │  - Git commits snapshots            │   │
│  └─────────┬───────────────────────────┘   │
│            ⬍ HTTP                         │
└────────────┬───────────────────────────────┘
             ⬍ http://skyrim-mcp-gateway:8765/mcp
┌────────────┴───────────────────────────────┐
│  Docker container (skyrim-mcp-gateway)      │
│  skyrim-mcp-gateway                         │
│    ↕ stdio MCP, one child                   │
│  dotnet.exe SkyrimMCP.dll                   │
│    ↕ named pipe \\.\pipe\SkyrimMCP          │
│  Skyrim + SKSE + SkyLinkAI plugin          │
└────────────────────────────────────────────┘
```

OpenCode also connects to the gateway at `http://127.0.0.1:8765/mcp` (published port).

## Components

### 1. Gateway Service (`scripts/mcp-gateway/`)

**Base image:** `python:3.12-alpine`

**What it does:**
- Spawns one `cmd.exe /c ... dotnet.exe SkyrimMCP.dll` child via WSL interop
- Performs MCP initialize handshake with the backend
- Caches `tools/list` and replays it to every frontend client
- Exposes Streamable HTTP MCP at `http://0.0.0.0:8765/mcp`
- Serializes all backend tool calls (one at a time)
- Manages separate MCP sessions for each frontend client
- Handles backend crashes with automatic restart

**Mounts required:**
- `/init:/init:ro` — WSL binfmt interpreter
- `/run/WSL:/run/WSL` — WSL interop socket
- `/mnt/c/Windows/System32:/mnt/c/Windows/System32:ro` — cmd.exe and system DLLs

### 2. Progress Poller Service (`scripts/progress-poller/`)

**Base image:** `python:3.12-alpine` (~50MB)

**What it does:**
- Connects to the gateway at `SKYRIM_MCP_URL`
- Calls read-only MCP tools to capture player state
- Normalizes responses to canonical snapshot JSON
- Calculates SHA-256 hash for change detection
- Git commits snapshots when state changes

**Mounts required:**
- `${PROGRESS_REPO_HOST_PATH:-../gts-progress}:/progress` — git snapshot repository

**Environment variables:**
- `POLL_INTERVAL=60` — seconds between polls
- `PROGRESS_REPO=/progress` — path to git snapshot repository in the container
- `SKYRIM_MCP_URL=http://skyrim-mcp-gateway:8765/mcp` — gateway endpoint (Docker DNS)

### 2. Entrypoint Script (`scripts/progress-poller/entrypoint.sh`)

Starts the poller. It does not need WSL interop because it never launches Windows binaries:

```bash
#!/bin/sh
exec python3 /poller.py
```

### 3. Poller Script (`scripts/progress-poller/poller.py`)

**Main loop:**
1. Connect to the Skyrim MCP gateway at `SKYRIM_MCP_URL`
2. Send MCP protocol handshake: `initialize` → `initialized`
3. Call tools sequentially:
   - `GetPlayerInfo` — name, race, level, health/magicka/stamina, location
   - `GetSkillLevels` — all 18 skills
   - `GetPerks` — acquired perks
   - `GetEquippedItems` — gear
   - `GetCellInfo` — exact coordinates
   - `GetGoldCount` — gold
   - `GetKnownSpells` — spells (optional, page=1)
   - `GetKnownShouts` — shouts
4. Normalize responses to canonical snapshot JSON (sorted keys, rounded floats)
5. Calculate SHA-256 hash of snapshot
6. If hash differs from `current.json`:
   - Write `snapshots/<timestamp>.json`
   - Update `current.json` symlink
   - `git add` + `git commit` with message: `snapshot <level> <name> @ <location>`
7. Sleep `POLL_INTERVAL` seconds

**MCP Protocol:**
- Remote MCP over HTTP to the gateway
- No direct backend process management
- Reuses the long-lived gateway instead of spawning `SkyrimMCP.dll`

### 4. Snapshot Schema

```json
{
  "snapshot_version": 1,
  "timestamp": "2026-05-30T18:00:00Z",
  "poll_duration_ms": 423,
  "player": {
    "name": "Xedin",
    "race": "Dark Elf",
    "level": 3,
    "location": "Whiterun",
    "coordinates": [8675.51, -40251.35, 3146.09],
    "health": {"current": 100, "base": 100},
    "magicka": {"current": 120, "base": 100},
    "stamina": {"current": 100, "base": 100},
    "gold": 3624
  },
  "skills": {
    "destruction": 25,
    "heavy_armor": 17,
    ...
  },
  "perk_count": 2,
  "perks": ["Novice Destruction", "Fickle Fate"],
  "equipment": {
    "head": "Iron Helmet",
    "body": "Iron Plate Armor",
    "left_hand": "Raise Corpse",
    "right_hand": "Flames",
    ...
  },
  "hash": "sha256:abc123..."
}
```

**Normalization rules:**
- All keys in lexical order (`json.dumps(sort_keys=True)`)
- Floats rounded to 2 decimal places
- Empty arrays as `[]`, nulls for missing gear
- `hash` = SHA-256 of all other fields (change detection)

### 5. Git History Model

**Repo structure:**
```
gts-progress/
├── current.json          → latest snapshot (symlink or copy)
├── snapshots/
│   ├── 2026-05-30T18-00-00.json
│   ├── 2026-05-30T18-01-00.json
│   └── ...
└── README.md             → AI-readable summary (auto-generated)
```

**Commit strategy:**
- One commit per poll (git handles object dedup for unchanged content)
- Commit message: `snapshot <level> <name> @ <location> [Δskills: +Destruction 2]`
- Tags for save games: `git tag save-<savename>` when save detected

**Save/load detection:**
- Poll `skyrim_poll_events` for `cell_loaded` events
- Monitor save directory mtime: `/mnt/c/Users/Owner/Documents/My Games/Skyrim Special Edition/Saves/`
- When `cell_loaded` fires + save mtime changed:
  - Find matching tag: `git tag -l "save-*" | grep <save-name>`
  - Create branch from that point: `git checkout -b session-<timestamp> <tag>`
  - Next poll continues from save point (history branches naturally)

### 3. Docker Compose Service

```yaml
services:
  skyrim-mcp-gateway:
    build: scripts/mcp-gateway
    ports:
      - "127.0.0.1:8765:8765"
    volumes:
      - /init:/init:ro
      - /run/WSL:/run/WSL
      - /mnt/c/Windows/System32:/mnt/c/Windows/System32:ro
    environment:
      - GATEWAY_HOST=0.0.0.0
      - GATEWAY_PORT=8765
      - SKYRIM_MCP_CMD=E: && cd \Games\GTSAV\mods\SkyLinkAI\SKSE\Plugins\SkyLinkAI_Server && dotnet.exe SkyrimMCP.dll
    user: "${UID:-1000}:${GID:-1000}"
    restart: unless-stopped

  progress-poller:
    build: scripts/progress-poller
    depends_on:
      - skyrim-mcp-gateway
    volumes:
      - ${PROGRESS_REPO_HOST_PATH:-../gts-progress}:/progress
    environment:
      - POLL_INTERVAL=60
      - PROGRESS_REPO=/progress
      - SKYRIM_MCP_URL=http://skyrim-mcp-gateway:8765/mcp
    user: "${UID:-1000}:${GID:-1000}"
    restart: unless-stopped
```

### 4. Usage

```bash
# Start everything (gateway + poller)
docker compose up -d

# Start only the gateway (for opencode use)
docker compose up -d skyrim-mcp-gateway

# View poller logs
docker compose logs -f progress-poller

# Stop everything
docker compose down
```

OpenCode connects to the gateway at `http://127.0.0.1:8765/mcp` (configured in `opencode.jsonc`).

## Save/Load Detection (Deferred)

Phase 1 skips save detection. Pure polling + git time-series first.

**Phase 2:** Add gateway-owned event polling with per-client cursors, plus save directory monitoring for automatic history branching.

## Notes

- **Gateway:** Must be running before the poller starts (`docker compose up -d skyrim-mcp-gateway`)
- **MCP server:** Accessed through the long-lived gateway; the poller must not spawn `SkyrimMCP.dll`
- **Event polling:** `skyrim_poll_events` is not used in phase 1 to avoid stateful event consumption conflicts between multiple clients
