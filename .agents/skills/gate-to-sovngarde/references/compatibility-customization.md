# Compatibility And Customization

GTS is a curated integrated list. Customization is possible, but it can void support and break list assumptions.

## First Response To Mod Additions

When asked if a mod can be added:

1. Check the live GTS `Mod Compatibility` wiki page.
2. Check the installed list or Load Order Library to see if the mod is already present, pinned, forked, patched, or functionally replaced.
3. Identify install edition: Vortex collection, Wabbajack AE, or Wabbajack non-AE.
4. Read the mod page, requirements, posts/bugs, changelog, install instructions, and incompatibilities.
5. Inspect runtime-sensitive requirements: SKSE DLL version, Address Library, PapyrusUtil/JContainers/MCM Helper, animation frameworks, Community Shaders/ENB, UI frameworks, and generated outputs.
6. Inspect xEdit conflicts for quests, cells/worldspaces, NPCs, factions, packages, perks, races, keywords, leveled lists, outfits, navmesh, weather, lighting, water, and scripts.
7. Inspect assets for interface files, scripts, meshes, animations/behavior, SKSE plugins, INIs, sounds, shaders, and loose-file/BSA priority.
8. Prefer a separate add-on mod plus focused patch plugin over editing GTS plugins or included mods.
9. State if a new game is needed and whether support is likely voided.

## Known Public Compatibility Examples

Re-check the live wiki before relying on these examples. At research time, the wiki listed:

- Compatible out of the box examples: Wheeler with Wheeler CTD Fix recommended, QuickLoot, Mark of Akatosh clock overlay, Deadly Spell Impacts v87, Strange Runes likely needing new save, SmoothCam and a preset, several audio mods, Centered Blue Palace Throne v87 requiring new save, Shadows of Skyrim, Clean Save Reloader v87, and Pronouns best on new save.
- Needs conflict resolving: Deadly Spell Impacts: Mysticism Compat v87, with a noted Scion conflict resolved by loading before Scion.
- Needs additional patch: Remember Lockpick Angle v87 needs the Locksmith Addon from Hand to Hand's files.
- Incompatible: Ordinator.

Do not turn this summary into blanket approval. Version-specific notes matter.

## Wabbajack Customization

- Wabbajack conversion README states support for modified installations will not be provided.
- Wabbajack updates delete files not part of the list unless protected. The README says to prefix custom mod names with `[NoDelete]` to keep them during updates.
- Do not use the MO2 sort button. The README explicitly warns against it.
- Do not drag/drop mods or plugins unless you know exactly what you are doing.
- If the user broke order, the README says backups of original `modlist.txt` and `loadorder.txt` are included and can be restored with MO2's Restore Backup button, but changed mod/plugin names can make restore fail.
- Use Stock Game and Root Builder concepts when explaining file placement.

## Vortex Customization

- Official GTS wiki workflows often assume Vortex collection rules.
- For unresolved conflicts/cycles, apply collection rules from the exact `Gate To Sovngarde` collection entry first.
- Remove non-collection mods while diagnosing vanilla GTS install problems.
- Only modify GTS once the base collection works.
- If rules are broken, the wiki may instruct clearing rules and applying collection rules again; follow the current page.

## xEdit Patch Guidance

- Load the GTS order exactly as installed.
- Create a new focused patch plugin loaded after affected masters.
- Add required masters to the patch; do not directly edit curated GTS plugins.
- Prefer ESL-flagged ESP only when records and compacting constraints are safe. Do not compact existing list plugins.
- Keep handmade patches in a separate mod/output folder.
- Document every intentional winner, especially when overriding GTS patches.
- Check scripts and quest aliases carefully; many changes are save-baked or new-game-only.

## Generated Outputs

Do not rerun generated-output tools reflexively. GTS includes tuned outputs.

- Nemesis: use when the GTS wiki or crash/log evidence points to animation graph issues.
- DynDOLOD/Occlusion/xLODGen/TexGen: only regenerate if following a documented workflow for a known worldspace/LOD change.
- Synthesis/Bashed patches/EasyNPC/Bodyslide: use separate output mods and document load/file priority.
- Community Shaders/ENB-like changes: preserve GTS defaults unless the user understands the performance/visual tradeoff.

## Support Language

Use explicit confidence labels:

- `Documented by GTS wiki`: cite page/source.
- `Documented by Wabbajack conversion`: cite README/metadata.
- `Likely safe but unverified`: explain why and what to test.
- `Needs patch/testing`: name the conflict area.
- `Unsupported/incompatible`: explain whether this comes from GTS docs or from observed conflicts.
