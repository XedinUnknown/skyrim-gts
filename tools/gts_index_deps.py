#!/usr/bin/env python3
"""Write a Make depfile for the active GTS recipe SQLite index."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "gts-index.config.json"


def load_config(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    config.setdefault("gts_path", "/mnt/e/games/GTSAV")
    config.setdefault("profile_path", str(Path(config["gts_path"]) / "profiles" / "Gate to Sovngarde Anniversary Edition Upgrade"))
    config.setdefault("db_path", "cache/gts-index/gts.sqlite")
    config.setdefault("index_dir", "cache/gts-item-recipe-index")
    config.setdefault("exporter_project", "tools/GtsItemRecipeExporter/GtsItemRecipeExporter.csproj")
    return config


def abs_path(value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else ROOT / path


def make_escape(path: Path) -> str:
    text = str(path)
    return text.replace("\\", "\\\\").replace(" ", "\\ ").replace("#", "\\#")


def dep_path(path: Path) -> Path:
    try:
        return path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return path


def sort_key(path: Path) -> str:
    return str(dep_path(path)).lower()


def enabled_mod_dirs(profile: Path, mods: Path) -> list[Path]:
    result: list[Path] = []
    for raw in (profile / "modlist.txt").read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.startswith("+"):
            continue
        name = raw[1:]
        if name.endswith("_separator"):
            continue
        path = mods / name
        if path.is_dir():
            result.append(path)
    return result


def active_plugins(profile: Path) -> set[str]:
    plugins = set()
    for raw in (profile / "plugins.txt").read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("*"):
            plugins.add(line[1:].lower())
    return plugins


def load_order(profile: Path, active: set[str], data: Path) -> list[str]:
    implicit = {"skyrim.esm", "update.esm", "dawnguard.esm", "hearthfires.esm", "dragonborn.esm"}
    result = []
    for raw in (profile / "loadorder.txt").read_text(encoding="utf-8", errors="replace").splitlines():
        plugin = raw.strip()
        if not plugin or plugin.startswith("#"):
            continue
        lower = plugin.lower()
        if lower in implicit or lower in active or (data / plugin).exists():
            result.append(plugin)
    return result


def plugin_sources(source_dirs: list[Path], desired: list[str]) -> list[Path]:
    wanted = {name.lower() for name in desired}
    found: dict[str, Path] = {}
    for directory in source_dirs:
        if not directory.is_dir():
            continue
        for child in directory.iterdir():
            if child.is_file() and child.name.lower() in wanted:
                found[child.name.lower()] = child
        if len(found) == len(wanted):
            break
    return [found[name.lower()] for name in desired if name.lower() in found]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--out", default="cache/gts-index.d")
    parser.add_argument("--target")
    args = parser.parse_args()

    config_path = abs_path(args.config)
    config = load_config(config_path)
    gts = abs_path(os.environ.get("GTS_PATH", str(config["gts_path"])))
    profile = abs_path(os.environ.get("GTS_PROFILE_PATH", str(config["profile_path"])))
    data = gts / "Game Root" / "Data"
    mods = gts / "mods"
    index_db = Path(args.target) if args.target else abs_path(os.environ.get("GTS_DB", str(config["db_path"])))
    exporter_project = abs_path(config["exporter_project"])

    active = active_plugins(profile)
    ordered = load_order(profile, active, data)
    sources = plugin_sources([data] + enabled_mod_dirs(profile, mods), ordered)
    prereqs = [
        config_path,
        ROOT / "tools" / "gts_recipes_export.py",
        ROOT / "tools" / "GtsItemRecipeExporter" / "Program.cs",
        exporter_project,
        profile / "plugins.txt",
        profile / "loadorder.txt",
        profile / "modlist.txt",
        *sources,
    ]

    depfile = abs_path(args.out)
    depfile.parent.mkdir(parents=True, exist_ok=True)
    target = make_escape(dep_path(index_db))
    ordered_prereqs = sorted(dict.fromkeys(prereqs), key=sort_key)
    body = (" " + chr(92) + "\n  ").join(make_escape(dep_path(path)) for path in ordered_prereqs)
    content = f"{target}: {body}\n"
    if depfile.exists() and depfile.read_text(encoding="utf-8") == content:
        print(f"Unchanged {depfile} with {len(sources)} plugin prerequisites")
        return
    depfile.write_text(content, encoding="utf-8")
    print(f"Wrote {depfile} with {len(sources)} plugin prerequisites")


if __name__ == "__main__":
    main()
