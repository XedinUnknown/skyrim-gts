# Sources And Research

Use current public sources before improvising. GTS changes quickly and advice can differ between the official Nexus/Vortex collection and community Wabbajack conversions.

## Primary Sources

- GTS wiki: `https://gatetosovngarde.wiki.gg/`
- GTS wiki API: `https://gatetosovngarde.wiki.gg/api.php`
- Installation Guide: `https://gatetosovngarde.wiki.gg/wiki/Installation_Guide`
- Quick Install: `https://gatetosovngarde.wiki.gg/wiki/Quick_Install`
- Troubleshooting: `https://gatetosovngarde.wiki.gg/wiki/Troubleshooting`
- Game Crash: `https://gatetosovngarde.wiki.gg/wiki/Game_Crash`
- Mod Compatibility: `https://gatetosovngarde.wiki.gg/wiki/Mod_Compatibility`
- Performance tweaks: `https://gatetosovngarde.wiki.gg/wiki/Collection_Performance_Tweaks`
- Nexus collection: `https://www.nexusmods.com/games/skyrimspecialedition/collections/qdurkx`
- Load Order Library revision: `https://loadorderlibrary.com/lists/gate-to-sovngarde-revision`
- Wabbajack conversion repo: `https://github.com/FlimsyParking/Gate-to-Sovngarde-Wabbajack`
- Wabbajack conversion README: `https://github.com/FlimsyParking/Gate-to-Sovngarde-Wabbajack/blob/main/README.md`
- Wabbajack metadata: `https://raw.githubusercontent.com/FlimsyParking/Gate-to-Sovngarde-Wabbajack/main/modlists.json`

## MediaWiki API Examples

Fetch page list:

```text
https://gatetosovngarde.wiki.gg/api.php?action=query&list=allpages&aplimit=500&format=json
```

Fetch source for pages:

```text
https://gatetosovngarde.wiki.gg/api.php?action=query&titles=Getting%20Started%7CTroubleshooting%7CMod%20Compatibility&prop=revisions&rvprop=content&rvslots=main&format=json
```

Fetch page extracts if available:

```text
https://gatetosovngarde.wiki.gg/api.php?action=query&prop=extracts&explaintext=1&titles=Getting%20Started&format=json
```

## Local Wiki Cache

The skill helper can clone selected pages or all public article pages into `.agents/skills/gate-to-sovngarde/wiki-cache/`:

```bash
python3 .agents/skills/gate-to-sovngarde/scripts/sync_wiki_pages.py --all --delay 0.5
```

Cache layout:

- `.wiki` files contain raw MediaWiki source for each page.
- `manifest.json` maps page titles to cache filenames and source URLs.
- The cache is ignored by git and can be deleted/rebuilt at any time.

Search policy:

- If `wiki-cache/` exists, search it first for broad or repeated questions.
- If a claim depends on current docs, refresh the relevant page or rerun `--all` before answering.
- If no local cache exists, fetch the specific live page through `webfetch` or the script.
- Use exact page titles from `manifest.json` when citing cached pages.

Future index path:

- Use `manifest.json` plus `.wiki` files as the deterministic source for a lexical index, vector index, or MCP search server.
- Preserve page title, source URL, revision timestamp if added later, section heading, and chunk text in any index.
- Keep the raw wiki cache as the source of truth so embeddings can be regenerated when chunking or model choices change.

## Web Constraints

- Use `webfetch` for public wiki, GitHub, and raw docs when it works.
- Use `npx agent-browser` for public pages that require JavaScript rendering, such as Load Order Library UI pages.
- Do not bypass Cloudflare, Nexus login, human verification, download gates, Nexus Premium restrictions, or paywalls.
- If blocked, say what blocked access and ask the user for the relevant text, screenshot, `loadorder.txt`, `plugins.txt`, crash log, or manager warning.

## Source Interpretation

- The official GTS wiki often describes Vortex collection workflows. Do not blindly apply Vortex steps to Wabbajack/MO2 installations.
- The Wabbajack conversion README and metadata describe the conversion, not necessarily the official Nexus collection.
- Load Order Library is useful for current list contents and order, but a user's installed version may differ.
- Nexus pages are authoritative for individual added mods, but GTS compatibility and pinned versions take precedence for the curated list.
