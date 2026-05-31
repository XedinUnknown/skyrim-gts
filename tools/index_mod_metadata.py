#!/usr/bin/env python3
"""Index active MO2 mod metadata using a reusable central SQLite cache."""

from __future__ import annotations

import argparse
import configparser
import html
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "gts-index.config.json"
GAME_DOMAIN = "skyrimspecialedition"


def load_config(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    config.setdefault("gts_path", "/mnt/e/games/GTSAV")
    config.setdefault("profile_path", str(Path(config["gts_path"]) / "profiles" / "Gate to Sovngarde Anniversary Edition Upgrade"))
    config.setdefault("db_path", "cache/gts-index/gts.sqlite")
    config.setdefault("mod_metadata_dir", "cache/gts-mod-metadata-index")
    config.setdefault("mod_metadata_cache_db", str(Path.home() / ".cache" / "skyrim-gts" / "mod-metadata-cache.sqlite"))
    return config


def abs_path(value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else ROOT / path


def project_db_path(config: dict[str, object]) -> Path:
    return abs_path(os.environ.get("GTS_DB", str(config.get("db_path", "cache/gts-index/gts.sqlite"))))


def plugins(profile: Path, mods_dir: Path) -> list[dict[str, object]]:
    mods: list[dict[str, object]] = []
    for priority, raw in enumerate((profile / "modlist.txt").read_text(encoding="utf-8", errors="replace").splitlines()):
        if not raw or raw[0] not in "+-":
            continue
        name = raw[1:]
        if name.endswith("_separator"):
            continue
        path = mods_dir / name
        if path.is_dir():
            mods.append({"priority": priority, "name": name, "enabled": raw[0] == "+", "path": path})
    return mods


def read_meta(mod: dict[str, object]) -> dict[str, object]:
    path = Path(mod["path"]) / "meta.ini"
    data: dict[str, object] = {"meta_path": str(path) if path.exists() else None}
    if not path.exists():
        return data

    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    try:
        parser.read(path, encoding="utf-8")
    except configparser.Error as exc:
        data["parse_error"] = str(exc)
        return data

    general = parser["General"] if parser.has_section("General") else {}
    for key in [
        "gameName", "modid", "version", "newestVersion", "category", "nexusFileStatus",
        "installationFile", "repository", "comments", "notes", "nexusDescription", "url",
        "lastNexusQuery", "lastNexusUpdate", "nexusLastModified", "nexusCategory", "tracked", "endorsed",
    ]:
        data[key] = general.get(key)

    file_ids = []
    if parser.has_section("installedFiles"):
        for key, value in parser["installedFiles"].items():
            if key.endswith("\\fileid"):
                file_ids.append(value)
    data["file_ids"] = ",".join(file_ids)
    return data


def clean_markup(text: str | None) -> str | None:
    if not text:
        return None
    text = text.replace("\\n", "\n")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[/?(?:b|i|u|center|left|right|size|color|spoiler|list|font|youtube|video|img|\*)[^\]]*\]", " ", text, flags=re.I)
    text = re.sub(r"\[url=[^\]]+\]", " ", text, flags=re.I)
    text = re.sub(r"\[/url\]", " ", text, flags=re.I)
    text = re.sub(r"\[img[^\]]*\].*?\[/img\]", " ", text, flags=re.I | re.S)
    text = re.sub(r"\[youtube\].*?\[/youtube\]", " ", text, flags=re.I | re.S)
    text = re.sub(r"https?://\S+\.(?:png|jpg|jpeg|gif|webp|bmp)\S*\s+", "", text, flags=re.I)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() or None


def cache_key(meta: dict[str, object], mod_name: str) -> str:
    repository = str(meta.get("repository") or "local").lower()
    modid = meta.get("modid")
    if modid and str(modid).isdigit() and int(str(modid)) > 0:
        return f"{repository}:skyrimspecialedition:{modid}"
    installation = meta.get("installationFile")
    if installation:
        return f"archive:{installation}"
    return f"local:{mod_name}"


def nexus_fetch(modid: str, api_key: str, delay: float) -> dict[str, object] | None:
    url = f"https://api.nexusmods.com/v1/games/{GAME_DOMAIN}/mods/{modid}.json"
    request = urllib.request.Request(url, headers={"apikey": api_key, "User-Agent": "skyrim-gts-local-index/1.0"})
    if delay:
        time.sleep(delay)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"Warning: Nexus API HTTP {exc.code} for mod {modid}", file=sys.stderr)
    except urllib.error.URLError as exc:
        print(f"Warning: Nexus API error for mod {modid}: {exc}", file=sys.stderr)
    return None


def open_cache(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=60, isolation_level=None)
    con.execute("pragma busy_timeout = 60000")
    con.execute("pragma journal_mode = wal")
    con.execute("pragma synchronous = normal")
    con.executescript(
        """
        create table if not exists mod_cache (
          cache_key text primary key,
          repository text,
          game_domain text,
          modid integer,
          display_name text,
          installation_file text,
          file_ids text,
          category text,
          nexus_category text,
          version text,
          newest_version text,
          comments text,
          notes_html text,
          notes_text text,
          description_html text,
          description_text text,
          nexus_summary text,
          nexus_name text,
          nexus_author text,
          nexus_version text,
          nexus_updated text,
          nexus_url text,
          local_meta_seen_at text,
          nexus_seen_at text,
          raw_meta_json text,
          raw_nexus_json text,
          mod_class text not null default 'other',
          ai_summary text
        );
        create index if not exists idx_mod_cache_modid on mod_cache(modid);
        create index if not exists idx_mod_cache_display_name on mod_cache(display_name);
        """
    )
    try:
        con.execute("alter table mod_cache add column ai_summary text")
    except sqlite3.OperationalError:
        pass
    for ddl in [
        "alter table mod_cache add column category text",
        "alter table mod_cache add column nexus_category text",
        "alter table mod_cache add column mod_class text not null default 'other'",
    ]:
        try:
            con.execute(ddl)
        except sqlite3.OperationalError:
            pass
    return con


def category_ids(category: object) -> set[int]:
    result: set[int] = set()
    for value in re.findall(r"\d+", str(category or "")):
        try:
            result.add(int(value))
        except ValueError:
            pass
    return result


def classify_mod(name: str, nexus_summary: str | None, description_text: str | None, comments: str | None,
                 category: object = None, nexus_category: object = None) -> str:
    text = " ".join(filter(None, [name, nexus_summary, description_text, comments])).lower()
    cats = category_ids(category) | category_ids(nexus_category)

    # Nexus/MO2 category IDs are useful signal, but not authoritative enough to
    # replace text heuristics for every category. These IDs cover common
    # gameplay-heavy Skyrim SE Nexus categories observed in GTS metadata.
    if cats & {24, 27, 31, 35, 43, 53}:
        return "gameplay"
    if cats & {30}:
        return "quest"

    exclude_patterns = ["retexture", "mesh", "replacer", "hd ", "4k", "2k", "1k", "skin texture", "body texture"]

    rules = [
        ("texture", ["retexture", "mesh ", "replacer", "hd ", "4k", "2k", "1k", "skin texture", "body texture",
                     "recolor", "reskin", "re-color"]),
        ("audio", ["sound", "audio", "music", "sfx", "reverb", "voice", "footstep"]),
        ("ui", ["hud", "ui ", "menu", "interface", "compass", "crosshair", "healthbar", "icon", "skyui"]),
        ("animation", ["animation", "animated", "idle", "mount", "jump", "dodge", "move"]),
        ("visual_env", ["weather", "cloud", "sky ", "water", "grass", "tree", "flora", "lens flare", "dof", "enb",
                        "lighting", "shadow", "shader", "community shaders", "sun", "fog", "mist"]),
        ("armor_weapon", ["armor", "weapon", "shield", "bow", "sword", "dagger", "axe", "mace", "staff",
                          "robe", "cloth", "outfit", "gear ", "equipment"]),
        ("npc", ["npc ", "face", "hair", "beard", "brow", "eye ", "skin", "overhaul npc", "vanilla npc",
                 "body", "preset", "racemenu", "overlay"]),
        ("follower", ["follower", "companion", "fde ", "fde-"]),
    ]

    gameplay_keywords = [
        "perk", "spell", "magic", "enchant", "alchemy", "smithing", "crafting",
        "combat", "damage", "health", "stamina", "magicka", "armor rating",
        "difficulty", "lethal", "injure", "mortal", "wound",
        "survival", "hunger", "thirst", "cold", "campfire", "sleep",
        "economy", "price", "gold", "loot", "leveled list", "vendor",
        "dragon", "boss", "monster", "creature", "enemy",
    ]
    has_gameplay = any(k in text for k in gameplay_keywords)
    has_exclude = any(k in text for k in exclude_patterns)

    strong_gameplay_keywords = [
        "spell pack", "new spells", "adds spells", "adds new spells", "spell tome",
        "perks", "perk overhaul", "skill tree", "shout", "standing stone",
        "artifact", "enchantment", "alchemy overhaul", "combat overhaul",
        "survival mode", "mechanic", "system", "quest expansion",
    ]
    if any(k in text for k in strong_gameplay_keywords):
        return "gameplay"

    for cls, patterns in rules:
        if any(p in text for p in patterns):
            if has_gameplay and not has_exclude and cls in ("armor_weapon", "npc", "texture", "audio", "animation", "ui", "visual_env"):
                return "gameplay"
            return cls

    if has_gameplay and not has_exclude:
        return "gameplay"

    if any(k in text for k in ["fix", "bug", "patch", "tweak", "crash", "optimize"]):
        return "fix"

    if any(k in text for k in ["framework", "library", "dll", "skse", "resource", "util", "api"]):
        return "framework"

    return "other"


def create_project_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(
        """
        create table if not exists manifest (key text primary key, value text not null);
        drop table if exists plugins_fts;
        drop table if exists plugins;
        drop table if exists mods;
        drop table if exists active_mods_fts;
        drop table if exists active_mods;
        create table mods (
          id integer primary key,
          cache_key text not null unique,
          name text,
          nexus_name text,
          nexus_author text,
          nexus_version text,
          nexus_updated text,
          nexus_url text,
          nexus_summary text,
          description_text text,
          comments text,
          category text,
          nexus_category text,
          version text,
          newest_version text,
          mod_class text not null default 'other',
          ai_summary text
        );
        create table plugins (
          mod_index integer primary key,
          mod_id integer references mods(id),
          priority integer not null,
          enabled integer not null,
          name text not null,
          path text not null,
          cache_key text not null,
          repository text,
          modid integer,
          installation_file text,
          notes_text text
        );
        create virtual table plugins_fts using fts5(name, mod_name, comments, notes_text, description_text, nexus_summary, mod_class, ai_summary);
        create index idx_plugins_cache_key on plugins(cache_key);
        create index idx_plugins_modid on plugins(modid);
        create index idx_plugins_mod_id on plugins(mod_id);
        create index idx_mods_cache_key on mods(cache_key);
        """
    )
    return con


def upsert_cache(con: sqlite3.Connection, key: str, mod_name: str, meta: dict[str, object], nexus: dict[str, object] | None) -> None:
    modid = meta.get("modid")
    description_html = meta.get("nexusDescription")
    notes_html = meta.get("notes")
    description_text = clean_markup(str(description_html)) if description_html else None
    comments = meta.get("comments")
    category = meta.get("category")
    nexus_category = meta.get("nexusCategory") or (nexus.get("category_id") if nexus else None)
    mod_class = classify_mod(
        nexus.get("name") if nexus else mod_name,
        nexus.get("summary") if nexus else None,
        description_text,
        str(comments) if comments else None,
        category,
        nexus_category,
    )
    now = datetime.now(timezone.utc).isoformat()
    con.execute(
        """
        insert into mod_cache (
          cache_key, repository, game_domain, modid, display_name,
          installation_file, file_ids, category, nexus_category, version,
          newest_version, comments, notes_html, notes_text, description_html,
          description_text, nexus_summary, nexus_name, nexus_author, nexus_version,
          nexus_updated, nexus_url, local_meta_seen_at, nexus_seen_at,
          raw_meta_json, raw_nexus_json, mod_class, ai_summary
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(cache_key) do update set
          repository=excluded.repository,
          game_domain=excluded.game_domain,
          modid=excluded.modid,
          display_name=excluded.display_name,
          installation_file=excluded.installation_file,
          file_ids=excluded.file_ids,
          category=excluded.category,
          nexus_category=coalesce(excluded.nexus_category, mod_cache.nexus_category),
          version=excluded.version,
          newest_version=excluded.newest_version,
          comments=excluded.comments,
          notes_html=excluded.notes_html,
          notes_text=excluded.notes_text,
          description_html=excluded.description_html,
          description_text=excluded.description_text,
          nexus_summary=coalesce(excluded.nexus_summary, mod_cache.nexus_summary),
          nexus_name=coalesce(excluded.nexus_name, mod_cache.nexus_name),
          nexus_author=coalesce(excluded.nexus_author, mod_cache.nexus_author),
          nexus_version=coalesce(excluded.nexus_version, mod_cache.nexus_version),
          nexus_updated=coalesce(excluded.nexus_updated, mod_cache.nexus_updated),
          nexus_url=excluded.nexus_url,
          local_meta_seen_at=excluded.local_meta_seen_at,
          nexus_seen_at=coalesce(excluded.nexus_seen_at, mod_cache.nexus_seen_at),
          raw_meta_json=excluded.raw_meta_json,
          raw_nexus_json=coalesce(excluded.raw_nexus_json, mod_cache.raw_nexus_json),
          mod_class=excluded.mod_class,
          ai_summary=coalesce(mod_cache.ai_summary, excluded.ai_summary)
        """,
        (
            key,
            meta.get("repository"),
            GAME_DOMAIN,
            int(str(modid)) if modid and str(modid).isdigit() else None,
            nexus.get("name") if nexus else mod_name,
            meta.get("installationFile"),
            meta.get("file_ids"),
            category,
            nexus_category,
            meta.get("version"),
            meta.get("newestVersion"),
            comments,
            notes_html,
            clean_markup(str(notes_html)) if notes_html else None,
            description_html,
            description_text,
            nexus.get("summary") if nexus else None,
            nexus.get("name") if nexus else None,
            nexus.get("author") if nexus else None,
            nexus.get("version") if nexus else None,
            nexus.get("updated_time") if nexus else None,
            f"https://www.nexusmods.com/skyrimspecialedition/mods/{modid}" if modid and str(modid).isdigit() else None,
            now,
            now if nexus else None,
            json.dumps(meta, ensure_ascii=False),
            json.dumps(nexus, ensure_ascii=False) if nexus else None,
            mod_class,
            None,
        ),
    )


def copy_project_subset(project: sqlite3.Connection, cache: sqlite3.Connection, mods: list[dict[str, object]], keys: list[str], config_path: Path, cache_path: Path, enriched: int) -> None:
    mod_id_map: dict[str, int] = {}
    next_mod_id = 1
    seen_keys: set[str] = set()
    for idx, (mod, key) in enumerate(zip(mods, keys), start=1):
        if key in seen_keys:
            continue
        seen_keys.add(key)
        row = cache.execute("select * from mod_cache where cache_key = ?", (key,)).fetchone()
        if row is None:
            continue
        mod_class = row["mod_class"] or classify_mod(
            str(mod["name"]),
            row["nexus_summary"] if row else None,
            row["description_text"] if row else None,
            row["comments"] if row else None,
            row["category"] if row else None,
            row["nexus_category"] if row else None,
        )
        project.execute(
            """
            insert into mods values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                next_mod_id,
                key,
                row["display_name"],
                row["nexus_name"],
                row["nexus_author"],
                row["nexus_version"],
                row["nexus_updated"],
                row["nexus_url"],
                row["nexus_summary"],
                row["description_text"],
                row["comments"],
                row["category"],
                row["nexus_category"],
                row["version"],
                row["newest_version"],
                mod_class,
                row["ai_summary"],
            ),
        )
        mod_id_map[key] = next_mod_id
        next_mod_id += 1

    for idx, (mod, key) in enumerate(zip(mods, keys), start=1):
        mod_id = mod_id_map.get(key)
        if mod_id is None:
            continue
        cache_row = cache.execute("select * from mod_cache where cache_key = ?", (key,)).fetchone()
        project.execute(
            """
            insert into plugins values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                idx,
                mod_id,
                mod["priority"],
                1 if mod["enabled"] else 0,
                mod["name"],
                str(mod["path"]),
                key,
                cache_row["repository"] if cache_row else None,
                cache_row["modid"] if cache_row else None,
                cache_row["installation_file"] if cache_row else None,
                cache_row["notes_text"] if cache_row else None,
            ),
        )
    project.execute(
        """
        insert into plugins_fts(rowid, name, mod_name, comments, notes_text, description_text, nexus_summary, mod_class, ai_summary)
        select a.mod_index, a.name, coalesce(m.name,''), coalesce(m.comments,''), coalesce(a.notes_text,''), coalesce(m.description_text,''), coalesce(m.nexus_summary,''), coalesce(m.mod_class,''), coalesce(m.ai_summary,'')
        from plugins a join mods m on m.id = a.mod_id
        """
    )
    class_dist = project.execute(
        "select m.mod_class, count(*) as cnt from plugins a join mods m on m.id = a.mod_id group by m.mod_class order by m.mod_class"
    ).fetchall()
    manifest = {
        "mod.generated_at": datetime.now(timezone.utc).isoformat(),
        "mod.config": str(config_path),
        "mod.central_cache_db": str(cache_path),
        "mod.active_mod_count": str(len(mods)),
        "mod.nexus_enriched_count": str(enriched),
        "mod.source": "Project subset of central local mod metadata cache",
    }
    for cls, cnt in class_dist:
        manifest[f"mod.class_{cls}_count"] = str(cnt)
    project.executemany("insert or replace into manifest values (?, ?)", manifest.items())


def index(config_path: Path, out_dir: Path | None, enrich: bool, limit: int | None, delay: float, refresh_nexus: bool, nexus_ttl: float) -> Path:
    config = load_config(config_path)
    gts = abs_path(os.environ.get("GTS_PATH", str(config["gts_path"])))
    profile = abs_path(os.environ.get("GTS_PROFILE_PATH", str(config["profile_path"])))
    project_db_path_value = Path(out_dir) if out_dir else project_db_path(config)
    cache_db_path = abs_path(os.environ.get("GTS_MOD_METADATA_CACHE_DB", str(config["mod_metadata_cache_db"])))
    api_key = os.environ.get("NEXUS_API_KEY")
    if enrich and not api_key:
        print("Warning: --enrich requested but NEXUS_API_KEY is not set; using local meta.ini only", file=sys.stderr)
        enrich = False

    mods = plugins(profile, gts / "mods")
    if limit is not None:
        mods = mods[:limit]
    ttl_secs = nexus_ttl * 3600

    cache = open_cache(cache_db_path)
    cache.row_factory = sqlite3.Row
    keys: list[str] = []
    enriched = 0
    skipped = 0
    no_modid = 0
    stale = 0
    total = len(mods)
    if enrich:
        print(f"[start] scanning {total} active mods; cached Nexus rows younger than {nexus_ttl:g}h are skipped", file=sys.stderr, flush=True)
    for idx, mod in enumerate(mods, start=1):
        meta = read_meta(mod)
        key = cache_key(meta, str(mod["name"]))
        keys.append(key)
        modid = meta.get("modid")
        existing = cache.execute("select nexus_seen_at from mod_cache where cache_key = ?", (key,)).fetchone()
        has_modid = modid and str(modid).isdigit() and int(str(modid)) > 0
        if enrich and has_modid:
            stale_ok = nexus_ttl <= 0
            if not stale_ok and existing and existing["nexus_seen_at"]:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(existing["nexus_seen_at"])).total_seconds()
                stale_ok = age > ttl_secs
            should_fetch = refresh_nexus or existing is None or existing["nexus_seen_at"] is None or stale_ok
            if should_fetch:
                stale += 1
                print(f"[{idx}/{total}] fetching Nexus for {mod['name']} (modid={modid})", file=sys.stderr)
                nexus = nexus_fetch(str(modid), api_key, delay)
                if nexus:
                    enriched += 1
                upsert_cache(cache, key, str(mod["name"]), meta, nexus)
                cache.commit()
                print(f"  fetched {'OK' if nexus else 'FAIL'}", file=sys.stderr)
            else:
                skipped += 1
                upsert_cache(cache, key, str(mod["name"]), meta, None)
                cache.commit()
        else:
            skipped += 1
            if enrich and not has_modid:
                no_modid += 1
            upsert_cache(cache, key, str(mod["name"]), meta, None)
            cache.commit()

        if enrich and (idx % 25 == 0 or idx == total):
            failed = stale - enriched
            print(f"[{idx}/{total}] checked; fetched={enriched} failed={failed} skipped_cached={skipped - no_modid} no_modid={no_modid}", file=sys.stderr, flush=True)
        elif not enrich and idx % 100 == 0:
            print(f"[{idx}/{total}] scanned", file=sys.stderr, flush=True)

    if enrich:
        print(f"[done] {enriched} fetched, {stale - enriched} failed, {skipped - no_modid} skipped cached, {no_modid} skipped without Nexus modid", file=sys.stderr)

    project = create_project_db(project_db_path_value)
    cache.row_factory = sqlite3.Row
    with project:
        copy_project_subset(project, cache, mods, keys, config_path, cache_db_path, enriched)
    print(f"Indexed {total} active mods to {project_db_path_value}", file=sys.stderr)
    print(f"Updated central metadata cache at {cache_db_path} ({enriched} Nexus API fetches)", file=sys.stderr)
    return project_db_path_value


def search(db_path: Path, query: str, limit: int) -> None:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        select a.mod_index, a.enabled, a.name, a.modid,
               m.name as mod_name, m.nexus_url, m.version,
               snippet(plugins_fts, 3, '[', ']', '...', 20) as snippet
        from plugins_fts
        join plugins a on a.mod_index = plugins_fts.rowid
        join mods m on m.id = a.mod_id
        where plugins_fts match ?
        order by rank
        limit ?
        """,
        (query, limit),
    ).fetchall()
    for row in rows:
        state = "+" if row["enabled"] else "-"
        print(f"[{row['mod_index']}] {state} {row['name']} modid={row['modid']} version={row['version']}")
        if row["nexus_url"]:
            print(f"  {row['nexus_url']}")
        if row["snippet"]:
            print(f"  {row['snippet']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--out")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("index")
    p.add_argument("--enrich", action="store_true", help="Fetch public mod details via Nexus API using NEXUS_API_KEY")
    p.add_argument("--refresh-nexus", action="store_true", help="Refetch Nexus data even if central cache already has it")
    p.add_argument("--nexus-ttl", type=float, default=168, help="Re-fetch Nexus entries older than this many hours (default 168 = 7d; 0 = always fetch)")
    p.add_argument("--limit", type=int)
    p.add_argument("--delay", type=float, default=0.25)
    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    config = load_config(abs_path(args.config))
    db_path = Path(args.out) if args.out else project_db_path(config)
    if args.command == "index":
        index(abs_path(args.config), Path(args.out) if args.out else None, args.enrich, args.limit, args.delay, args.refresh_nexus, args.nexus_ttl)
    elif args.command == "search":
        search(db_path, args.query, args.limit)


if __name__ == "__main__":
    main()
