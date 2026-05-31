---
name: gate-to-sovngarde
description: Expert support for Gate to Sovngarde (GTS), JaySerpa's Skyrim Special Edition collection, including the Nexus/Vortex collection and community Wabbajack/MO2 conversions. Use this whenever the user mentions Gate to Sovngarde, GTS, qdurkx, JaySerpa collection, GTS Wabbajack, GTS AE/non-AE, GTS compatibility, GTS gameplay systems, GTS performance, GTS install/update issues, Vortex collection warnings, MO2/Root Builder/Stock Game for GTS, or adding/removing/patching mods in GTS.
---

# Gate to Sovngarde

Use this skill for Gate to Sovngarde (GTS), JaySerpa's curated Skyrim Special Edition collection and its community Wabbajack conversions. Treat GTS as an integrated modlist with curated patches, pinned versions, tuned MCMs, and intentional load-order/configuration decisions.

## Start Here

Classify the request before answering:

- Install/update: determine whether the user is using official Nexus/Vortex GTS or a Wabbajack/MO2 conversion, and whether they have the Anniversary Edition Upgrade.
- Troubleshooting: separate manager/deployment warnings, SKSE/DLL launch errors, crash logs, in-game intended mechanics, and performance/resolution issues.
- Gameplay: explain GTS systems from the wiki rather than vanilla Skyrim assumptions.
- Compatibility/customization: check GTS compatibility sources first, then use general Skyrim modding/xEdit principles conservatively.
- Research: use the GTS wiki API, Wabbajack GitHub repo, Load Order Library, maintainer docs, and user-provided files before guessing.

For more detail, read the relevant bundled reference:

- `references/sources.md` for public sources, API endpoints, and research constraints.
- `references/install-update.md` for Vortex and Wabbajack install/update facts.
- `references/gameplay-systems.md` for GTS mechanics, progression, survival, travel, combat, traits, races, perks, and transformations.
- `references/troubleshooting.md` for common GTS errors, crashes, performance, and save-safety guidance.
- `references/compatibility-customization.md` for adding mods, patching, and unsupported-change rules.

If the user asks general Skyrim modding questions while working on GTS, also apply the `skyrim-modding` skill.

## Source Priority

Prefer sources in this order:

1. Current GTS wiki pages and maintainer notes.
2. Wabbajack conversion README/metadata when the user is on a Wabbajack/MO2 edition.
3. For this local `skyrim-gts` project, use the `gts-local-tools` skill for the DB schema, Makefile targets, container setup, and tool pipeline. Key entry points: `make mod-search Q=<query>`, `make item Q="item name"`, `make game-readme`, and `current-game.md`. Use these before broad Wabbajack-directory searches.
4. Load Order Library and installed `loadorder.txt`, `plugins.txt`, `modlist.txt`, crash logs, and manager warnings.
5. Nexus mod pages and changelogs for added mods.
6. General Skyrim modding knowledge.

When source status matters, state whether advice is documented by GTS, documented by the Wabbajack conversion, inferred from Skyrim modding practice, or unverified.

## Safety Rules

- Do not recommend LOOT sorting, Vortex sort-button fixes, moving plugins, dragging mods, updating included mods, compacting/ESL-flagging list plugins, cleaning plugins, regenerating outputs, or broad conflict-rule changes unless the relevant GTS/Wabbajack documentation supports that exact action.
- Do not recommend updating individual included mods just because Nexus has a newer version. Pinned older versions may be intentional.
- Do not recommend removing mods from GTS as a first fix. Prefer disabling via MCM/INI if the mod supports it, or make a documented patch.
- Tell users that modified GTS installs may not receive official support.
- Prefer reversible changes: manager profile backups, named output mods, `[NoDelete]` for Wabbajack custom mods when documented, and separate xEdit patch plugins.
- Protect saves. Warn when changes require a new game, affect scripts, remove plugins, change major overhauls, or cross a GTS update that the changelog says is save-incompatible.
- Do not bypass Cloudflare, Nexus login, human verification, paywalls, or Nexus Premium restrictions. Use public docs or ask the user for the relevant text/log.

## GTS Facts To Preserve

- Official GTS is a Nexus collection by JaySerpa, commonly identified by collection slug `qdurkx`.
- Community Wabbajack conversions are maintained separately and may have AE and non-AE editions.
- GTS targets current Steam Skyrim SE/AE; GOG requires documented compatibility steps and is not the default.
- Old saves are not compatible with a fresh GTS install; start a new character.
- The game language should be English.
- Anniversary Edition Upgrade content changes which optional/recommended files are required. If the user owns AE Upgrade, verify Creation Club content was downloaded and the matching edition/optional files are installed.
- GTS intentionally changes many vanilla mechanics: alternate start, traits, Story Mode, survival, restricted fast travel, no menu pause, more lethal combat, container limits, injuries, stress/fear, new travel options, Campfire Skills of the Wild, Adamant/Hand to Hand perks, Stormcrown Thu'um perks, and transformation systems.

## Troubleshooting Pattern

Ask for or inspect only what is needed:

- Install/manager issue: manager type, edition, exact warning text, whether install/update finished, AE ownership/content state, disk space, clean install state, and whether non-GTS mods are present.
- Crash: crash log path/content, whether crash is before main menu, on New Game, on save load, in a cell, or during an action.
- SKSE/DLL issue: runtime version, SKSE messages, Address Library/Engine Fixes state, VC++ Redistributable, antivirus/quarantine, and GOG vs Steam.
- Gameplay confusion: check whether the symptom is an intended GTS mechanic before treating it as a bug.
- Performance/resolution: Community Shaders, SSE Display Tweaks, Auto Resolution, BethINI Pie, pagefile/swap, VRAM, resolution, and Wabbajack/MO2 vs Vortex paths.

For Vortex-specific GTS errors, the wiki sometimes instructs users to apply collection rules, reset plugin groups, sort within the collection workflow, or follow exact group assignments. Do not generalize that into generic LOOT advice.

For Wabbajack/MO2 GTS, the conversion README explicitly says not to use the sort button and not to drag/drop mods or plugins unless the user knows what they are doing.

## Adding Mods To GTS

When asked whether a mod can be added:

1. Check `Mod Compatibility` on the GTS wiki and whether the mod is already present, pinned, forked, patched, or functionally replaced.
2. Identify manager/install edition: Vortex collection, Wabbajack AE, or Wabbajack non-AE.
3. Inspect runtime-sensitive requirements: SKSE DLLs, Address Library, MCM, animation frameworks, ENB/Community Shaders, and generated-output tools.
4. Inspect record and asset conflicts in xEdit and the manager where needed.
5. Prefer a separate add-on mod and focused patch over editing GTS mods directly.
6. State the support risk and whether a new game is needed.

Known public compatibility examples change over time. Re-check the live page before relying on cached memory. At time of writing, examples included compatible UI/camera/audio/magic/misc mods, some mods needing conflict resolution or patches, and Ordinator as incompatible.

## Local Wiki Cache

This skill includes `scripts/sync_wiki_pages.py`, a small MediaWiki API fetcher. Use it to refresh selected public wiki pages or clone all public article pages into `wiki-cache/` when you need current text and webfetch is not enough.

When `wiki-cache/` exists, search it before relying on memory. Prefer local cache search for repeat questions, broad compatibility checks, and troubleshooting pages, then refresh from the live wiki when exact current wording matters.

Fetch selected pages:

```bash
python3 .agents/skills/gate-to-sovngarde/scripts/sync_wiki_pages.py "Getting Started" "Troubleshooting" "Mod Compatibility"
```

Clone all public article pages and write a manifest:

```bash
python3 .agents/skills/gate-to-sovngarde/scripts/sync_wiki_pages.py --all --delay 0.5
```

Search the cloned wiki with ripgrep or the available content-search tool against `.agents/skills/gate-to-sovngarde/wiki-cache/`. The generated `manifest.json` maps page titles to local files and is the right input if you later add a lexical or vector index.

The script is read-only against the wiki and writes local `.wiki` files for analysis. `wiki-cache/` is intentionally ignored by git because it is regenerated source material.

## Character Progress Tracking

Track the user's character progress across sessions. Before each interaction, scan `current-game.md` in the project root (or a progress log if the user keeps one) for the character's current state: name, level, build/playstyle, location, recent quests, and what they were last doing. When the session produces new milestones (level ups, quest completion, gear upgrades, build decisions), update or append to the progress record so the next session picks up context seamlessly.
