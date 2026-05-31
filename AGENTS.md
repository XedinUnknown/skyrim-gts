# Project Context

This project is for working with a Gate to Sovngarde (GTS) Skyrim Special Edition install.

The user's GTS install was installed with Wabbajack, not Vortex.

The installed edition is the Anniversary Edition (AE) Wabbajack edition. Assume AE-specific Creation Club/Anniversary Upgrade content is relevant unless the user says otherwise.

The GTS Wabbajack install path is `/mnt/e/games/GTSAV`.

## Gate to Sovngarde Rules

- Treat GTS as a curated integrated modlist, not a generic Skyrim mod setup.
- Prefer GTS wiki, GTS Wabbajack documentation, Load Order Library, and maintainer notes over generic modding advice.
- Do not recommend LOOT sorting, moving plugins, updating included mods, or broad conflict-rule changes unless GTS/Wabbajack documentation explicitly supports it.
- Assume changes to the list may void official support.
- Prefer reversible customizations: MO2 profile backups, separate output mods, xEdit patch plugins, and documented changes.
- For Wabbajack updates, remember files outside the list may be removed unless protected by the documented Wabbajack workflow, such as `[NoDelete]` where applicable.

## Research Workflow

- Use `webfetch` for public wiki/GitHub/docs pages when it works.
- Use `npx agent-browser` when pages block `webfetch`, require JavaScript rendering, or expose dynamic controls such as Load Order Library downloads.
- Do not bypass Cloudflare, login requirements, Nexus Premium restrictions, or human verification challenges.
- Project Make commands must run inside the tools container unless explicitly stated otherwise. From the host, invoke them as `docker compose run --rm tools make <target> ...`. The container has the `/gts` mount and .NET dependencies needed to rebuild indexes when stale. In project instructions and examples, plain `make ...` means “run this Make target inside the tools container.”

## MCP Server Management

The Skyrim MCP server (`SkyrimMCP.dll`) is now accessed through a **gateway proxy** (`skyrim-mcp-gateway`). The gateway is defined in `opencode.jsonc` as a remote MCP server at `http://127.0.0.1:8765/mcp`.

### Architecture

The gateway is a long-lived Docker service that:
- Exposes a Streamable HTTP MCP endpoint at `http://127.0.0.1:8765/mcp`
- Owns exactly one backend `SkyrimMCP.dll` stdio child process
- Serializes all tool calls to the backend (one at a time)
- Manages separate MCP sessions for each frontend client
- Handles backend crashes with automatic restart

Multiple OpenCode sessions and the progress poller can connect concurrently through the gateway.

### Starting the gateway

```bash
docker compose up -d skyrim-mcp-gateway
```

Or start the full environment (gateway + progress poller):

```bash
docker compose up -d
```

### Restarting the gateway

```bash
docker compose restart skyrim-mcp-gateway
```

### If the gateway goes stale

The gateway manages the backend child process. If the backend dies, the gateway automatically restarts it. If the gateway itself dies:

```bash
docker compose up -d skyrim-mcp-gateway
```

OpenCode will reconnect on the next tool invocation.

### Cleaning up orphaned processes

The gateway Docker container manages the `dotnet.exe SkyrimMCP.dll` process. Stopping the container cleans up:

```bash
docker compose down
```

### Legacy: Direct stdio mode (no longer used)

Previously, `opencode.jsonc` configured the skyrim MCP as a local stdio server. Each session spawned its own `SkyrimMCP.dll` child, which could not be shared. The gateway replaces this approach.

## Relevant Skills

- `gate-to-sovngarde`: GTS-specific installation, troubleshooting, compatibility, and Wabbajack guidance.
- `skyrim-modding`: general Skyrim SE/AE modding, xEdit, Papyrus, SKSE, CommonLibSSE-NG, and compatibility work.
- `skyrim-research`: source-finding workflow for Skyrim/GTS/Nexus/Load Order Library research.
