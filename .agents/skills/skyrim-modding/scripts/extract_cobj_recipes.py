#!/usr/bin/env python3
"""Extract COBJ crafting recipes from Skyrim/TES5 plugins.

This is a lightweight offline inspector for Constructible Object records. It is
not a replacement for xEdit, but it is useful when you need a searchable recipe
table from an installed list and only have plugin files available.
"""

from __future__ import annotations

import argparse
import csv
import json
import struct
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


COMPRESSED_RECORD = 0x00040000


@dataclass
class RecordInfo:
    plugin: str
    rec_type: str
    local_formid: int
    key: str
    raw_formid: str
    edid: str | None = None
    name: str | None = None


@dataclass
class Recipe:
    plugin: str
    local_formid: int
    key: str
    raw_formid: str
    edid: str | None = None
    created_formid: str | None = None
    created_edid: str | None = None
    created_name: str | None = None
    workbench_formid: str | None = None
    workbench_edid: str | None = None
    output_count: int = 1
    ingredients: list[dict[str, object]] = field(default_factory=list)
    conditions: int = 0


def zstring(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")


def localized_string(raw: bytes) -> str | None:
    if len(raw) == 4:
        return None
    return zstring(raw)


def u32(raw: bytes, offset: int = 0) -> int:
    return struct.unpack_from("<I", raw, offset)[0]


def i32(raw: bytes, offset: int = 0) -> int:
    return struct.unpack_from("<i", raw, offset)[0]


def formid_text(formid: int) -> str:
    return f"{formid:08X}"


def record_key(plugin: str, formid: int) -> str:
    return f"{plugin}:{formid & 0x00FFFFFF:06X}"


def resolve_ref_key(raw_formid: int, recipe_plugin: str, contexts: dict[str, list[str]]) -> str:
    masters = contexts.get(recipe_plugin, [])
    index = raw_formid >> 24
    file_names = masters + [recipe_plugin]
    source = file_names[index] if index < len(file_names) else recipe_plugin
    return record_key(source, raw_formid)


def iter_fields(data: bytes) -> Iterable[tuple[str, bytes]]:
    pos = 0
    override_size: int | None = None
    while pos + 6 <= len(data):
        field_type = data[pos : pos + 4].decode("ascii", errors="replace")
        size = struct.unpack_from("<H", data, pos + 4)[0]
        pos += 6
        if field_type == "XXXX" and size == 4 and pos + 4 <= len(data):
            override_size = u32(data, pos)
            pos += size
            continue
        if override_size is not None:
            size = override_size
            override_size = None
        if pos + size > len(data):
            break
        yield field_type, data[pos : pos + size]
        pos += size


def parse_record_payload(raw: bytes, flags: int) -> bytes:
    if flags & COMPRESSED_RECORD:
        expected_size = u32(raw, 0)
        payload = zlib.decompress(raw[4:])
        if len(payload) != expected_size:
            raise ValueError(f"decompressed {len(payload)} bytes, expected {expected_size}")
        return payload
    return raw


def iter_records(blob: bytes) -> Iterable[tuple[str, int, int, bytes]]:
    pos = 0
    end = len(blob)
    while pos + 24 <= end:
        rec_type = blob[pos : pos + 4].decode("ascii", errors="replace")
        size = u32(blob, pos + 4)
        if size < 0 or pos + 24 + size > end:
            break

        if rec_type == "GRUP":
            group_end = pos + size
            if group_end > pos + 24:
                yield from iter_records(blob[pos + 24 : group_end])
            pos = group_end
            continue

        flags = u32(blob, pos + 8)
        formid = u32(blob, pos + 12)
        payload = blob[pos + 24 : pos + 24 + size]
        try:
            payload = parse_record_payload(payload, flags)
        except Exception:
            payload = b""
        yield rec_type, flags, formid, payload
        pos += 24 + size


def read_masters(blob: bytes) -> list[str]:
    for rec_type, _flags, _formid, payload in iter_records(blob):
        if rec_type != "TES4":
            continue
        return [zstring(value) for field, value in iter_fields(payload) if field == "MAST"]
    return []


def parse_records(plugin_path: Path) -> tuple[list[RecordInfo], list[Recipe], list[str]]:
    blob = plugin_path.read_bytes()
    masters = read_masters(blob)
    records: list[RecordInfo] = []
    recipes: list[Recipe] = []

    for rec_type, _flags, formid, payload in iter_records(blob):
        key = record_key(plugin_path.name, formid)
        raw = formid_text(formid)
        edid: str | None = None
        name: str | None = None

        if rec_type == "COBJ":
            recipe = Recipe(plugin_path.name, formid, key, raw)
            for field, value in iter_fields(payload):
                if field == "EDID":
                    recipe.edid = zstring(value)
                elif field == "CNAM" and len(value) >= 4:
                    recipe.created_formid = formid_text(u32(value))
                elif field == "BNAM" and len(value) >= 4:
                    recipe.workbench_formid = formid_text(u32(value))
                elif field == "NAM1" and len(value) >= 2:
                    recipe.output_count = u32(value) if len(value) >= 4 else struct.unpack_from("<H", value)[0]
                elif field == "CNTO" and len(value) >= 8:
                    recipe.ingredients.append(
                        {"formid": formid_text(u32(value)), "count": i32(value, 4)}
                    )
                elif field == "CTDA":
                    recipe.conditions += 1
            recipes.append(recipe)
            continue

        for field, value in iter_fields(payload):
            if field == "EDID":
                edid = zstring(value)
            elif field == "FULL":
                name = localized_string(value)
        if edid or name:
            records.append(RecordInfo(plugin_path.name, rec_type, formid, key, raw, edid, name))

    return records, recipes, masters


def build_index(records: list[RecordInfo]) -> dict[str, RecordInfo]:
    index: dict[str, RecordInfo] = {}
    for record in records:
        index[record.key] = record
    return index


def resolve_recipe(recipe: Recipe, index: dict[str, RecordInfo], contexts: dict[str, list[str]]) -> dict[str, object]:
    created_key = resolve_ref_key(int(recipe.created_formid, 16), recipe.plugin, contexts) if recipe.created_formid else None
    bench_key = resolve_ref_key(int(recipe.workbench_formid, 16), recipe.plugin, contexts) if recipe.workbench_formid else None
    created = index.get(created_key or "")
    bench = index.get(bench_key or "")
    ingredients: list[dict[str, object]] = []
    for ingredient in recipe.ingredients:
        raw_formid = int(str(ingredient["formid"]), 16)
        resolved_key = resolve_ref_key(raw_formid, recipe.plugin, contexts)
        record = index.get(resolved_key)
        ingredients.append(
            {
                "raw_formid": ingredient["formid"],
                "resolved_formid": resolved_key,
                "count": ingredient["count"],
                "edid": record.edid if record else None,
                "name": record.name if record else None,
                "type": record.rec_type if record else None,
                "plugin": record.plugin if record else None,
            }
        )

    return {
        "plugin": recipe.plugin,
        "formid": recipe.key,
        "raw_formid": recipe.raw_formid,
        "edid": recipe.edid,
        "created_raw_formid": recipe.created_formid,
        "created_formid": created_key,
        "created_edid": created.edid if created else None,
        "created_name": created.name if created else None,
        "created_type": created.rec_type if created else None,
        "workbench_raw_formid": recipe.workbench_formid,
        "workbench_formid": bench_key,
        "workbench_edid": bench.edid if bench else None,
        "output_count": recipe.output_count,
        "ingredients": ingredients,
        "conditions_count": recipe.conditions,
    }


def write_csv(path: Path, recipes: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "plugin",
                "formid",
                "raw_formid",
                "edid",
                "created_raw_formid",
                "created_formid",
                "created_edid",
                "created_name",
                "created_type",
                "workbench_raw_formid",
                "workbench_formid",
                "workbench_edid",
                "output_count",
                "ingredients",
                "conditions_count",
            ],
        )
        writer.writeheader()
        for recipe in recipes:
            row = dict(recipe)
            row["ingredients"] = "; ".join(
                f"{item.get('count')}x {item.get('name') or item.get('edid') or item.get('resolved_formid')}"
                for item in recipe["ingredients"]  # type: ignore[index]
            )
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plugins", nargs="+", help="Plugin files in load order, e.g. Skyrim.esm Update.esm MyMod.esp")
    parser.add_argument("--json", dest="json_path", help="Write JSON output")
    parser.add_argument("--csv", dest="csv_path", help="Write CSV output")
    parser.add_argument("--contains", help="Filter recipes by created item name/EDID or recipe EDID")
    args = parser.parse_args()

    all_records: list[RecordInfo] = []
    all_recipes: list[Recipe] = []
    manifest: list[dict[str, object]] = []
    contexts: dict[str, list[str]] = {}

    for index, plugin in enumerate(args.plugins):
        path = Path(plugin)
        records, recipes, masters = parse_records(path)
        contexts[path.name] = masters
        all_records.extend(records)
        all_recipes.extend(recipes)
        manifest.append({"plugin": path.name, "index": index, "masters": masters, "recipes": len(recipes)})

    index = build_index(all_records)
    resolved = [resolve_recipe(recipe, index, contexts) for recipe in all_recipes]

    if args.contains:
        needle = args.contains.casefold()
        resolved = [
            recipe
            for recipe in resolved
            if needle in str(recipe.get("edid") or "").casefold()
            or needle in str(recipe.get("created_edid") or "").casefold()
            or needle in str(recipe.get("created_name") or "").casefold()
        ]

    payload = {"plugins": manifest, "recipes": resolved}

    if args.json_path:
        Path(args.json_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.csv_path:
        write_csv(Path(args.csv_path), resolved)
    if not args.json_path and not args.csv_path:
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
