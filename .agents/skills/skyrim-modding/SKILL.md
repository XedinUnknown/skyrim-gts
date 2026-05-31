---
name: skyrim-modding
description: Expert workflow for Skyrim Special Edition/Anniversary Edition and Bethesda Creation Engine modding. Use whenever the user asks about Skyrim mods, plugins, load order, MO2, Vortex, Wabbajack, xEdit/SSEEdit, Creation Kit, Papyrus, SKSE, Address Library, CommonLibSSE-NG, Nexus Mods, compatibility patches, crashes, save safety, ESL/ESP/ESM plugins, BSA/loose files, animations, LOD, ENB/Community Shaders, or adding mods to a curated list. Always apply this skill before giving Skyrim modding advice.
---

# Skyrim Modding

Use this skill for practical Skyrim Special Edition / Anniversary Edition modding, patching, troubleshooting, and mod development. Treat Skyrim modding as a data-integration problem across plugins, assets, scripts, native DLLs, generated outputs, and save-game state.

## Start Here

Before answering, classify the task:

- Install/use a mod: identify manager, runtime, requirements, deployment model, and save impact.
- Add a mod to an existing list: inspect compatibility, included equivalents, conflicts, requirements, and whether support is voided.
- Patch conflicts: use xEdit principles, inspect record winners, create focused patch plugins, and preserve curated list rules.
- Papyrus/CK work: account for source/compiled scripts, properties, quests/aliases, dialogue/scenes, and save-baked state.
- SKSE/native work: identify runtime, SKSE version, Address Library, CommonLibSSE-NG target, and Windows/MSVC constraints.
- Crash/debug: separate load-time, main-menu, new-game, save-load, cell-specific, action-specific, and native-plugin failures.

**For GTS projects: always read `current-game.md` in the project root first.** This auto-generated file contains the active modlist with descriptions, version numbers, and mod IDs. Use it to identify what mods are already installed before searching modlist files or the Wabbajack directory.

If the answer needs more detail than fits here, read the relevant reference file in this skill directory:

- `references/concepts.md` for plugins, records, assets, saves, and conflict theory.
- `references/tools.md` for MO2, Vortex, Wabbajack, xEdit, CK, SKSE, CommonLibSSE-NG, Nemesis/OAR, LOD, and shader tools.
- `references/workflows.md` for adding mods, xEdit patching, troubleshooting, Papyrus, and SKSE workflows.
- `references/recipe-extraction.md` for extracting crafting recipes and item requirements from plugins.
- `references/nexus-mcp.md` for Nexus Mods API/MCP options and caution notes.

## First Principles

- Identify the target runtime before recommending binaries: Steam AE `1.6.1170`, older AE, SE `1.5.97`, GOG, or VR.
- Treat curated modlists as integrated systems. Do not recommend LOOT sorting, manual plugin moves, updating included mods, or broad conflict-rule changes unless the list maintainer explicitly supports it.
- Preserve user saves. Warn when a change requires a new game, affects scripts, swaps major overhauls, removes plugins, changes form IDs, or alters persistent references.
- Prefer reversible changes: profiles, backups, separate output mods, and documented xEdit patches.
- Avoid redistributing third-party assets or plugin records without checking mod permissions.
- Distinguish plugin load order from asset/file priority. A plugin conflict winner is not the same thing as loose-file/BSA overwrite priority.
- Do not clean, compact, ESL-flag, unpack BSA files, regenerate LOD, rerun Nemesis, or update DLLs as a reflex. Explain why the action is needed and what it can break.
- Treat Nexus pages, mod descriptions, file requirements, posts, bug reports, and changelogs as required reading for compatibility-sensitive advice.

## Core Tooling Map

- Vortex: collections, deployment, rules, groups, hardlinks, profiles, staged mods.
- MO2: profiles, virtual file system, left-pane mod priority, right-pane plugin order, separators, Root Builder, Stock Game.
- xEdit/SSEEdit: conflict inspection, patch plugins, compacting ESL only when safe, cleaning only when appropriate.
- Creation Kit: quests, scenes, dialogue, navmesh, scripts, forms, SE/AE CK quirks.
- Papyrus: source `.psc`, compiled `.pex`, properties, events, latent functions, save-baked state.
- SKSE/CommonLibSSE-NG: native plugins, runtime targeting, Address Library IDs, CMake/vcpkg/Conan, Windows/MSVC constraints.
- LOOT: useful for generic lists and metadata, but not authoritative for curated modlists that provide their own order/rules.
- Wabbajack: reproducible list installer; updates may remove files outside the list unless protected by the list's documented workflow.
- Synthesis, zEdit, Wrye Bash, EasyNPC, DynDOLOD/xLODGen/TexGen, Nemesis, OAR, Bodyslide, Cathedral Assets Optimizer, SSE NIF Optimizer, BethINI: generated-output tools that should usually write into separate output mods.
- Recipe extraction: crafting requirements live in `COBJ` records, not usually in wiki pages. In this `skyrim-gts` project, Make commands must run inside the tools container; from the host use `docker compose run --rm tools make ...`. Use `make item Q="item name"` for item provenance, stats, source plugin, and likely mod metadata. If it returns fuzzy matches, answer from them with a caveat instead of probing SQLite schema, plugin files, or temporary Mutagen scripts. Use root `current-game.md` as the **primary source** for "what mods are installed" questions before searching modlist text files. Use narrower Makefile targets (`make search`, `make recipe`, `make chain`) for follow-up recipe facts before searching the Wabbajack install tree. Use xEdit scripts for authoritative inspection/export only when deeper verification is explicitly needed.

## Compatibility Triage

When asked whether a mod can be added:

1. Check if the list already includes it, an older pinned version, a fork, or a functional equivalent.
2. Read requirements, incompatible-mod notes, changelog, bugs, posts, and file-specific install instructions.
3. Check masters, plugin type, DLL/runtime target, SKSE/Address Library, MCM dependencies, animation frameworks, and generated-output requirements.
4. Check conflicts in xEdit: leveled lists, quests, cells/worldspaces, NPCs, perks, races, keywords, scripts, packages, AI data, outfits, races, navmesh, weather, lighting, and water.
5. Check assets: meshes, textures, scripts, interface files, animations, behavior files, sounds, SKSE DLLs, ENB/CS files, and INI files.
6. Classify as likely safe, safe only on new game, needs conflict resolution, needs a patch, needs generated output, unsupported for curated list, or incompatible.
7. For curated lists, include whether support will likely be voided by customization.

## Development Guidance

For Papyrus:

- Keep script changes small and preserve property names/types unless migrating intentionally.
- Avoid polling when events or aliases can do the job.
- Be careful with `OnUpdate`, cloak effects, and scripts attached to many objects.
- Remember compiled scripts and save state can keep old behavior alive.
- Keep `.psc` source and `.pex` compiled output aligned. Do not assume source shipped with a mod matches the deployed compiled script.
- Changing quest aliases, properties, script names, or attached scripts can require a new game or a migration path.

For SKSE/CommonLibSSE-NG:

- Confirm the project targets the same runtime family as the user.
- Use Address Library/CommonLib relocation rather than hard-coded addresses when possible.
- Do not assume Linux builds can produce a working SKSE DLL; Windows/MSVC tooling is commonly required.
- Package DLLs with the expected SKSE path and dependency notes.
- For current Steam AE, SKSE's current AE build is for game `1.6.1170`; GOG AE has a different game version. Do not mix runtime-specific DLLs.
- CommonLibSSE-NG supports SE, AE, and VR multi-targeting and can produce a single DLL for compatible runtime sets, but runtime-specific ports exist and are not interchangeable.

## Troubleshooting Pattern

Ask for or inspect:

- Crash log, SKSE log, Engine Fixes log, `Documents/My Games/Skyrim Special Edition/SKSE`, and manager warnings.
- `plugins.txt`, `loadorder.txt`, and enabled/disabled plugin state.
- Recent changes: new mods, updated mods, deployed rules, removed plugins, INI edits, ENB/Community Shaders changes.
- Whether the issue occurs before main menu, on new game, on existing save, in a specific cell, or after a repeatable action.

Start with missing masters, wrong runtime DLLs, missing Address Library, bad deployment, antivirus/quarantine, and outdated VC++ Redistributable before deeper debugging.

## xEdit Patch Principles

Use xEdit to understand conflict winners, not just red rows. A conflict can be intended, benign, or broken. Bad conflicts usually include one mod unintentionally reverting another mod's meaningful change, partially overwriting a record, or mixing incompatible edits.

When patching:

- Create small, focused patch plugins loaded after the affected masters.
- Add all required masters to the patch.
- Prefer ESL-flagged ESP patches only when the plugin is safe for ESL constraints.
- Keep generated/handmade patches in a separate mod or output folder, not inside upstream mods.
- For curated lists, do not directly edit list plugins unless the maintainer workflow explicitly says to.
- In MO2, move xEdit outputs out of `Overwrite` into a named mod.

## Research Sources

Use these sources before improvising:

- Tome of xEdit: `https://tes5edit.github.io/docs/`
- xEdit The Method: `https://tes5edit.github.io/docs/6-themethod.html`
- xEdit GitHub: `https://github.com/TES5Edit/TES5Edit`
- MO2 GitHub/docs: `https://github.com/ModOrganizer2/modorganizer`
- SKSE: `https://skse.silverlock.org/`
- CommonLibSSE-NG: `https://github.com/CharmedBaryon/CommonLibSSE-NG`
- Creation Kit docs if available; note that the official CK wiki may be down or behind maintenance.
- Nexus Mods pages, Load Order Library, mod author docs, and list-specific docs.

If direct web fetching fails, use `npx agent-browser` for public pages. Do not bypass logins, Cloudflare human checks, premium-download restrictions, or paywalls.
