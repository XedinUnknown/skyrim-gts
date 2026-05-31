---
name: gts-local-tools
description: Local project tooling for the skyrim-gts repository — SQLite DB schema (mods, plugins, plugins_fts FTS5), Makefile targets, Docker container setup, mod metadata indexing, Nexus API enrichment, opencode AI summarization, and item/recipe query pipeline. Use for questions about the repository's Python tools, cache structure, or build targets.
---

# GTS Local Tools

This skill documents the local `skyrim-gts` project's tooling. Use it when answering questions about the repository's Makefile, SQLite caches, indexing pipeline, summarization, or container setup.

## Container Setup

Tools run inside a Docker container. From the host:

```
docker compose run --rm tools make <target>
```

The container has Python 3, .NET SDK, and opencode. Source is mounted at `/workspace`, GTS install at `/gts` (read-only), and central cache at `/home/owner/.cache/skyrim-gts`.

`opencode` binary is mounted from the host at `/usr/local/bin/opencode`. Config and auth are mounted under `/tmp/home/.config/opencode` and `/tmp/home/.local/share/opencode` respectively.

## SQLite Schema (local DB: `cache/gts-index/gts.sqlite`)

### `mods`
Canonical per-Nexus-page data. One row per unique `cache_key`.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `cache_key` | TEXT UNIQUE | e.g. `nexus:skyrimspecialedition:<modid>` |
| `name` | TEXT | Canonical display name from Nexus |
| `nexus_name`, `nexus_author`, `nexus_version`, `nexus_updated`, `nexus_url` | TEXT | Nexus metadata |
| `nexus_summary` | TEXT | Short Nexus summary |
| `description_text` | TEXT | Cleaned mod description |
| `comments` | TEXT | Maintainer notes |
| `category`, `nexus_category` | TEXT | Raw MO2/Nexus category IDs from `meta.ini`/Nexus metadata |
| `version`, `newest_version` | TEXT | Version info |
| `mod_class` | TEXT | Classified category (gameplay, quest, texture, audio, animation, ui, visual_env, armor_weapon, npc, follower, fix, framework, other) |
| `ai_summary` | TEXT | AI-generated one-line summary |

### `plugins`
Per-plugin rows. One row per ESP/ESL plugin.

| Column | Type | Description |
|--------|------|-------------|
| `mod_index` | INTEGER PK | Load-order index |
| `mod_id` | INTEGER FK → mods(id) | Parent mod |
| `priority` | INTEGER | MO2 priority |
| `enabled` | INTEGER | 1 = enabled |
| `name` | TEXT | Plugin display name |
| `path` | TEXT | Absolute path to mod directory |
| `cache_key` | TEXT | References `mods.cache_key` |
| `repository` | TEXT | Nexus repository |
| `modid` | INTEGER | Nexus mod ID |
| `installation_file` | TEXT | Archive filename |
| `notes_text` | TEXT | Per-plugin user notes |

### `plugins_fts`
FTS5 virtual table for full-text search. Columns: `name`, `mod_name`, `comments`, `notes_text`, `description_text`, `nexus_summary`, `mod_class`, `ai_summary`. Populated from `plugins JOIN mods` during rebuild.

Shadow tables (`plugins_fts_content`, `plugins_fts_docsize`, `plugins_fts_idx`, `plugins_fts_data`, `plugins_fts_config`) are managed by SQLite.

### Other tables
- `ingredients`: craftable item ingredients with counts, EDIDs, source plugins.
- `recipes`: crafting recipes with workbenches, outputs, keyword conditions.
- `manifest`: key-value metadata about the build.

### Central cache (`mod-metadata-cache.sqlite`)
Path: `~/.cache/skyrim-gts/mod-metadata-cache.sqlite`.

`mod_cache` table mirrors the `mods` schema plus raw JSON fields (`raw_meta_json`, `raw_nexus_json`), timestamps (`local_meta_seen_at`, `nexus_seen_at`), and HTML variants (`notes_html`, `description_html`). It also stores raw category IDs (`category`, `nexus_category`) and computed `mod_class`, preserving `ai_summary` on metadata refresh. This is the canonical store; `gts.sqlite` is a project subset rebuilt from it.

## Makefile Targets

### Indexing
- `make mod-metadata` — Rebuild `gts.sqlite` from central cache + MO2 `modlist.txt`. Scans `meta.ini` files, upserts central cache, creates local subset.
- `make mod-metadata-enrich` — Same as above plus fetches Nexus API details (requires `NEXUS_API_KEY` in `.env`).
- `make clean-mod-metadata` — Remove stamp to force full rebuild next time.

### Search
- `make mod-search Q=<query>` — Full-text search across all mod/plugin descriptions, names, summaries, comments, and notes. Uses `plugins_fts`.
- `make search Q=<query>` — Search craftable item recipes by name.
- `make recipe Q="<item name>"` — Show crafting recipe for an item.
- `make chain Q="<item name>" DEPTH=4` — Show recipe tree (what ingredients come from).
- `make item Q="<item name>"` — Show item stats, recipe, source plugin, and likely mod.
- `make best MATERIALS="<materials>"` — Find craftable items from given materials.

### AI Summarization
- `make mod-summarize` — Summarize mod descriptions without AI summaries using opencode. Writes to `mods.ai_summary` and central cache.
- `make mod-summarize LIMIT=10` — Process only N mods.
- `make mod-summarize GLOBAL=1` — Summarize all mods in central cache (not just active game mods).
- `make mod-summarize MODIDS=45855,45574` — Summarize specific mods by Nexus modid.
- `make mod-summarize FORCE=1` — Regenerate active-game summaries even when `ai_summary` already exists.
- `make mod-summarize GLOBAL=1 FORCE=1` — Regenerate every summary in the central cache.
- `make mod-summarize TIMEOUT=120` — Set the per-batch opencode timeout in seconds.
- `make mod-summarize LOG=cache/gts-index/mod-summarize.log` — Write raw model output and debug details to a log file instead of the CLI.
- `make mod-summarize BATCH=20` — Set the number of mods per opencode batch.

Flags: `MODEL=<model>` (default `nvidia/nvidia/nemotron-3-nano-30b-a3b`), `LIMIT=<N>`, `GLOBAL=1`, `MODIDS=<ids>`, `FORCE=1`, `TIMEOUT=<seconds>`, `LOG=<path>`, `BATCH=<N>`.

Existing forced behavior: `MODIDS=<ids>` always re-summarizes the selected Nexus mod IDs, even when summaries already exist. Missing before this support: local active-game and global central-cache modes had no documented full regeneration switch and skipped existing `ai_summary` rows.

### Documentation
- `make game-readme` — Generate `docs/current-game.md` and `current-game.md` with all enabled mods, summaries, and search snippets.

## Summarization Pipeline (`tools/summarize_mods.py`)

Subcommands: `export`, `import`, `run`.

- `run` (default): export from DB → pipe through `opencode run` → parse output → write `ai_summary` to both `mods` table and central `mod_cache`.
- Local mode (no flags): reads `mods JOIN plugins WHERE enabled=1` for mods without summaries.
- `--global` / `-g`: reads from central `mod_cache` instead.
- `--modids <ids>`: only specified Nexus modids from central cache.
- Writes always go to central cache; local mode also writes to `mods.ai_summary`.
- Summaries are transported as one line per mod, but the model may encode meaningful internal newlines as literal `\n`; the importer decodes these back into stored multi-line Markdown.
- Failed, timed-out, or partially unparsed raw model output is written to `--log-file`/`LOG` (default `cache/gts-index/mod-summarize.log`) so batch runs do not spam the terminal.

OpenCode invocation uses `--model` (default `nvidia/nvidia/nemotron-3-nano-30b-a3b`) passed via `-m` flag.

## Indexing Pipeline (`tools/index_mod_metadata.py`)

1. Reads `modlist.txt` from MO2 profile for active mods.
2. Reads `meta.ini` from each mod directory (modid, version, description, comments, notes).
3. Upserts into central `mod_cache` (deduped by `cache_key`).
4. Optionally fetches Nexus API for enriched data.
5. Rebuilds local `gts.sqlite`:
   - `mods` table populated from unique `cache_key` rows in central cache.
   - `plugins` table populated with per-plugin data + `mod_id` FK.
   - `plugins_fts` populated from the join.
6. Populates `manifest` table with counts and timestamps.

## Recipe Extraction (`tools/gts_recipes_export.py`, `tools/query_item_recipes.py`)

Recipes are extracted from plugin `COBJ` records via a Mutagen-based .NET tool. The SQLite index is used for fast lookups:
- `ingredients`: ingredient counts, names, EDIDs, source plugins.
- `recipes`: workbench EDID, output item, keyword conditions.
- Cross-referenced with `plugins JOIN mods` for mod provenance.

## AGENTS.md

For project-level context (GTS install path, Wabbajack edition, safety rules), refer to `AGENTS.md` in the project root. This skill covers the tooling layer only.
