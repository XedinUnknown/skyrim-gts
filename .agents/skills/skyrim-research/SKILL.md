---
name: skyrim-research
description: Research Skyrim Special Edition, Skyrim modding, Nexus Mods pages, Load Order Library pages, Creation Kit docs, SKSE/CommonLibSSE resources, and Gate to Sovngarde sources. Use this whenever the user asks about Skyrim, SSE, AE, SKSE, Papyrus, xEdit, Vortex, MO2, Wabbajack, Nexus collections, Load Order Library, or mod compatibility; use Agent Browser when direct fetching is blocked by Cloudflare, login walls, or dynamic pages.
---

# Skyrim Research

Use this skill to gather reliable context for Skyrim Special Edition modding questions before answering or editing project files.

## Source Order

Prefer primary or near-primary sources:

1. Official modlist docs, wiki pages, changelogs, GitHub repos, and pinned Discord/Nexus information supplied by the user.
2. Load Order Library for `loadorder.txt`, `plugins.txt`, modlist structure, and plugin ordering.
3. Nexus Mods pages for collection/mod descriptions, files, requirements, posts, and bug reports.
4. Creation Kit wiki/docs, xEdit docs, SKSE docs, CommonLibSSE/CommonLibSSE-NG docs, and Address Library docs for implementation details.
5. Community posts only as supporting evidence, not as final authority.

## Browser Fallback

If direct fetching fails with `403`, Cloudflare, login, JavaScript rendering, or incomplete content:

```bash
npx agent-browser open <url>
npx agent-browser wait --load networkidle
npx agent-browser snapshot -i -u -c
```

If the page changes after a click, re-run `snapshot` before using refs again. For pages with download buttons or hidden panels, click the relevant ref, wait, and re-snapshot.

Do not attempt to bypass authentication, paywalls, Nexus Premium restrictions, or human verification challenges. If a page requires a human action or account access, report that clearly and use alternate public sources.

## Research Checklist

For modlist or compatibility questions, capture:

- Skyrim runtime/version: SE `1.5.x`, AE `1.6.x`, current Steam `1.6.1170`, GOG, or VR.
- Manager/tooling: Vortex collection, MO2/Wabbajack, Root Builder, Stock Game, LOOT, xEdit, Nemesis, OAR, Community Shaders.
- Install constraints: clean game, English language, same-drive staging, hardlink deployment, required Visual C++ Redistributable, disk space.
- Plugin constraints: missing masters, ESL/ESP/ESM status, cyclic rules, load order position, intentionally pinned old mod versions.
- Native-code constraints: SKSE version, Address Library version, Engine Fixes/preloader, CommonLibSSE runtime target.
- Save constraints: new game required, update save compatibility, scripts baked into saves.

## Output Style

Be explicit about confidence and source limitations. Separate facts from assumptions. For troubleshooting, give the safest diagnostic path first and avoid telling the user to sort or rearrange a curated modlist unless the source says that is supported.
