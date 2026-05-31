# Troubleshooting

Start by identifying manager and edition: Vortex collection, Wabbajack AE, Wabbajack non-AE, GOG compatibility, or modified install.

## Intended Mechanics That Look Like Bugs

- No compass, sneak eye, or player map marker: intended until Wayfarer perks unlock them, unless Story Mode is active.
- Menus do not pause: intended Skyrim Souls behavior; can be adjusted through collection tweaks.
- Containers have weight limits: intended.
- Gear temper level degrades: intended; items do not fully break.
- Fast travel requires travel packs by default.
- Survival Mode requires sleep to level up and affects hunger/exhaustion/cold.
- Starting room warning about optional files usually means AE Upgrade optional/recommended files are missing.
- Potion hotkeys have defaults and can fail if the related setup is wrong; check GTS wiki before generic hotkey advice.

## Vortex Collection Warnings

Use exact GTS wiki steps, not generic Vortex/LOOT advice.

- Missing masters: check disabled plugins, missing AE/CC content, or optional files. Missing masters can cause startup crashes.
- Redundant mods: review duplicate or empty deployed mods according to wiki guidance.
- File conflicts/cycles: apply collection rules from the `Gate To Sovngarde` collection entry, restart Vortex, then follow the wiki's cycle resolution guidance if needed.
- Plugin cyclic rules: the wiki documents exact group cleanup/reset and specific Dynamic LOD and Late Fixes and Changes group membership for certain versions. Do not improvise broad group changes.
- Failed dependency install: check Nexus rate limits, damaged archive, disk space/quota/read-only folders, antivirus, Nexus outage, deleted mods, or browser ad blockers.
- Failed to parse plugin: reinstall the mod that owns the plugin.
- Loose files may not get loaded: wiki says this warning is irrelevant to Skyrim SE and can be dismissed.

## Launch, SKSE, DLL, And Startup Crashes

- Crash logs are usually in `Documents\My Games\Skyrim Special Edition\SKSE\` and named like `crash-YYYY-MM-DD-HH-MM-SS.log`.
- Crash before main menu or during startup is often missing masters or disabled plugins.
- Crash log references to early SKSE DLLs such as `BladeAndBlunt.dll`, `DragonWar.dll`, or `Journeyman.dll` can indicate that the matching plugin is disabled.
- If crash log mentions `BladeAndBlunt.dll` and `BladeAndBlunt.esp` cannot be found, check that `plugins.txt` has all plugins enabled. Vortex may need disable/enable/restart cycles to regenerate it.
- If crashing after pressing New Game with `PlayerCharacter`, `QueuedPlayer`, `skeleton.nif`, or missing BSA archive symptoms, run the vanilla Skyrim launcher from Steam, change/toggle a launcher option to regenerate INIs, close it, and launch through the manager again.
- SKSE/DLL load warnings: install/repair current Visual C++ Redistributable, check antivirus/Windows Defender/Smart App Control quarantine, verify correct Steam/GOG runtime, and reinstall the affected mod, SKSE, Address Library, and Engine Fixes components if documented.
- Engine Fixes SKSE64 Preloader must have the correct deployment/type in Vortex; the wiki names `Engine Injector` for Vortex.
- Non-Steam or pirated versions are unsupported. GOG requires the GOG Compatibility guide.

## In-Game Crashes

- `BShkbAnimationGraph` in crash logs suggests an animation graph issue; the wiki points to running Nemesis.
- Crash while loading a save can be a modded Skyrim limitation, especially with saves made during high script load or after dirty loading.
- For unknown crashes, Phostwood's crash analyzer may help, but GTS Discord/help channels and source logs are still important.

## Safe Saving

Recommended save hygiene from the wiki:

- Avoid saving during heavy script load: large combat, Civil War battles, scenes, quest transitions, boss events.
- Avoid saving immediately after a loading screen; wait at least 30 seconds.
- Disable autosaves if they cause instability; BethINI Pie can manage autosave settings.
- Do not remove mods from an active save unless the author explicitly says it is safe. Assume removal is unsafe.
- If adding a mod, make and back up a save first.
- Avoid repeated dirty loading in one game session. The safest load is the first load after launching the game.
- Too many save files can cause problems; clean old saves periodically.
- Resaver can clean unattached instances/undefined elements but is not a general magic fix; use carefully.

## Performance

- GTS is optimized by default, but weaker hardware or high framerates may need tweaks.
- BethINI Pie can apply recommended tweaks and presets. Download manually, not through mod manager link.
- SSE Display Tweaks handles VSync and FPS cap. Config is commonly under `Data\SKSE\plugins\SSEDisplayTweaks.ini`; custom settings can go in `SSEDisplayTweaks_Custom.ini` to survive GTS updates.
- To enable VSync set `EnableVSync=true`; to cap FPS set `FramerateLimit`; for tearing set `AllowTearing=false`.
- Community Shaders includes upscaling and should not usually be fully disabled. Expensive effects include SSGI, Sub-Surface Scattering, Skylighting, and Grass Collision.
- Frame Generation is disabled by default in Wabbajack README notes; enable only if hardware/display conditions make sense and check known UI issues.
- Set a Windows pagefile to system-managed size on a fast drive if stability is poor. Linux equivalent is swap or ZRAM.
- Low VRAM users may downgrade Skyland AIO from 2K to 1K, but follow the wiki FOMOD/file-copy/reversal steps exactly.
- VRAMr can optimize textures but needs substantial output space and its manual should be read.
- Faster HDT-SMP performance preset and AVX2 option can help if CPU supports AVX2. Wabbajack README says GTS ships compatibility-focused AVX by default.
- Papyrus Tweaks `bSpeedUpNativeCalls` is experimental; back up saves before enabling.

## Resolution

- Wabbajack README says Auto Resolution reduced most issues.
- For Wabbajack/MO2 resolution problems, use MO2 built-in INI editor, open `skyrimprefs.ini`, verify `iSize H`/`iSize W`, and press Save even if unchanged.
- Fullscreen INI expectations may not apply because GTS Display Tweaks/Frame Generation configuration can make `Fullscreen=1` nonfunctional.
- For wide/ultrawide, use the GTS wiki `Wide and Ultrawide` page.
