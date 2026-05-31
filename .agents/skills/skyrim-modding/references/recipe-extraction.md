# Recipe Extraction

Use this when the user asks for exact crafting requirements, recipe visibility, workbench requirements, or all craftable items in a Skyrim SE/AE setup or curated modlist.

## Key Point

Crafting recipes are plugin data. Wiki pages and mod descriptions are often incomplete. The authoritative source is the winning `COBJ` records in the user's actual installed plugin load order.

For the local `skyrim-gts` project, do not start item/recipe questions by recursively searching the Wabbajack install directory. This repository already has generated lookup artifacts and Make targets. Project Make commands are container commands: plain `make ...` in these instructions means run the target inside the tools container, or from the host use `docker compose run --rm tools make ...`. Start with the fast indexed sources, then escalate only if the index is missing or insufficient:

1. For a complete item answer, start with `make item Q="item name"`. It prints fuzzy recipe matches, stats, ingredients, source plugin, and likely active mod metadata.
2. Search `current-game.md` at the repository root only when you need extra human-readable mod context or to cross-check likely provenance.
3. Use the narrower Makefile interface for follow-up item/recipe facts: `make search Q="item name"`, `make recipe Q="item name"`, or `make chain Q="item name" DEPTH=4`.
4. If `make` says the recipe DB is stale or missing, run `make index` rather than hand-searching plugin folders.
5. Only use broad filesystem/plugin inspection after the generated index fails to answer the question or when exact non-recipe record data is needed.

Avoid tangents after a successful `make item` result. If the lookup returns fuzzy matches, answer from those matches with a clear caveat such as "I found no exact item named X; the closest indexed match is Y." Do not inspect SQLite schema, run ad-hoc Python database queries, create temporary Mutagen readers, or search plugin files just to improve confidence. Escalate beyond `make item` only when the user explicitly asks for deep record verification, the Make target reports no useful matches, or the question asks for data the Make output does not include.

For questions like "what mod does this item come from, what are its stats, and show how you found it," report both trails: the human-readable mod trail from `current-game.md`/metadata, and the authoritative item trail from `make recipe`/the recipe SQLite DB. Be explicit about which facts come from descriptions versus plugin records.

`COBJ` records include:

- `CNAM`: created item.
- `BNAM`: workbench keyword, such as forge, tanning rack, cooking pot, or custom crafting station.
- `CNTO`: required components and counts.
- `NAM1`: output count.
- `CTDA`: conditions controlling recipe visibility, perks, quests, globals, keywords, DLC state, or other requirements.

If an item does not appear in-game, common reasons are missing ingredients, wrong workbench, unmet `CTDA` conditions, missing perk/book/quest/global, hidden recipes, disabled plugin, or a different mod winning/conflicting.

## Preferred Authoritative Workflow: xEdit

Use xEdit/SSEEdit when available because it understands load-order winning overrides, masters, ESL compacted form IDs, localized strings, and conditions better than a lightweight parser.

1. Launch xEdit through the same manager/profile as the user, e.g. MO2 or Vortex.
2. Load the full active plugin list or the suspected plugin plus masters.
3. Filter for `Constructible Object (COBJ)` records.
4. Search by created item name/EDID, recipe EDID, workbench keyword, or ingredient.
5. Inspect the winning override of the recipe.
6. Expand `Items` for ingredients, `Created Object` for output, `Workbench Keyword` for station, and `Conditions` for visibility requirements.
7. Export rows with an xEdit script if a complete table is needed.

For curated lists, do not modify the recipe while inspecting. If a patch is needed, create a separate patch plugin.

## Authoritative CLI Options

There are two practical CLI-capable routes.

### xEdit command line plus script

xEdit documents command-line switches and Pascal-like scripting. Relevant switches include:

- `-sse` or a renamed `SSEEdit.exe`/`SSEEdit64.exe` for Skyrim Special Edition mode.
- `-script:"ScriptName.pas"` to run an xEdit script.
- `-autoload` to load active modules automatically.
- `-moprofile:<profile name>` to use a Mod Organizer profile.
- `-D:<path>` to specify a Data directory.
- `-P:<path\plugins.txt>` to specify a custom plugins file.
- `-I:<path>` to specify game INI path.
- `-S:<path>` to specify the scripts directory.
- `-R:<path\log.txt>` to specify a log path.

For this project, a likely shape is:

```powershell
SSEEdit64.exe -sse -autoload -moprofile:"Gate to Sovngarde Anniversary Edition Upgrade" -script:"ExportItemRecipeIndex.pas"
```

If running outside MO2 or against a Wabbajack Stock Game copy, use explicit paths:

```powershell
SSEEdit64.exe -sse -autoload -D:"E:\games\GTSAV\Game Root\Data\" -P:"E:\games\GTSAV\profiles\Gate to Sovngarde Anniversary Edition Upgrade\plugins.txt" -script:"ExportItemRecipeIndex.pas"
```

Use xEdit for the final authoritative export because scripts can call `WinningOverride`, `LinksTo`, `GetElementEditValues`, `GetLoadOrderFormID`, and condition display helpers from xEdit's decoded record model.

### Mutagen or Synthesis CLI

Mutagen is a .NET library for analyzing, creating, and manipulating Bethesda plugins. Its docs show load-order iteration such as:

```csharp
using var env = GameEnvironment.Typical.Skyrim(SkyrimRelease.SkyrimSE);
foreach (var weaponEditorId in env.LoadOrder.PriorityOrder.Weapon().WinningOverrides()
    .Select(weap => weap.EditorID))
{
    Console.WriteLine(weaponEditorId);
}
```

Synthesis is a Mutagen-based patcher pipeline with a documented CLI. It can run a pipeline with explicit `--DataFolderPath` and `--LoadOrderFilePath`.

Use Mutagen/Synthesis when you want a maintainable cross-platform exporter in C# with strongly typed records. Use xEdit when you want parity with what modders inspect manually and the most mature decoded condition/display behavior.

For large MO2/Wabbajack profiles, avoid repeatedly searching every mod directory for every plugin. First build a plugin-name-to-path index from the active MO2 `modlist.txt`, then stage active plugins into a temporary Data folder and run Mutagen over that staged folder. Put a runtime limit and benchmark logging on exporter runs.

For query workflows, export to SQLite rather than only JSON/CSV. A useful schema has:

- `manifest`: generation time, profile path, staged Data path, plugin count, recipe count, timings, exporter version.
- `recipes`: recipe form ID, recipe EDID, source plugin, created item form ID/name/EDID/type/value/weight/count, workbench keyword, condition count.
- `ingredients`: recipe ID, ingredient form ID/name/EDID/type/value/weight/count.

SQLite supports fast exact and fuzzy queries such as item recipe lookup, reverse ingredient lookup, recursive resource-chain expansion, and economic ranking. Treat economic ranking carefully: vanilla item `Value` is a base value, not guaranteed vendor sale value, and condition-gated/quest recipes may not be actually craftable by the current character.

In a project that provides a Make workflow, prefer simple user-facing targets over long commands:

```bash
make index
make item Q="Black Leather Backpack"
make search Q=backpack
make recipe Q="Leather Backpack"
make chain Q="Leather Backpack" DEPTH=4
make best MATERIALS="leather strips"
```

If the project uses Make dependency files, regenerate the depfile from the active MO2 profile whenever the active mod/plugin set changes. The depfile should make the SQLite DB depend on project config, exporter/query code, `plugins.txt`, `loadorder.txt`, `modlist.txt`, and each active plugin file discovered in MO2 load order. Then `make index` can skip work when the DB is current and rebuild when relevant plugin inputs change.

## Bundled Offline Parser

This skill includes `scripts/extract_cobj_recipes.py`. It parses plugin files directly and emits JSON/CSV recipe tables.

Example:

```bash
python3 .agents/skills/skyrim-modding/scripts/extract_cobj_recipes.py \
  "/path/to/Skyrim.esm" \
  "/path/to/Update.esm" \
  "/path/to/MyMod.esp" \
  --contains backpack \
  --json /tmp/recipes-backpack.json \
  --csv /tmp/recipes-backpack.csv
```

Use plugins in load order. Include masters and plugins that define relevant item names; otherwise ingredient or output names may be unresolved.

For a full list:

```bash
python3 .agents/skills/skyrim-modding/scripts/extract_cobj_recipes.py /path/to/*.esm /path/to/*.esp --json /tmp/recipes.json --csv /tmp/recipes.csv
```

Prefer explicitly ordered plugin paths over shell globs for curated lists. Shell glob order is alphabetical, not load order.

## Parser Limitations

The bundled parser is intentionally lightweight.

- It reads `COBJ`, `EDID`, `FULL`, `CNAM`, `BNAM`, `NAM1`, `CNTO`, and counts `CTDA` conditions.
- It does not fully evaluate `CTDA` conditions.
- It does not fully model xEdit conflict winners across overrides.
- It may not resolve all form IDs in complex ESL/light-plugin setups.
- Localized strings may require string files, so some names may be unavailable while EDIDs/form IDs still appear.
- It cannot see recipes injected or changed at runtime by SKSE/Papyrus.

Use parser output as a fast searchable index. Use xEdit to confirm any recipe that is missing, condition-gated, overridden, or important to patch.

## Building A Searchable Recipe Reference

For a modlist or project, generate artifacts under a local ignored cache, for example:

```text
recipe-cache/recipes.json
recipe-cache/recipes.csv
recipe-cache/manifest.json
```

Index fields useful for search:

- Created item name, EDID, form ID, and type.
- Recipe EDID and source plugin.
- Workbench keyword.
- Ingredients with counts, names, EDIDs, form IDs, and source plugins.
- Condition count and raw condition summary if using xEdit export.

For future MCP/vector search, keep JSON as source of truth and build chunks like:

```text
Recipe: <created_name> (<created_edid>)
Workbench: <workbench_edid>
Output: <count>
Ingredients: <count>x <ingredient>; ...
Conditions: <summary>
Source: <plugin> <formid>
```

Vector search is useful for fuzzy user queries like "backpack carry weight". Exact search over JSON/CSV is still better for form IDs, EDIDs, workbenches, and ingredient counts.
