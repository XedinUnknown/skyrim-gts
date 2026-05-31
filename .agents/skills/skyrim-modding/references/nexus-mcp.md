# Nexus Mods API and MCP Notes

## What To Use Nexus For

For compatibility work, Nexus pages can provide:

- Requirements and required file versions.
- Optional files and FOMOD choices.
- Incompatibility notes.
- Posts and bugs that document current breakage.
- Changelogs that explain why a pinned old version may be intentional.
- Permissions and redistribution constraints.

Do not bypass login, Cloudflare, Nexus Premium, download restrictions, or human verification. If a page is blocked, use public mirrors, author GitHub/docs, Load Order Library, or ask the user to provide the relevant text.

## Nexus Mods MCP Search Findings

Search results show community Nexus Mods MCP servers exist, but they are not official Nexus infrastructure and should be reviewed before use.

Candidates found:

- `Charrdge/nexusmods-mcp`: described as a Nexus Mods MCP server using REST v1 and GraphQL search/details/files. Search result says stdio/docker support.
- `er2g/nexusmods-mcp-server`: described as NexusMods MCP for searching mods, fetching details, listing files, and downloading without an API key. Treat the "without API key" claim cautiously and verify that it respects Nexus terms.
- MCP directory listings such as `mcpmarket.com/server/nexus-mods`, `mcpworld.com`, and `lobehub.com` list Nexus Mods MCP variants. These are directories, not primary sources.

Quality checks before installing any MCP:

1. Inspect repository source, license, maintainer activity, releases, and issues.
2. Verify whether it requires a Nexus API key and how it stores it.
3. Verify it respects Nexus Terms of Service and does not bypass download restrictions.
4. Prefer read-only/search/detail operations over download automation.
5. Configure API keys via environment variables or secure local config, not committed files.
6. Add narrow MCP permissions where the agent supports them.

## If No MCP Is Configured

Use direct public web research:

- Try `webfetch` first for docs/GitHub/wiki pages.
- Use `npx agent-browser` for pages that require JavaScript rendering.
- Stop at human verification or login walls.
- Ask the user for mod-page text, files tab details, or screenshots when needed.

## Local Metadata Cache Pattern

For large MO2/Wabbajack lists, first index local MO2 metadata before reaching for web automation. MO2 `meta.ini` often already contains Nexus mod IDs, installed file IDs, comments, notes, versions, categories, and a cached `nexusDescription` field.

A robust local workflow is:

- Keep a central reusable SQLite cache outside the project, keyed by Nexus game/mod ID, archive name, or local mod name.
- Build a project-specific active-mod SQLite subset from `modlist.txt`, pointing each active mod to the central cache key.
- Search the project subset with SQLite FTS for normal questions.
- Optionally enrich the central cache through the official Nexus Mods API when `NEXUS_API_KEY` is present.
- Do not use MCP/browser scraping to bypass Cloudflare, login, premium download restrictions, or human verification.

Nexus MCP can still be useful later for read-only search/detail operations, but treat community servers as unvetted until their source, credential handling, and Terms-of-Service behavior are reviewed.
