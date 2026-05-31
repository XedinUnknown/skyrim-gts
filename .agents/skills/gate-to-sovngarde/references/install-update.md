# Installation And Updates

Separate official Nexus/Vortex GTS from Wabbajack/MO2 conversions before giving steps.

## Common Requirements

- Use the current Steam Skyrim Special Edition/Anniversary runtime unless the docs say otherwise.
- Wabbajack conversion README names Skyrim SE `1.6.1170` as the supported Steam runtime.
- GOG can work only through documented compatibility steps; do not assume it works out of the box.
- Use English game language.
- Start a new game; old saves are not compatible with installing GTS.
- Install the latest Microsoft Visual C++ Redistributable.
- Use a clean Skyrim install. Remove old modded game files, stale INIs, and SKSE folders where the relevant install guide instructs.
- If the user owns Anniversary Edition Upgrade, launch Skyrim through Steam and download owned Creation Club content before installing GTS. Do not tab out during CC download if following the Wabbajack README guidance.
- Use enough disk space and preferably an SSD.

## Official Nexus/Vortex Collection

The GTS wiki install guide targets Vortex.

- Nexus Premium is optional for Nexus collections, but without it the user must manually click through many downloads. The Wabbajack conversion README is stricter and says support for manual non-Premium Wabbajack installs is not offered.
- Vortex should use a clean profile for the collection.
- Enable profile management and disable Vortex FNIS integration where the GTS quick install says so.
- Mod staging should be on the same drive as Skyrim, with hardlink deployment.
- If the user owns AE Upgrade, verify the Creation Club group has the expected owned plugins and install the recommended/optional GTS files when prompted.
- During collection install, ignore temporary missing dependency/file conflict warnings until the install finishes unless the guide says otherwise.
- Avoid touching Vortex while installing. If Vortex freezes, let it finish.
- For FOMOD popups during install, the wiki says to finish specific listed installers with default options and cancel others so Vortex can resume later.

## Wabbajack/MO2 Conversion

The community Wabbajack conversion is separate from the official Nexus collection and is maintained by FlimsyParking.

- The repo currently advertises two standalone versions: Anniversary Edition Upgrade and Non-AE. Pick the one matching AE Upgrade ownership.
- Wabbajack metadata version observed: `0.104.0` for both AE and non-AE at research time.
- Metadata observed AE sizes: 2153 archives, archive size about 83.6 GB, installed files about 133.3 GB, total about 216.8 GB.
- Metadata observed non-AE sizes: 1903 archives, archive size about 78.2 GB, installed files about 127.5 GB, total about 205.7 GB.
- The README recommends Nexus Premium and says support for manual Wabbajack installs without Premium is not offered.
- Install outside `Program Files`, Windows system folders, Desktop, Downloads, and other protected locations.
- Keep the install folder path short to avoid path length issues.
- Run the vanilla Skyrim launcher through Steam at least once before installing; if AE content is owned, download it first.
- Start Steam before launching GTS through MO2.
- Launch through `ModOrganizer.exe` and the `Gate to Sovngarde` executable/dropdown entry.
- The MO2 message `The application must run to completion because its output is required` is not an error; do not press Unlock.
- The Wabbajack version uses Stock Game, so it has a separate game copy and should not touch the Steam Skyrim install.
- The Wabbajack version uses Root Builder.
- Do not use MO2's sort button. Do not drag/drop mods or plugins unless intentionally customizing with knowledge of consequences.
- Included mods may have older pinned versions intentionally; do not update them just because Nexus shows updates.

## Updates

For Vortex GTS:

- Check the GTS changelog first for new-game requirements.
- If any save-incompatible update occurred between the installed and target versions, updating on the old save is not safe.
- Updating onto the same profile is documented by the wiki.
- If Vortex asks whether to remove old mods from the older revision, the wiki says to remove all.

For Wabbajack GTS:

- Check both the Wabbajack conversion changelog and original GTS changelog for every included collection version between old and new.
- Back up saves before updating, or start a new game if required.
- Updating is like installing: select the same path and tick `Overwrite Existing Modlist` per README guidance.
- Wabbajack updates can delete files not part of the list. For user-added mods the README says to prefix mod names with `[NoDelete]` to preserve them during updates.

## Wide/Resolution Notes

- Wabbajack README says GTS now uses Auto Resolution, but if resolution is wrong, open MO2's built-in INI editor, check `skyrimprefs.ini`, set `iSize H` and `iSize W`, and press Save even if unchanged.
- High-resolution monitors may need Windows resolution lowered before install/start if playing at a lower resolution.
- Wide/ultrawide users should follow the GTS wiki's `Wide and Ultrawide` page.
