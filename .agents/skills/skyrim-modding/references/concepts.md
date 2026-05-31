# Skyrim/Bethesda Modding Concepts

## Runtime and Edition

Skyrim modding advice depends on runtime:

- Classic/LE: original 32-bit Skyrim, different toolchain and plugin ecosystem.
- SE `1.5.97`: pre-AE Special Edition runtime; many older DLL mods target this.
- AE `1.6.x`: current Steam Anniversary Edition runtime family; Steam current is `1.6.1170`.
- GOG AE: separate runtime, e.g. `1.6.1179`, often needs separate DLL support.
- VR: separate runtime and separate SKSEVR/CommonLib support.

Plugin-only mods often work across SE/AE if their masters exist. SKSE DLL mods are runtime-sensitive.

## Plugin Types

- `.esm`: master plugin. Loads early; other plugins can depend on it.
- `.esp`: standard plugin. Counts toward the classic 255 full-plugin limit unless ESL-flagged.
- `.esl`: light master. Uses ESL form ID space and does not count as a full plugin.
- ESL-flagged ESP: `.esp` file marked as light. Convenient for patches, but only safe if record count/form ID constraints are respected.

Do not compact form IDs in a plugin already used by saves or downstream patches unless you understand the consequences. Compacting changes form IDs and can break references.

## Records and Conflict Winners

Bethesda plugins are record databases. If two plugins edit the same record, the last-loaded plugin wins for that record or field depending on conflict structure. Asset overwrites are separate from plugin conflict winners.

Common records that matter for compatibility:

- `CELL`/`WRLD`: placed objects, lighting, water, image spaces, world edits.
- `NAVM`: navmesh; especially fragile and hard to merge manually.
- `NPC_`: stats, outfits, AI data, faces, packages, voice types.
- `LVLI`/`LVLN`/`LVSP`: leveled lists; often mergeable but still semantic.
- `QUST`/`SCEN`/`DIAL`/`INFO`: quests and dialogue; can be script- and condition-sensitive.
- `PERK`, `SPEL`, `MGEF`, `KYWD`, `RACE`, `FACT`, `PACK`, `OTFT`, `ARMO`, `WEAP`.

Red rows in xEdit are not automatically bad. Intended overwrites are normal. Bad conflicts are semantic: a later plugin unintentionally loses another mod's important change.

## Assets and File Priority

Loose files and BSAs determine assets: meshes, textures, scripts, interface files, animations, sounds, DLLs, INIs. In MO2, left-pane mod priority controls loose-file winners. Plugin order does not determine loose-file winner. In Vortex, deployment/rules determine file winners.

Important asset classes:

- `.nif` meshes: can conflict with texture paths, collision, physics, partition data.
- `.dds` textures: resolution/format/performance tradeoffs.
- `.pex` Papyrus bytecode: runtime script behavior.
- `.psc` Papyrus source: authoring/reference only unless compiled.
- SKSE `.dll`: native code; runtime- and dependency-sensitive.
- Animation/behavior files: may need Nemesis, FNIS, OAR, DAR, Pandora, or paired output.
- UI files: SWF/Scaleform and config files can conflict heavily.

## Saves and Persistence

Skyrim saves store far more than player position. They can retain script instances, quest states, aliases, placed references, enabled/disabled refs, inventories, and changed forms.

High-risk changes mid-save:

- Removing plugins with scripts, quests, placed refs, or persistent data.
- Renaming scripts, changing property types, removing properties without migration.
- Swapping major perk, magic, combat, economy, survival, follower, or quest overhauls.
- Compacting form IDs or changing plugin master relationships.

Safe/unavoidable advice: when in doubt, test on a new game and keep save backups.

## Curated Modlists

Curated lists are products, not piles of mods. They often contain pinned versions, custom patches, generated outputs, specific asset priorities, and non-obvious conflict rules. Generic advice like "sort with LOOT" or "update the mod" can break them.

For curated lists:

- Prefer list docs and maintainer notes.
- Make reversible changes in separate mods/plugins.
- Preserve load order unless the list's workflow says otherwise.
- Assume unsupported changes may void official support.
