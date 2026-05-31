# Skyrim Modding Tools

## Mod Managers

### Mod Organizer 2

MO2 uses a virtual filesystem so mods remain separated. Key concepts:

- Left pane: mod priority and loose-file conflict winners.
- Right pane: plugin load order.
- Profiles: separate enabled mods, plugin order, saves, and INIs depending on settings.
- Overwrite: generated files from tools; should be moved into named output mods.
- Stock Game: Wabbajack pattern that keeps a separate game copy isolated from Steam files.
- Root Builder: manages root-folder files such as ENB/Community Shaders/SKSE loader files in MO2 workflows.

MO2 is especially suitable for experimentation and Wabbajack lists because changes are isolated and reversible.

### Vortex

Vortex uses deployment and rules to place files into the game. Key concepts:

- Staging folder should usually be on the same drive as the game for hardlink deployment.
- File conflict rules and plugin groups can become stale or cyclic.
- Collections often rely on specific rules and installation choices.

Use Vortex guidance for Nexus collections unless the user's install is a Wabbajack/MO2 conversion.

### Wabbajack

Wabbajack installs reproducible modlists, commonly with MO2, Stock Game, and generated outputs. Updating a list may delete files not included in the manifest unless the list documents a protection mechanism. Do not assume custom mods survive updates.

## xEdit / SSEEdit

xEdit is the core inspection and patching tool for Bethesda plugin records. It can:

- View conflicts and conflict winners.
- Create patch plugins with `Copy as override into...`.
- Add masters and inspect dependencies.
- Run Quick Auto Clean when cleaning is appropriate.
- Check for errors.
- Compact form IDs and ESL-flag plugins when safe.
- Create ModGroups for The Method.

The xEdit docs caution that Creation Kit is the proper tool for many extensive mod-authoring tasks; xEdit is excellent for inspection, patching, cleaning, and precise record edits.

## Creation Kit

Creation Kit is Bethesda's official editor for forms, quests, scenes, dialogue, navmesh, cells, worldspaces, scripts, packages, and many authoring tasks. CK is often necessary for:

- Dialogue and scenes.
- Quest and alias setup.
- Navmesh work.
- Complex cell/worldspace authoring.
- Papyrus property assignment.

The official CK wiki may be unavailable or behind maintenance. If so, use archived docs, community CK references, UESP, and mod-author examples with caution.

## Papyrus

Papyrus is Skyrim's scripting language. Tooling includes the CK compiler, Champollion/Papyrus decompiler, Caprica, Papyrus logs, and IDE extensions. Remember:

- `.psc` source is not executed.
- `.pex` compiled bytecode is executed.
- Properties are bound in plugins/CK and can be save-baked.
- Logs can reveal runtime errors but are not a general performance profiler.

## SKSE and Native Plugins

SKSE extends Skyrim scripting and native functionality. Current public facts from SKSE docs:

- Steam AE current build: SKSE `2.2.6` for game `1.6.1170`.
- GOG AE has a separate `1.6.1179` build.
- SE `1.5.97` uses SKSE `2.0.20`.
- VR uses SKSEVR `2.0.12` for game `1.4.15`.
- Windows Store/Game Pass and Epic releases are not supported by SKSE.

Native plugin crash triage starts with SKSE logs, Address Library, runtime mismatch, missing VC++ redistributable, missing dependencies, and recently changed DLLs.

## CommonLibSSE-NG and Address Library

CommonLibSSE-NG is a C++ library for SKSE plugins. It supports SE, AE, and VR runtime targeting, including single DLLs that support multiple runtimes. It can be consumed through vcpkg or Conan and expects Windows/MSVC-oriented tooling for normal development.

Address Library lets DLL plugins resolve runtime addresses by ID rather than hard-coded addresses. End users need the correct Address Library variant for their runtime.

## Generated Output Tools

Generated outputs should usually be isolated as separate mods:

- Nemesis/FNIS/Pandora: behavior generation.
- OAR/DAR: animation replacement frameworks; OAR often avoids behavior generation but still has conditions/configs.
- BodySlide/Outfit Studio: body/outfit meshes.
- DynDOLOD/TexGen/xLODGen: distant object, terrain, and texture LOD.
- Synthesis/zEdit/Mutagen patchers: generated conflict patches.
- Wrye Bash: Bashed Patch, especially leveled-list merging in older/generic workflows.
- EasyNPC: facegen/NPC merge workflows.

Do not regenerate outputs for curated lists unless the list's docs say how.

## Shader/Graphics Tools

- ENB: root-level binaries/configs, preset-specific, can conflict with community shader setups.
- Community Shaders: SKSE/plugin-based graphics stack with feature add-ons.
- Reshade: post-processing injector.
- BethINI/INI edits: can affect display, memory, grass, shadows, LOD, and stability.

Graphics changes can affect performance and stability as much as visuals.
