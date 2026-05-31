# Skyrim MCP Multi-Client Investigation

## Summary

The current `SkyrimMCP.dll` cannot be shared directly by multiple clients. It is a stdio MCP server, so each MCP client launches and owns its own child process. That works for one opencode session, but it is the wrong shape for a background progress poller plus interactive agent sessions.

Recommended solution: run one long-lived MCP gateway that exposes a remote MCP endpoint on localhost, owns one backend `SkyrimMCP.dll` stdio child, and serializes calls to that backend. Point opencode and the progress poller at the gateway URL instead of launching `SkyrimMCP.dll` themselves.

## Findings

- MCP stdio transport is single-client by design: the client starts the server subprocess and communicates over that subprocess' stdin/stdout.
- MCP Streamable HTTP is the standard transport for an independent server process that can handle multiple client connections.
- `opencode.jsonc` currently configures Skyrim as a local MCP server:

```jsonc
"mcp": {
  "skyrim": {
    "type": "local",
    "command": ["cmd.exe", "/c", "E: && cd \\Games\\GTSAV\\mods\\SkyLinkAI\\SKSE\\Plugins\\SkyLinkAI_Server && dotnet.exe SkyrimMCP.dll"]
  }
}
```

- The installed server binary references `WithStdioServerTransport` and `NamedPipeClientStream`, with no HTTP/SSE transport references visible from binary strings.
- The backend server connects to the game through `\\.\pipe\SkyrimMCP`; the practical project constraint is one useful backend connection to the game at a time.

## Why Not Share Stdio Directly

Stdio has no attach/reconnect/multiplex layer. A second client cannot safely connect to the same process' stdin/stdout, and starting another `SkyrimMCP.dll` creates a second backend process competing for the same game pipe. Killing or replacing the child process also does not make opencode reconnect inside an existing session.

## Recommended Architecture

```text
opencode session A ─┐
opencode session B ─┼─ HTTP MCP ─┐
progress poller  ───┘            │
                         skyrim-mcp-gateway
                           - long-lived daemon
                           - client sessions
                           - request queue / mutex
                           - cached event log
                                  │ stdio MCP, one child
                                  ▼
                         dotnet.exe SkyrimMCP.dll
                                  │ named pipe
                                  ▼
                         Skyrim + SKSE + SkyLinkAI
```

The gateway is the only process that starts `SkyrimMCP.dll`. Every external user connects to the gateway as a remote MCP server.

## Gateway Behavior

- Start one backend `SkyrimMCP.dll` child and run the MCP initialize flow once.
- Cache backend `tools/list` and expose those tools to every frontend client.
- For `tools/call`, place calls on a single serialized queue before forwarding to the backend child.
- Maintain independent frontend MCP sessions so multiple opencode instances can initialize independently.
- Restart the backend child if it exits, then reinitialize and report temporary tool failures during reconnect.
- Bind to `127.0.0.1` only by default.
- Optionally require a static bearer token if exposed outside localhost.

## Event Polling Caveat

`skyrim_poll_events` is stateful: it returns events since the last poll. If multiple clients call the backend tool directly, one client can consume events that another client expected.

The gateway should handle this explicitly instead of being a blind proxy for events:

- Preferred: the gateway owns backend `PollEvents` on a timer, appends events to an internal ring buffer, and serves per-client cursors from that buffer.
- Simpler phase 1: reserve `skyrim_poll_events` for the progress poller only and document that interactive sessions should not call it.
- For snapshot polling, normal read-only state tools such as player info, skills, gear, cell info, gold, spells, and shouts are safe to proxy serially.

## opencode Config After Gateway

Once the gateway exists, replace the local MCP entry with a remote one:

```jsonc
"mcp": {
  "skyrim": {
    "type": "remote",
    "url": "http://127.0.0.1:8765/mcp",
    "timeout": 30000
  }
}
```

Restart opencode after changing this config.

## Implementation Options

### Option A: Stdio-to-HTTP MCP Gateway

Build a small gateway in this repo. It speaks Streamable HTTP MCP to clients and raw stdio JSON-RPC MCP to the existing `SkyrimMCP.dll` backend.

Pros:
- Does not require modifying SkyLinkAI or decompiling its game pipe protocol.
- Works with any MCP client that supports remote MCP.
- Keeps the progress poller and opencode on the same access path.

Cons:
- Needs enough MCP server behavior to support initialization, tool listing, tool calls, sessions, and errors.
- Needs special handling for stateful event polling.

This is the recommended path.

### Option B: Patch or Replace `SkyrimMCP.dll`

Modify the server to use Streamable HTTP directly instead of stdio.

Pros:
- Cleanest final shape if the source is available and maintainable.
- No proxy layer.

Cons:
- Depends on having source and being willing to maintain a fork inside a curated GTS install.
- Still needs concurrency control and event cursor design.

This is best only if SkyLinkAI upstream supports it or we intentionally fork the server.

### Option C: Keep Poller Outside MCP

Have the poller read state from another source while opencode keeps owning the stdio MCP session.

Pros:
- Avoids MCP multiplexing.

Cons:
- No equivalent data source currently exists for full player/game state.
- Duplicates integration work and does not solve multi-opencode sessions.

This is not recommended.

## Revised Progress Poller Plan

The progress poller should not spawn `SkyrimMCP.dll`. It should connect to the gateway URL and call read-only tools there. Git recording remains unchanged after snapshots are collected.

Minimal phase 1:

- Implement gateway with one backend child and serialized `tools/call`.
- Convert `opencode.jsonc` to remote MCP.
- Convert progress poller plan to use `SKYRIM_MCP_URL=http://host.docker.internal:8765/mcp` from Docker, while host opencode uses `http://127.0.0.1:8765/mcp`.
- Do not use `skyrim_poll_events` for save/load branching until the gateway has event buffering.

Phase 2:

- Add gateway-owned event polling and per-client cursors.
- Add save/load branching from buffered events plus save directory monitoring.
- Add read/write tool policy so the progress poller can only call safe read-only tools.
