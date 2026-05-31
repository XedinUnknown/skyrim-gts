#!/usr/bin/env python3
"""Config-driven entrypoint for the GTS item/recipe SQLite exporter."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
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
    config.setdefault("mod_metadata_dir", "cache/gts-mod-metadata-index")
    config.setdefault("dotnet", "/mnt/e/games/util/dotnet/dotnet")
    config.setdefault("max_seconds", 120)
    config.setdefault("exporter_project", "tools/GtsItemRecipeExporter/GtsItemRecipeExporter.csproj")
    return config


def abs_path(value: object) -> str:
    path = Path(str(value))
    return str(path if path.is_absolute() else ROOT / path)


def active_mods(profile_path: Path, mods_path: Path) -> list[dict[str, object]]:
    mods: list[dict[str, object]] = []
    modlist = profile_path / "modlist.txt"
    for priority, raw in enumerate(modlist.read_text(encoding="utf-8", errors="replace").splitlines()):
        if not raw.startswith("+"):
            continue
        name = raw[1:]
        if name.endswith("_separator"):
            continue
        path = mods_path / name
        if path.is_dir():
            mods.append({"priority": priority, "name": name, "path": path})
    return mods


def metadata_by_path(metadata_db: Path) -> dict[str, sqlite3.Row]:
    if not metadata_db.exists():
        return {}
    con = sqlite3.connect(metadata_db)
    con.row_factory = sqlite3.Row
    try:
        return {row["path"]: row for row in con.execute("select p.mod_index, p.path, p.modid, m.version from plugins p join mods m on m.id = p.mod_id")}
    finally:
        con.close()


def enrich_recipe_source_mods(index_db: Path, gts_path: Path, profile_path: Path, metadata_db: Path) -> None:
    con = sqlite3.connect(index_db)
    con.row_factory = sqlite3.Row
    try:
        plugins = {
            row["source_plugin"]
            for row in con.execute("select distinct source_plugin from recipes")
        }
        data_path = gts_path / "Game Root" / "Data"
        mods = active_mods(profile_path, gts_path / "mods")
        metadata = metadata_by_path(metadata_db)

        candidates: dict[str, list[dict[str, object]]] = {name.lower(): [] for name in plugins}
        for plugin in plugins:
            path = data_path / plugin
            if path.exists():
                candidates[plugin.lower()].append({
                    "plugin_name": plugin,
                    "provider_type": "data",
                    "priority": -1,
                    "mod_index": None,
                    "mod_path": str(data_path),
                    "modid": None,
                    "version": None,
                })

        for mod in mods:
            mod_path = Path(mod["path"])
            meta = metadata.get(str(mod_path))
            for child in mod_path.iterdir():
                if not child.is_file():
                    continue
                plugin = child.name
                if plugin.lower() not in candidates:
                    continue
                candidates[plugin.lower()].append({
                    "plugin_name": plugin,
                    "provider_type": "mod",
                    "priority": int(mod["priority"]),
                    "mod_index": meta["mod_index"] if meta else None,
                    "mod_path": str(mod_path),
                    "modid": meta["modid"] if meta else None,
                    "version": meta["version"] if meta else None,
                })

        con.executescript(
            """
            alter table recipes add column source_mod_name text;
            alter table recipes add column source_mod_index integer;
            alter table recipes add column source_mod_path text;
            alter table recipes add column source_modid integer;
            alter table recipes add column source_mod_version text;
            alter table recipes add column source_mod_provider_count integer not null default 0;
            create index idx_recipes_source_mod_index on recipes(source_mod_index);
            create index idx_recipes_source_modid on recipes(source_modid);
            create index idx_recipes_source_mod_path on recipes(source_mod_path);
            """
        )
        enriched = 0
        for matches in candidates.values():
            if not matches:
                continue
            winner = max(matches, key=lambda item: int(item["priority"]))
            con.execute(
                """
                update recipes
                set source_mod_name = ?,
                    source_mod_index = ?,
                    source_mod_path = ?,
                    source_modid = ?,
                    source_mod_version = ?,
                    source_mod_provider_count = ?
                where lower(source_plugin) = lower(?)
                """,
                (
                    Path(str(winner["mod_path"])).name,
                    winner["mod_index"],
                    winner["mod_path"],
                    winner["modid"],
                    winner["version"],
                    len(matches),
                    winner["plugin_name"],
                ),
            )
            enriched += con.total_changes
        con.execute(
            "insert or replace into manifest values (?, ?)",
            ("source_mod_plugins", str(len([m for m in candidates.values() if m]))),
        )
        con.commit()
        print(f"Enriched recipe source mod fields for {len([m for m in candidates.values() if m])} plugins in {index_db}")
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--contains")
    parser.add_argument("--out")
    parser.add_argument("--max-seconds", type=int)
    parser.add_argument("--", dest="separator", action="store_true")
    args, extra = parser.parse_known_args()

    config = load_config(Path(args.config))
    gts_path = os.environ.get("GTS_PATH", str(config["gts_path"]))
    profile_path = os.environ.get("GTS_PROFILE_PATH", str(config["profile_path"]))
    db_path = os.environ.get("GTS_DB", str(config["db_path"]))
    dotnet = os.environ.get("DOTNET", str(config["dotnet"]))
    out_path = args.out or abs_path(db_path)
    max_seconds = args.max_seconds if args.max_seconds is not None else int(config["max_seconds"])

    cmd = [
        abs_path(dotnet),
        "run",
        "--project",
        abs_path(config["exporter_project"]),
        "--",
        "--gts-path",
        abs_path(gts_path),
        "--profile",
        abs_path(profile_path),
        "--out",
        out_path,
        "--max-seconds",
        str(max_seconds),
    ]
    if args.contains:
        cmd += ["--contains", args.contains]
    cmd += extra
    result = subprocess.call(cmd, cwd=ROOT)
    if result != 0:
        return result

    enrich_recipe_source_mods(
        Path(out_path),
        Path(abs_path(gts_path)),
        Path(abs_path(profile_path)),
        Path(abs_path(db_path)),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
