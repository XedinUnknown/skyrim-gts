# Skyrim GTS Toolkit

AI-assisted tooling for a [Gate to Sovngarde](https://www.nexusmods.com/skyrimspecialedition/mods/86886) (GTS) Skyrim Special Edition install. Connects to a running game via MCP, indexes mod metadata and crafting recipes, and tracks character progression over time.

## What's in here

| Component | Purpose |
|-----------|---------|
| **MCP Gateway** | Long-lived proxy that owns a single `SkyrimMCP.dll` backend; serves HTTP MCP at `:8765/mcp` for multiple concurrent clients |
| **Progress Poller** | Docker service that polls game state (player info, inventory, quests) every 60s and commits snapshots to `gts-progress/` |
| **Recipe Index** | SQLite database of craftable items and their recipes, built from the MO2 profile's plugin list |
| **Mod Metadata** | Indexed mod descriptions with optional Nexus API enrichment and AI summarization |
| **OpenCode Skills** | Agent skills for GTS-specific troubleshooting, Skyrim modding, and Nexus/Load Order Library research |

## Prerequisites

- Linux with Docker and Docker Compose
- Wabbajack GTS install at `/mnt/e/games/GTSAV` (or set `GTS_HOST_PATH`)
- [OpenCode](https://opencode.ai) CLI (for AI agent features)
- Skyrim Special Edition / Anniversary Edition installed and runnable via `cmd.exe` from WSL

## Quick start

```bash
# 1. Clone
git clone git@github.com:XedinUnknown/skyrim-gts.git
cd skyrim-gts

# 2. Copy and edit environment
cp .env.example .env
# Edit .env — set GTS_HOST_PATH if your install isn't at /mnt/e/games/GTSAV

# 3. Start the gateway (must be running for any MCP tools to work)
make gateway-start

# 4. Start the progress poller (optional — commits character snapshots to gts-progress/)
make poller-start

# 5. Build the recipe + mod metadata index (first time only, or after mod list changes)
docker compose run --rm tools make rebuild
```

## Usage

### Query crafting recipes

```bash
docker compose run --rm tools make search Q=backpack
docker compose run --rm tools make recipe Q="Leather Backpack"
docker compose run --rm tools make chain Q="Leather Backpack" DEPTH=4
docker compose run --rm tools make item Q="Black Leather Backpack"
docker compose run --rm tools make best MATERIALS="leather strips"
```

### Search mod metadata

```bash
docker compose run --rm tools make mod-search Q=perks
docker compose run --rm tools make mod-summarize          # AI-summarize active mods
docker compose run --rm tools make mod-summarize GLOBAL=1  # summarize all cached mods
```

### Character progression

The progress poller snapshots your character state to `gts-progress/` every minute. Inspect history:

```bash
cd gts-progress
git log --oneline
cat current.json
```

### OpenCode integration

Start the gateway first, then OpenCode connects automatically via the config in `opencode.jsonc`. All 87+ Skyrim tools (player info, inventory, quests, spells, NPCs, teleport, etc.) become available to the agent.

## Gateway lifecycle

The gateway manages a single `SkyrimMCP.dll` child process. If the game closes, it auto-restarts the backend when the game is relaunched.

```bash
make gateway-start    # start in background
make gateway-status   # check if running
make gateway-stop     # stop
make poller-logs      # tail poller output
```

## Project structure

```
scripts/
  mcp-gateway/       # Python HTTP MCP gateway (gateway.py, Dockerfile)
  progress-poller/   # Docker poller service (poller.py, Dockerfile)
tools/               # Recipe indexer, mod metadata, query scripts
cache/               # SQLite indexes and build artifacts
gts-progress/        # Character snapshot git repo (separate .git)
docs/                # Generated game state docs
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GTS_HOST_PATH` | `/mnt/e/games/GTSAV` | Path to GTS Wabbajack install |
| `NEXUS_API_KEY` | — | Nexus Mods API key for mod enrichment |
| `POLL_INTERVAL` | `60` | Seconds between game state polls |
| `GATEWAY_HOST` | `127.0.0.1` | Gateway bind address |
| `GATEWAY_PORT` | `8765` | Gateway port |

## Notes

- This project treats GTS as a curated modlist. Don't recommend LOOT sorting, plugin moves, or broad conflict changes unless GTS documentation supports it.
- `gts-progress/` has its own git repo. Always `cd` into it before running git commands there.
- See `AGENTS.md` for AI agent guidelines and safety rules.
