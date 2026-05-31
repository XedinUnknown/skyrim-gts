# Skyrim Modding Workflows

## Adding a Mod to an Existing Setup

1. Identify runtime, manager, and whether the setup is curated.
2. Check whether the mod or equivalent is already included.
3. Read the mod page: description, requirements, files, install instructions, incompatibilities, changelog, posts, bugs.
4. Check SKSE DLL runtime requirements and Address Library requirements.
5. Install into a reversible mod/profile or test copy.
6. Inspect plugin masters and missing masters before launching.
7. Inspect xEdit conflicts and file conflicts.
8. Create focused patches or output mods as needed.
9. Test on a new game or disposable save before using a real save.
10. Document the change so it can be repeated after updates.

## The Method, Adapted

The xEdit "Method" is a disciplined conflict-resolution workflow:

1. Start from a clean baseline.
2. Add one mod or one logical batch.
3. Run xEdit Very Quick Show Conflicts.
4. Decide which conflicts are intended and which need resolution.
5. Change load order only when appropriate and supported.
6. Create small focused patches for semantic conflicts.
7. Use ModGroups to hide intentional conflicts in iterative list-building workflows.
8. Repeat.

For curated modlists, do not literally reorder the list as a generic Method exercise. Use the principles for inspection and patching while preserving the curated order.

## Creating an xEdit Patch

1. Load affected plugins and their masters in xEdit.
2. Find the record where two or more mods need combined edits.
3. Right-click the desired base record and `Copy as override into...` a new patch plugin.
4. Use ESL-flagged ESP only if safe for the patch.
5. Drag/copy fields from source plugins so the patch preserves the intended combined result.
6. Ensure all source plugins are masters of the patch.
7. Save the patch.
8. Put the patch into a named mod/output folder.
9. Load after the mods it patches.
10. Re-check in xEdit.

Never assume all red conflicts need patching. Patch the semantic problem, not the color.

## Crash Triage

Classify timing first:

- Before launcher/main menu: missing DLL dependency, wrong SKSE/runtime, root files, ENB/CS, broken plugin header, missing masters.
- At main menu: missing masters, broken UI files, DLL load failure, bad INI, bad generated output.
- New game start: alternate start/startup quest issues, animation behavior, bad scripts, missing assets.
- Loading a save: save-baked scripts, removed plugin, changed form IDs, corrupted save, missing generated output.
- Entering a cell: bad mesh/NIF, broken navmesh, bad placed ref, lighting/water conflict, actor package issue.
- Performing an action: animation, magic effect, perk, script, item, menu, or DLL hook related to that action.

Collect:

- Crash log if available.
- SKSE logs.
- Engine Fixes logs.
- `plugins.txt` and `loadorder.txt`.
- Recent changes.
- Whether it reproduces on a new game.

## Papyrus Workflow

1. Identify owning plugin, quest, alias, object, magic effect, or active effect.
2. Locate source `.psc` if available and compiled `.pex` actually deployed.
3. Check properties and attached scripts in CK/xEdit.
4. Avoid changing script names or property types without migration.
5. Prefer events over polling.
6. Be cautious with cloak effects, frequent `OnUpdate`, and scripts on many objects.
7. Test on new game for structural changes.
8. Use Papyrus logs to find errors, not as proof of all problems.

## SKSE/CommonLibSSE-NG Workflow

1. Confirm game runtime and SKSE version.
2. Confirm Address Library variant and version.
3. Check whether the plugin targets SE, AE, VR, GOG, or multi-runtime.
4. Use CommonLibSSE-NG relocation/address abstractions where possible.
5. Build with the expected Windows toolchain unless the project explicitly supports cross-compilation.
6. Package DLL under `Data/SKSE/Plugins` with any INI/JSON config and required dependencies.
7. Test startup with only required dependencies before testing in a full list.

## Curated List Customization

1. Read the list's customization rules.
2. Back up profile, saves, and relevant text files.
3. Add mods in separate separators/output mods.
4. Preserve curated plugin order unless documented otherwise.
5. Avoid updating included mods.
6. Check list-specific compatibility notes before generic advice.
7. Expect official support to stop once modified.
8. For Wabbajack, understand update deletion/protection rules before adding files.
