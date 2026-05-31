#!/usr/bin/env python3
"""Query the local GTS item/recipe SQLite index."""

from __future__ import annotations

import argparse
import re
import sqlite3
from collections import defaultdict
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def search(con: sqlite3.Connection, text: str) -> None:
    like = f"%{text.lower()}%"
    rows = con.execute(
        """
        select recipe_id, created_name, created_edid, created_value, workbench_edid, condition_count
        from recipes
        where lower(coalesce(created_name,'') || ' ' || coalesce(created_edid,'') || ' ' || coalesce(recipe_edid,'')) like ?
        order by created_name, created_edid
        limit 50
        """,
        (like,),
    ).fetchall()
    for row in rows:
        print(f"[{row['recipe_id']}] {row['created_name'] or row['created_edid']} value={row['created_value']} workbench={row['workbench_edid']} conditions={row['condition_count']}")


def recipe(con: sqlite3.Connection, text: str) -> None:
    like = f"%{text.lower()}%"
    rows = con.execute(
        """
        select * from recipes
        where lower(coalesce(created_name,'') || ' ' || coalesce(created_edid,'') || ' ' || coalesce(recipe_edid,'')) like ?
        order by created_name, created_edid
        limit 20
        """,
        (like,),
    ).fetchall()
    for row in rows:
        ingredients = con.execute(
            "select * from ingredients where recipe_id = ? order by ingredient_name, ingredient_edid",
            (row["recipe_id"],),
        ).fetchall()
        print(f"{row['created_count']}x {row['created_name'] or row['created_edid']} [{row['created_formid']}]")
        print(f"  Recipe: {row['recipe_edid']} from {row['source_plugin']}")
        print(f"  Workbench: {row['workbench_edid'] or row['workbench_formid'] or 'none'}")
        print(f"  Value/weight: {row['created_value']}/{row['created_weight']}")
        print("  Ingredients:")
        for item in ingredients:
            print(f"  {item['count']}x {item['ingredient_name'] or item['ingredient_edid'] or item['ingredient_formid']} value={item['ingredient_value']}")


def normalize_query(text: str) -> list[str]:
    text = text.lower().replace("packpack", "backpack")
    words = re.findall(r"[a-z0-9]+", text)
    return [w for w in words if w not in {"the", "a", "an", "with", "of"}]


def matching_recipes(con: sqlite3.Connection, terms: list[str], limit: int = 20) -> list[sqlite3.Row]:
    haystack = "lower(coalesce(created_name,'') || ' ' || coalesce(created_edid,'') || ' ' || coalesce(recipe_edid,''))"
    where = " and ".join([f"{haystack} like ?" for _ in terms]) or "1=1"
    params = [f"%{term}%" for term in terms]
    return con.execute(
        f"""
        select * from recipes
        where {where}
        order by created_name, created_edid, recipe_edid
        limit ?
        """,
        (*params, limit),
    ).fetchall()


def likely_mods(metadata_db: Path | None, plugin: str) -> list[sqlite3.Row]:
    if metadata_db is None or not metadata_db.exists():
        return []
    stem = Path(plugin).stem.lower()
    terms = [stem]
    if stem == "campfire":
        terms.insert(0, "Campfire - Complete Camping System")
    con = connect(metadata_db)
    try:
        rows: list[sqlite3.Row] = []
        seen: set[int] = set()
        for term in terms:
            found = con.execute(
                """
                select p.mod_index, p.name, m.version, p.modid, m.ai_summary, m.nexus_summary
                from plugins p join mods m on m.id = p.mod_id
                where p.enabled = 1
                  and lower(p.name) like ?
                order by
                  case when lower(p.name) = lower(?) then 0 else 1 end,
                  p.priority
                limit 5
                """,
                (f"%{term.lower()}%", term),
            ).fetchall()
            for row in found:
                if row["mod_index"] not in seen:
                    rows.append(row)
                    seen.add(row["mod_index"])
        return rows[:5]
    finally:
        con.close()


def mod_metadata(metadata_db: Path | None, mod_index: object | None, mod_path: object | None) -> sqlite3.Row | None:
    if metadata_db is None or not metadata_db.exists():
        return None
    con = connect(metadata_db)
    try:
        if mod_index is not None:
            row = con.execute(
                """
                select p.mod_index, p.name, m.version, p.modid, m.ai_summary, m.nexus_summary, m.description_text
                from plugins p join mods m on m.id = p.mod_id
                where p.mod_index = ?
                """,
                (mod_index,),
            ).fetchone()
            if row:
                return row
        if mod_path is None:
            return None
        return con.execute(
            """
            select p.mod_index, p.name, m.version, p.modid, m.ai_summary, m.nexus_summary, m.description_text
            from plugins p join mods m on m.id = p.mod_id
            where p.path = ?
            """,
            (str(mod_path),),
        ).fetchone()
    finally:
        con.close()


def row_get(row: sqlite3.Row, key: str) -> object | None:
    return row[key] if key in row.keys() else None


def lookup(con: sqlite3.Connection, text: str, metadata_db: Path | None) -> None:
    original_terms = normalize_query(text)
    attempts = [original_terms]
    if "leather" in original_terms:
        attempts.append([t for t in original_terms if t != "leather"])
    if "backpack" in original_terms:
        attempts.append([t for t in original_terms if t in {"backpack", "black", "brown", "white", "fine", "fur"}])

    rows: list[sqlite3.Row] = []
    used_terms: list[str] = []
    for terms in attempts:
        rows = matching_recipes(con, terms)
        if rows:
            used_terms = terms
            break

    print(f"Query: {text}")
    if not rows:
        print("No recipe/item matches found in the generated recipe index.")
        print("How checked: Makefile item lookup -> recipe SQLite index (`recipes` table).")
        return

    if used_terms != original_terms:
        print(f"No exact all-term match; showing fuzzy matches for: {' '.join(used_terms)}")
        print("Answer guidance: say no exact item name was found, then report the closest indexed match(es). Do not inspect SQLite/schema/plugin files unless deeper verification was explicitly requested.")
    print("How found: Makefile item lookup -> generated recipe SQLite index (`recipes` + `ingredients`).")
    print("")

    source_plugins = []
    source_mods: dict[str, dict[str, object | None]] = {}
    metadata_cache: dict[str, sqlite3.Row | None] = {}
    for row in rows:
        if row["source_plugin"] not in source_plugins:
            source_plugins.append(row["source_plugin"])
        print(f"{row['created_count']}x {row['created_name'] or row['created_edid']} [{row['created_formid']}]")
        print(f"  Source plugin: {row['source_plugin']}")
        source_mod_name = row_get(row, "source_mod_name")
        if source_mod_name:
            mod_index = row_get(row, "source_mod_index")
            mod_path = row_get(row, "source_mod_path")
            mod_path_text = str(mod_path) if mod_path else ""
            cache_key = str(mod_index) if mod_index is not None else mod_path_text
            if cache_key not in metadata_cache:
                metadata_cache[cache_key] = mod_metadata(metadata_db, mod_index, mod_path)
            meta = metadata_cache[cache_key]
            display_name = meta["name"] if meta else source_mod_name
            modid = meta["modid"] if meta else row_get(row, "source_modid")
            version = meta["version"] if meta else row_get(row, "source_mod_version")
            provider_count = row_get(row, "source_mod_provider_count")
            mod_text = str(display_name)
            if version:
                mod_text += f" `{version}`"
            if modid:
                mod_text += f" modid={modid}"
            if provider_count and int(provider_count) > 1:
                mod_text += f" ({provider_count} enabled mods ship this plugin; this is the winning provider)"
            print(f"  Source mod: {mod_text}")
            summary = (meta["ai_summary"] or meta["nexus_summary"] or meta["description_text"]) if meta else None
            if summary:
                source_mods[cache_key] = {
                    "name": display_name,
                    "modid": modid,
                    "version": version,
                    "provider_count": provider_count,
                    "summary": summary,
                }
        print(f"  Recipe: {row['recipe_edid']} [{row['recipe_formid']}]")
        print(f"  Workbench: {row['workbench_edid'] or row['workbench_formid'] or 'none'}")
        print(f"  Stats: value={row['created_value']} weight={row['created_weight']}")
        print(f"  Conditions: {row['condition_count']}")
        ingredients = con.execute(
            "select * from ingredients where recipe_id = ? order by ingredient_name, ingredient_edid",
            (row["recipe_id"],),
        ).fetchall()
        if ingredients:
            print("  Ingredients:")
            for item in ingredients:
                name = item["ingredient_name"] or item["ingredient_edid"] or item["ingredient_formid"]
                print(f"    {item['count']}x {name} value={item['ingredient_value']}")
        print("")

    if source_mods:
        print("Source mod details:")
        for info in source_mods.values():
            mod_text = str(info["name"])
            if info["version"]:
                mod_text += f" `{info['version']}`"
            if info["modid"]:
                mod_text += f" modid={info['modid']}"
            if info["provider_count"] and int(info["provider_count"]) > 1:
                mod_text += f" ({info['provider_count']} enabled mods ship this plugin; shown mod is winning provider)"
            print(f"  - {mod_text}")
            print(f"    {info['summary']}")
        print("")

    if not any(row_get(row, "source_mod_name") for row in rows) and metadata_db:
        print("Likely active mod metadata for source plugin(s):")
        any_mods = False
        for plugin in source_plugins:
            mods = likely_mods(metadata_db, plugin)
            if not mods:
                continue
            any_mods = True
            print(f"  {plugin}:")
            for mod in mods:
                modid = f" modid={mod['modid']}" if mod["modid"] else ""
                summary = mod["ai_summary"] or mod["nexus_summary"] or ""
                print(f"    - {mod['name']} `{mod['version'] or 'unknown'}`{modid}")
                if summary:
                    print(f"      {summary}")
        if not any_mods:
            print("  No likely active mod metadata match found by source plugin name.")


def chain(con: sqlite3.Connection, text: str, depth: int) -> None:
    seen: set[str] = set()

    def expand(query: str, level: int) -> None:
        if level > depth:
            return
        like = f"%{query.lower()}%"
        rows = con.execute(
            """
            select * from recipes
            where lower(coalesce(created_name,'') || ' ' || coalesce(created_edid,'')) like ?
            order by created_name, created_edid
            limit 5
            """,
            (like,),
        ).fetchall()
        for row in rows:
            key = row["created_formid"]
            indent = "  " * level
            if key in seen:
                print(f"{indent}{row['created_name'] or row['created_edid']} (already shown)")
                continue
            seen.add(key)
            print(f"{indent}{row['created_count']}x {row['created_name'] or row['created_edid']}")
            ingredients = con.execute("select * from ingredients where recipe_id = ?", (row["recipe_id"],)).fetchall()
            for item in ingredients:
                name = item["ingredient_name"] or item["ingredient_edid"] or item["ingredient_formid"]
                print(f"{indent}  needs {item['count']}x {name}")
                expand(name, level + 2)

    expand(text, 0)


def best(con: sqlite3.Connection, materials: list[str]) -> None:
    clauses = []
    params = []
    for material in materials:
        clauses.append("lower(coalesce(i.ingredient_name,'') || ' ' || coalesce(i.ingredient_edid,'')) like ?")
        params.append(f"%{material.lower()}%")
    where = " or ".join(clauses) if clauses else "1=1"
    rows = con.execute(
        f"""
        select r.recipe_id, r.created_name, r.created_edid, r.created_value, r.created_count,
               group_concat(i.count || 'x ' || coalesce(i.ingredient_name, i.ingredient_edid, i.ingredient_formid), '; ') as ingredients,
               sum(i.count * coalesce(i.ingredient_value, 0)) as known_input_value
        from recipes r
        join ingredients i on i.recipe_id = r.recipe_id
        where {where}
        group by r.recipe_id
        order by (coalesce(r.created_value, 0) * r.created_count - known_input_value) desc,
                 coalesce(r.created_value, 0) desc
        limit 50
        """,
        params,
    ).fetchall()
    for row in rows:
        output_value = (row["created_value"] or 0) * row["created_count"]
        margin = output_value - (row["known_input_value"] or 0)
        print(f"margin={margin:g} output_value={output_value:g} [{row['recipe_id']}] {row['created_name'] or row['created_edid']} <- {row['ingredients']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="cache/gts-index/gts.sqlite")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("search")
    p.add_argument("text")
    p = sub.add_parser("recipe")
    p.add_argument("text")
    p = sub.add_parser("chain")
    p.add_argument("text")
    p.add_argument("--depth", type=int, default=4)
    p = sub.add_parser("best")
    p.add_argument("materials", nargs="+")
    p = sub.add_parser("lookup")
    p.add_argument("text")
    p.add_argument("--metadata-db")
    args = parser.parse_args()

    con = connect(Path(args.db))
    if args.command == "search":
        search(con, args.text)
    elif args.command == "recipe":
        recipe(con, args.text)
    elif args.command == "chain":
        chain(con, args.text, args.depth)
    elif args.command == "best":
        best(con, args.materials)
    elif args.command == "lookup":
        metadata_db = Path(args.metadata_db) if args.metadata_db else None
        lookup(con, args.text, metadata_db)


if __name__ == "__main__":
    main()
