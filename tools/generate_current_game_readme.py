#!/usr/bin/env python3
"""Generate a current-game overview from the active mod metadata index."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "gts-index.config.json"


SECTIONS = [
    ("Core GTS And List Patches", ["Gate to Sovngarde", "GTS", "JaySerpa", "patch", "specific patches"]),
    ("Progression, Perks, Races, Standing Stones", ["perk", "Adamant", "Hand to Hand", "Aetherius", "Mundus", "Pilgrim", "standing stone", "race overhaul"]),
    ("Magic, Shouts, Religion, Artifacts", ["Mysticism", "magic", "spell", "Thaumaturgy", "Artificer", "Pilgrim", "Stormcrown", "shout", "artifact"]),
    ("Combat, Enemies, Injuries", ["combat", "Blade and Blunt", "Lawless", "enemy", "injury", "wounds", "dragon", "bandit"]),
    ("Survival, Needs, Camping, Travel", ["survival", "Campfire", "Journeyman", "fast travel", "needs", "sleep", "cold", "camp"]),
    ("Crafting, Economy, Loot, Items", ["craft", "recipe", "Smithing", "economy", "loot", "container", "backpack", "Gourmet", "Apothecary"]),
    ("Quests, New Lands, Followers", ["quest", "Wyrmstooth", "Bruma", "Vigilant", "follower", "Lucien", "Auri", "Remiel", "3DNPC"]),
    ("NPCs, AI, Dialogue, Reputation", ["dialogue", "AI Overhaul", "NPC", "reputation", "relationship", "faction", "conversation"]),
    ("World, Cities, Dungeons, Encounters", ["city", "town", "dungeon", "encounter", "world", "landscape", "road", "location", "interior"]),
    ("Visuals, Audio, UI, Animation", ["texture", "mesh", "animation", "sound", "music", "UI", "camera", "map", "Community Shaders", "DynDOLOD"]),
    ("Fixes, SKSE, Frameworks, Utilities", ["SKSE", "Address Library", "fix", "framework", "utility", "PapyrusUtil", "Base Object Swapper", "SPID", "KID"]),
]

DISABLE_TERMS = ["disabled", "disable", "removed", "obsolete", "hidden", "overwritten", "overwrite", "replaced", "conflict"]

CLASS_IMPORTANCE = {
    "gameplay": "full",
    "quest": "full",
    "visual_env": "brief",
    "texture": "brief",
    "audio": "brief",
    "ui": "brief",
    "animation": "brief",
    "armor_weapon": "medium",
    "npc": "brief",
    "follower": "medium",
    "fix": "brief",
    "framework": "brief",
    "other": "medium",
}

CLASS_LABELS = {
    "gameplay": "Gameplay, Combat, Magic, Perks",
    "quest": "Quests, New Lands, Dungeons",
    "visual_env": "Visual Environment, Weather, Lighting",
    "texture": "Texture, Mesh, Visual Replacers",
    "audio": "Audio, Sound, Music",
    "ui": "UI, Interface, HUD",
    "animation": "Animations",
    "armor_weapon": "Armor, Weapons, Equipment",
    "npc": "NPCs, Faces, Bodies",
    "follower": "Followers, Companions",
    "fix": "Fixes, Patches, Bugfixes",
    "framework": "Frameworks, SKSE Plugins, Utilities",
    "other": "Other Mods",
}


def strip_urls(text: str) -> str:
    return re.sub(r"https?://\S+", "", text)


def full_description(row: sqlite3.Row) -> str:
    text = row["description_text"] or row["nexus_summary"] or row["comments"] or row["notes_text"] or ""
    return strip_urls(text)


def load_config(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    config.setdefault("mod_metadata_dir", "cache/gts-mod-metadata-index")
    config.setdefault("index_dir", "cache/gts-item-recipe-index")
    config.setdefault("db_path", "cache/gts-index/gts.sqlite")
    return config


def abs_path(value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else ROOT / path


def project_db_path(config: dict[str, object]) -> Path:
    return abs_path(os.environ.get("GTS_DB", str(config.get("db_path", "cache/gts-index/gts.sqlite"))))


def connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def clean(text: str | None, limit: int = 700) -> str:
    if not text:
        return ""
    text = text.replace("\ufeff", "").replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip(' "')
    text = strip_urls(text)
    if len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


def one_line(row: sqlite3.Row, limit: int = 360) -> str:
    text = row["nexus_summary"] or row["description_text"] or row["comments"] or row["notes_text"] or ""
    return clean(text, limit)


def append_summary(lines: list[str], text: str) -> None:
    for line in text.splitlines() or [text]:
        if line.strip():
            lines.append(f"  - {line}")
        else:
            lines.append("  -")


MODS_COLS = "p.*, m.name as mod_name, m.nexus_summary, m.description_text, m.comments, m.nexus_name, m.nexus_author, m.nexus_version, m.nexus_updated, m.nexus_url, m.version, m.newest_version, m.mod_class, m.ai_summary"

def all_mods(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return con.execute(f"select {MODS_COLS} from plugins p join mods m on m.id = p.mod_id order by p.priority").fetchall()


def search_rows(con: sqlite3.Connection, terms: list[str], limit: int = 24) -> list[sqlite3.Row]:
    seen: set[int] = set()
    rows: list[sqlite3.Row] = []
    for term in terms:
        escaped = term.replace('"', '""')
        query = f'"{escaped}"' if " " in term else escaped
        try:
            found = con.execute(
                f"""
                select {MODS_COLS} from plugins_fts
                join plugins p on p.mod_index = plugins_fts.rowid
                join mods m on m.id = p.mod_id
                where plugins_fts match ?
                order by rank
                limit ?
                """,
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            continue
        for row in found:
            if row["mod_index"] in seen:
                continue
            seen.add(row["mod_index"])
            rows.append(row)
            if len(rows) >= limit:
                return rows
    return rows


def recipe_stats(recipe_db: Path) -> dict[str, object]:
    if not recipe_db.exists():
        return {}
    con = connect(recipe_db)
    stats = {
        "recipes": con.execute("select count(*) from recipes").fetchone()[0],
        "ingredients": con.execute("select count(*) from ingredients").fetchone()[0],
        "workbenches": con.execute("select count(distinct workbench_edid) from recipes where workbench_edid is not null").fetchone()[0],
    }
    stats["top_workbenches"] = con.execute(
        "select workbench_edid, count(*) as n from recipes group by workbench_edid order by n desc limit 12"
    ).fetchall()
    return stats


def disabled_rows(con: sqlite3.Connection, limit: int = 80) -> list[sqlite3.Row]:
    clauses = []
    params = []
    for term in DISABLE_TERMS:
        clauses.append("lower(coalesce(m.comments,'') || ' ' || coalesce(p.notes_text,'') || ' ' || coalesce(m.description_text,'')) like ?")
        params.append(f"%{term}%")
    return con.execute(
        f"select {MODS_COLS} from plugins p join mods m on m.id = p.mod_id where {' or '.join(clauses)} order by p.priority limit ?",
        (*params, limit),
    ).fetchall()


def write_readme(metadata_db: Path, recipe_db: Path, out: Path) -> None:
    con = connect(metadata_db)
    mods = all_mods(con)
    enabled = [m for m in mods if m["enabled"]]
    disabled = [m for m in mods if not m["enabled"]]
    stats = recipe_stats(recipe_db)
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")

    lines: list[str] = []
    lines.append("# Current Gate to Sovngarde Game Overview")
    lines.append("")
    lines.append(f"Generated: `{generated}`")
    lines.append("")
    lines.append("This document is generated from the current MO2 profile metadata cache, the local GTS project config, and the local recipe index. It is a working reference, not an official GTS support document.")
    lines.append("")
    lines.append("## Source And Caveats")
    lines.append("")
    lines.append(f"- Active metadata DB: `{display_path(metadata_db)}`")
    lines.append(f"- Recipe DB: `{display_path(recipe_db)}`")
    lines.append(f"- Active mods indexed: `{len(enabled)}` enabled, `{len(disabled)}` disabled entries present in MO2 modlist")
    lines.append("- Most descriptions come from MO2 `meta.ini` cached `nexusDescription`, comments, and notes. Run `make mod-metadata-enrich` with `NEXUS_API_KEY` set to enrich the central cache with Nexus API detail fields.")
    lines.append("- GTS is curated. When this document says a mod provides a feature, GTS patches, MCMs, INIs, hidden files, or priority overrides may alter or disable parts of it.")
    lines.append("- Recipe truth comes from plugin data and the generated recipe DB; mod description truth comes from cached metadata and should be checked against xEdit/MO2 for exact conflict winners.")
    lines.append("")
    lines.append("## High-Level GTS Behavior")
    lines.append("")
    lines.append("- GTS uses Alternate Perspective instead of the vanilla intro, with traits/background choices and Story Mode options.")
    lines.append("- Combat is more lethal than vanilla, with stronger resource management pressure and many enemy/combat overhauls.")
    lines.append("- Survival, stress/fear, injuries, travel restrictions, Campfire-style systems, and no-menu-pause style immersion systems are expected parts of the experience.")
    lines.append("- Adamant/Hand to Hand, Mysticism, Mundus, Aetherius, Pilgrim, Blade and Blunt, Apothecary, Gourmet, Thaumaturgy, Artificer, and many JaySerpa/GTS-specific patches appear as major gameplay pillars in this active profile.")
    lines.append("")
    if stats:
        lines.append("## Generated Recipe Index Snapshot")
        lines.append("")
        lines.append(f"- Winning crafting recipes indexed: `{stats['recipes']}`")
        lines.append(f"- Ingredient rows indexed: `{stats['ingredients']}`")
        lines.append(f"- Distinct workbench keywords: `{stats['workbenches']}`")
        lines.append("- Top workbenches:")
        for row in stats["top_workbenches"]:
            lines.append(f"  - `{row['workbench_edid'] or 'none'}`: {row['n']} recipes")
        lines.append("")

    lines.append("## Major Systems By Active Mod Metadata")
    lines.append("")

    class_order = ["gameplay", "quest", "visual_env", "texture", "audio", "ui", "animation",
                   "armor_weapon", "npc", "follower", "fix", "framework", "other"]

    mods_by_class: dict[str, list[sqlite3.Row]] = {}
    for m in enabled:
        cls = m["mod_class"] or "other"
        mods_by_class.setdefault(cls, []).append(m)

    for cls in class_order:
        if cls not in mods_by_class:
            continue
        rows = mods_by_class[cls]
        importance = CLASS_IMPORTANCE.get(cls, "brief")
        label = CLASS_LABELS.get(cls, cls.capitalize())

        lines.append(f"### {label}")
        lines.append("")

        for row in rows:
            modid = f" modid={row['modid']}" if row["modid"] else ""
            lines.append(f"- **{row['name']}** `{row['version'] or 'unknown version'}`{modid}")

            ai = row["ai_summary"]
            if ai:
                append_summary(lines, ai)
            elif importance == "full":
                desc = full_description(row)
                if desc:
                    for line in desc.split("\n"):
                        lines.append(f"  - {line}")
            elif importance == "medium":
                summary = row["nexus_summary"] or row["description_text"] or ""
                if summary:
                    lines.append(f"  - {clean(summary, 500)}")
            else:
                summary = row["nexus_summary"] or row["description_text"] or ""
                if summary:
                    lines.append(f"  - {clean(summary, 200)}")
        lines.append("")

    lines.append("## Likely Disabled, Hidden, Replaced, Or Conflict-Managed Features")
    lines.append("")
    rows = disabled_rows(con)
    if rows:
        for row in rows:
            text = clean(" ".join(filter(None, [row["comments"], row["notes_text"], row["description_text"]])), 420)
            lines.append(f"- **{row['name']}**: {text}")
    else:
        lines.append("No obvious disable/hidden/obsolete/conflict notes found in cached metadata.")
    lines.append("")

    lines.append("## All Enabled Mods Appendix")
    lines.append("")
    lines.append("This appendix is intentionally broad so the document can be searched directly.")
    lines.append("")
    for row in enabled:
        modid = f" modid={row['modid']}" if row["modid"] else ""
        ai = row["ai_summary"]
        summary = one_line(row, 240)
        lines.append(f"- **{row['name']}** `{row['version'] or 'unknown'}`{modid}")
        if ai:
            append_summary(lines, ai)
        elif summary:
            lines.append(f"  - {summary}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out} with {len(enabled)} enabled mods")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--metadata-db")
    parser.add_argument("--recipe-db")
    parser.add_argument("--out", default="docs/current-game.md")
    args = parser.parse_args()

    config = load_config(abs_path(args.config))
    default_db = project_db_path(config)
    metadata_db = Path(args.metadata_db) if args.metadata_db else default_db
    recipe_db = Path(args.recipe_db) if args.recipe_db else default_db
    write_readme(metadata_db, recipe_db, abs_path(args.out))


if __name__ == "__main__":
    main()
