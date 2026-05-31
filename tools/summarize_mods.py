#!/usr/bin/env python3
"""Export mod data for AI summarization, then import the results.

Usage
-----
  # One-shot: export → pipe through opencode → import
  python3 tools/summarize_mods.py --export | \\
    opencode run --command summarize-mods | \\
    python3 tools/summarize_mods.py --import

  # Or two-phase for inspection / restart:
  python3 tools/summarize_mods.py --export > /tmp/mods.txt
  opencode run --command summarize-mods "$(cat /tmp/mods.txt)" \\
    > /tmp/summaries.txt
  python3 tools/summarize_mods.py --import < /tmp/summaries.txt
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "gts-index.config.json"
SUMMARIZE_COMMAND = ROOT / ".opencode" / "commands" / "summarize-mods.md"

BATCH_SIZE = int(os.environ.get("MOD_SUMMARY_BATCH_SIZE", "20"))
MAX_DESC = 1200


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def load_config(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    config.setdefault("mod_metadata_dir", "cache/gts-mod-metadata-index")
    config.setdefault("db_path", "cache/gts-index/gts.sqlite")
    config.setdefault("mod_metadata_cache_db", str(Path.home() / ".cache" / "skyrim-gts" / "mod-metadata-cache.sqlite"))
    return config


def abs_path(value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else ROOT / path


def project_db_path(config: dict[str, object]) -> Path:
    return abs_path(os.environ.get("GTS_DB", str(config.get("db_path", "cache/gts-index/gts.sqlite"))))


def central_cache_path(config: dict[str, object]) -> Path:
    return abs_path(os.environ.get("GTS_MOD_METADATA_CACHE_DB", str(config.get("mod_metadata_cache_db", ""))))


def connect_central_cache(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, timeout=60)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout = 60000")
    try:
        con.execute("select ai_summary from mod_cache limit 0")
    except sqlite3.OperationalError:
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


def connect_project(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, timeout=60)
    con.row_factory = sqlite3.Row
    con.execute("pragma journal_mode = wal")
    try:
        con.execute("select ai_summary from mods limit 0")
    except sqlite3.OperationalError:
        try:
            con.execute("alter table mods add column ai_summary text")
        except sqlite3.OperationalError:
            pass
    for ddl in [
        "alter table mods add column category text",
        "alter table mods add column nexus_category text",
    ]:
        try:
            con.execute(ddl)
        except sqlite3.OperationalError:
            pass
    return con


def mods_to_summarize(con: sqlite3.Connection, force: bool = False) -> list[sqlite3.Row]:
    summary_filter = "" if force else "and (m.ai_summary is null or m.ai_summary = '')"
    return con.execute(
        f"""
        select m.id, m.cache_key, m.name, m.mod_class,
               coalesce(m.nexus_summary, '') as nexus_summary,
               coalesce(m.description_text, '') as description_text,
               coalesce(m.comments, '') as comments
        from mods m
        join plugins a on a.mod_id = m.id
        where a.enabled = 1
          and (m.nexus_summary != '' or m.description_text != '' or m.comments != '')
          {summary_filter}
        group by m.id
        order by m.name
        """
    ).fetchall()


def strip_urls(text: str) -> str:
    return re.sub(r"https?://\S+", "", text)


def clean_nexus_desc(text: str) -> str:
    text = strip_urls(text)
    text = re.sub(r"\[/?font[^\]]*\]", "", text, flags=re.I)
    text = re.sub(r"\[/?youtube[^\]]*\]", "", text, flags=re.I)
    text = re.sub(r"\[img[^\]]*\].*?\[/img\]", "", text, flags=re.I | re.S)
    text = re.sub(r"\[/?video[^\]]*\]", "", text, flags=re.I)
    text = re.sub(r"\[/?(?:b|i|u|center|left|right|size|color|spoiler|list|\*)[^\]]*\]", "", text, flags=re.I)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def format_text(row: sqlite3.Row) -> str:
    parts = []
    important = (row["mod_class"] or "other") in {"gameplay", "quest"}
    if row["nexus_summary"]:
        parts.append(f"Nexus: {strip_urls(row['nexus_summary'])}")
    if row["description_text"]:
        desc = clean_nexus_desc(row["description_text"]) if important else strip_urls(row["description_text"][:MAX_DESC])
        parts.append(f"Description: {desc}")
    if row["comments"]:
        parts.append(f"Comments: {strip_urls(row['comments'][:500])}")
    desc = "\n".join(parts)
    return f"name: {row['name']}\nclass: {row['mod_class'] or 'other'}\ndescription: {desc}"


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def decode_summary(text: str) -> str:
    return text.replace("\\n", "\n").replace("\\t", "\t").strip()


def preview_output(text: str | bytes | None, limit: int = 2000) -> str:
    if text is None:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    text = strip_ansi(text).strip()
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text


def load_command_template(path: Path = SUMMARIZE_COMMAND) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2]
    return text.strip()


def append_log(log_path: Path | None, heading: str, text: str | bytes | None) -> None:
    if log_path is None or text is None:
        return
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    text = strip_ansi(text).rstrip()
    if not text:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n\n## {heading}\n\n")
        handle.write(text)
        handle.write("\n")


def row_has(row: sqlite3.Row, key: str) -> bool:
    return key in row.keys()


def cache_mods_to_summarize(con: sqlite3.Connection, force: bool = False) -> list[sqlite3.Row]:
    summary_filter = "" if force else "and (ai_summary is null or ai_summary = '')"
    return con.execute(
        f"""
        select rowid as mod_index, display_name as name, coalesce(mod_class, 'other') as mod_class,
               coalesce(nexus_summary, '') as nexus_summary,
               coalesce(description_text, '') as description_text,
               coalesce(comments, '') as comments,
               cache_key
        from mod_cache
        where (nexus_summary != '' or description_text != '' or comments != '')
          {summary_filter}
        order by display_name
        """
    ).fetchall()


def cache_mods_by_ids(con: sqlite3.Connection, modids: list[int]) -> list[sqlite3.Row]:
    placeholders = ",".join("?" for _ in modids)
    return con.execute(
        f"""
        select rowid as mod_index, display_name as name, coalesce(mod_class, 'other') as mod_class,
               coalesce(nexus_summary, '') as nexus_summary,
               coalesce(description_text, '') as description_text,
               coalesce(comments, '') as comments,
               cache_key
        from mod_cache
        where modid in ({placeholders})
        order by display_name
        """,
        modids,
    ).fetchall()


def overlay_project_classes(rows: list[sqlite3.Row], project_db: Path | None) -> list[dict[str, object]]:
    if project_db is None or not project_db.exists():
        return [dict(row) for row in rows]
    con = connect_project(project_db)
    by_key = {
        row["cache_key"]: row["mod_class"]
        for row in con.execute("select cache_key, mod_class from mods where cache_key is not null")
    }
    con.close()
    result: list[dict[str, object]] = []
    for row in rows:
        item = dict(row)
        item["mod_class"] = by_key.get(item.get("cache_key"), item.get("mod_class") or "other")
        result.append(item)
    return result


def name_cache_key_map(con: sqlite3.Connection, modids: list[int] | None = None) -> dict[str, str]:
    if modids:
        placeholders = ",".join("?" for _ in modids)
        rows = con.execute(
            f"select display_name, cache_key from mod_cache where modid in ({placeholders})",
            modids,
        ).fetchall()
    else:
        rows = con.execute(
            "select display_name, cache_key from mod_cache"
        ).fetchall()
    mapping: dict[str, str] = {}
    for r in rows:
        name = r["display_name"]
        if name and name not in mapping:
            mapping[name] = r["cache_key"]
    return mapping


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

def cmd_export(config_path: Path, metadata_db_path: Path | None,
                limit: int | None, cls_filter: str | None,
                global_: bool = False, modids: list[int] | None = None,
                force: bool = False) -> None:
    config = load_config(config_path)
    if global_ or modids:
        cache_path = central_cache_path(config)
        cache_con = connect_central_cache(cache_path)
        if modids:
            rows = cache_mods_by_ids(cache_con, modids)
        else:
            rows = cache_mods_to_summarize(cache_con, force=force)
        if modids:
            rows = overlay_project_classes(rows, metadata_db_path or project_db_path(config))
        cache_con.close()
        source = "central cache"
    else:
        db_path = metadata_db_path or project_db_path(config)
        con = connect_project(db_path)
        rows = mods_to_summarize(con, force=force)
        con.close()
        source = "project DB"

    if cls_filter:
        rows = [r for r in rows if r["mod_class"] == cls_filter]
    if limit is not None:
        rows = rows[:limit]

    if not rows:
        print("No mods to summarize.", file=sys.stderr, flush=True)
        return

    print(f"Exporting {len(rows)} mods from {source} in batches of {BATCH_SIZE}.",
          file=sys.stderr, flush=True)

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        for row in batch:
            print("---")
            print(format_text(row))
        print("__BATCH_END__")


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------

def cmd_import(config_path: Path, metadata_db_path: Path | None,
               global_: bool = False, modids: list[int] | None = None) -> int:
    config = load_config(config_path)
    cache_path = central_cache_path(config)
    cache_con = connect_central_cache(cache_path)

    if global_ or modids:
        con = None
        name_to_key = name_cache_key_map(cache_con, modids)
    else:
        db_path = metadata_db_path or project_db_path(config)
        con = connect_project(db_path)
        name_to_key = None

    summary_map: dict[str, str] = {}
    line_no = 0
    for raw in sys.stdin:
        raw = strip_ansi(raw).strip()
        line_no += 1
        if not raw:
            continue
        colon = raw.find(": ")
        if colon < 1:
            continue
        name = raw[:colon].strip()
        summary = raw[colon + 2:].strip()
        if summary:
            summary_map[name] = decode_summary(summary)

    imported = 0
    for name, summary in summary_map.items():
        cache_key = (name_to_key or {}).get(name) if (global_ or modids) else None
        if cache_key:
            cache_con.execute("update mod_cache set ai_summary = ? where cache_key = ?",
                              (summary, cache_key))
            imported += 1
        elif con:
            cur = con.execute("select id, cache_key from mods where name = ?", (name,))
            row = cur.fetchone()
            if row:
                con.execute("update mods set ai_summary = ? where id = ?",
                            (summary, row["id"]))
                cache_con.execute("update mod_cache set ai_summary = ? where cache_key = ?",
                                  (summary, row["cache_key"]))
                imported += 1

    if con:
        con.commit()
        con.close()
    cache_con.commit()
    cache_con.close()

    dest = "central cache" if (global_ or modids) else f"local DB ({db_path}) and central cache"
    print(f"Imported {imported} summaries into {dest} ({cache_path}).",
          file=sys.stderr)
    return imported


# ---------------------------------------------------------------------------
# run (export → opencode → import in one step)
# ---------------------------------------------------------------------------

def cmd_run(config_path: Path, metadata_db_path: Path | None,
            limit: int | None, cls_filter: str | None,
            opencode_cmd: str, opencode_model: str | None,
            global_: bool = False, modids: list[int] | None = None,
            force: bool = False, timeout: int = 120,
            log_path: Path | None = None) -> int:
    config = load_config(config_path)
    db_path = metadata_db_path or project_db_path(config)
    cache_path = central_cache_path(config)
    cache_con = connect_central_cache(cache_path)

    if global_ or modids:
        if modids:
            rows = cache_mods_by_ids(cache_con, modids)
        else:
            rows = cache_mods_to_summarize(cache_con, force=force)
        if modids:
            rows = overlay_project_classes(rows, db_path)
        con = None
        name_to_key = name_cache_key_map(cache_con, modids if modids else None)
        source = "central cache"
    else:
        con = connect_project(db_path)
        rows = mods_to_summarize(con, force=force)
        con.close()
        name_to_key = None
        source = "project DB"

    if cls_filter:
        rows = [r for r in rows if r["mod_class"] == cls_filter]
    if limit is not None:
        rows = rows[:limit]

    if not rows:
        print("No mods to summarize.", file=sys.stderr)
        return 0

    total = len(rows)
    success = 0
    failed = 0
    t_start = time.time()
    print(f"Summarizing {total} mods from {source} via opencode (batches of {BATCH_SIZE})",
          file=sys.stderr, flush=True)
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            f"# summarize_mods log\n\nsource={source}\ntotal={total}\nmodel={opencode_model}\ntimeout={timeout}\n",
            encoding="utf-8",
        )
        print(f"Raw opencode output will be written to {log_path}", file=sys.stderr, flush=True)

    for i in range(0, total, BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        t_batch = time.time()

        lines = []
        for row in batch:
            lines.append("---")
            lines.append(format_text(row))
        batch_text = "\n".join(lines)

        print(f"  [batch {batch_num}/{total_batches}] "
              f"processing {len(batch)} mods...",
              file=sys.stderr, flush=True)
        try:
            prompt = load_command_template().replace("$ARGUMENTS", batch_text)
            opencode_args = [opencode_cmd, "run"]
            if opencode_model:
                opencode_args += ["-m", opencode_model]
            result = subprocess.run(
                opencode_args,
                input=prompt, capture_output=True, text=True, timeout=timeout,
            )
            elapsed = time.time() - t_batch

            if result.returncode != 0:
                print(f"  [batch {batch_num}/{total_batches}] "
                      f"FAILED ({elapsed:.0f}s) "
                      f"opencode exited {result.returncode}",
                      file=sys.stderr, flush=True)
                append_log(log_path, f"batch {batch_num} failed stdout", result.stdout)
                append_log(log_path, f"batch {batch_num} failed stderr", result.stderr)
                failed += len(batch)
                continue

            stdout = strip_ansi(result.stdout)
            parsed_pairs: list[tuple[str, str]] = []
            for raw in stdout.splitlines():
                raw = raw.strip()
                colon = raw.find(": ")
                if colon < 1:
                    continue
                name = raw[:colon].strip()
                summary = decode_summary(raw[colon + 2:].strip())
                if not summary:
                    continue
                parsed_pairs.append((name, summary))

            parsed = 0
            used_fallback = 0
            batch_by_name = {row["name"]: row for row in batch}
            for index, (name, summary) in enumerate(parsed_pairs[:len(batch)]):
                batch_row = batch_by_name.get(name)
                if batch_row is None and index < len(batch):
                    batch_row = batch[index]
                    used_fallback += 1
                cache_key = None
                if batch_row is not None:
                    cache_key = batch_row["cache_key"]
                elif global_ or modids:
                    cache_key = (name_to_key or {}).get(name)
                if cache_key:
                    cache_con.execute(
                        "update mod_cache set ai_summary = ? where cache_key = ?",
                        (summary, cache_key),
                    )
                    cache_con.commit()
                    parsed += 1
                    if batch_row is not None and row_has(batch_row, "id"):
                        con2 = connect_project(db_path)
                        con2.execute(
                            "update mods set ai_summary = ? where id = ?",
                            (summary, batch_row["id"]),
                        )
                        con2.commit()
                        con2.close()
                elif not (global_ or modids):
                    con2 = connect_project(db_path)
                    cur = con2.execute(
                        "select id, cache_key from mods where name = ?", (name,)
                    )
                    row = cur.fetchone()
                    if row:
                        con2.execute(
                            "update mods set ai_summary = ? where id = ?",
                            (summary, row["id"]),
                        )
                        con2.commit()
                        cache_con.execute(
                            "update mod_cache set ai_summary = ? where cache_key = ?",
                            (summary, row["cache_key"]),
                        )
                        cache_con.commit()
                        parsed += 1
                    con2.close()

            if parsed < len(batch):
                append_log(log_path, f"batch {batch_num} unparsed stdout", stdout)
                if log_path:
                    print(f"  unparsed output logged to {log_path}", file=sys.stderr, flush=True)
            elif used_fallback and log_path:
                append_log(log_path, f"batch {batch_num} name fallback stdout", stdout)

            success += parsed
            failed += len(batch) - parsed
            done_frac = (i + len(batch)) / total
            eta = (time.time() - t_start) / done_frac * (1 - done_frac)
            eta_str = f"{eta/60:.0f}m" if eta > 60 else f"{eta:.0f}s"
            print(f"  [batch {batch_num}/{total_batches}] "
                  f"{parsed}/{len(batch)} parsed "
                  f"({elapsed:.0f}s · "
                  f"{success}/{success+failed} total · "
                  f"ETA {eta_str})",
                  file=sys.stderr, flush=True)

        except subprocess.TimeoutExpired as exc:
            elapsed = time.time() - t_batch
            print(f"  [batch {batch_num}/{total_batches}] "
                  f"TIMEOUT ({elapsed:.0f}s)",
                  file=sys.stderr, flush=True)
            append_log(log_path, f"batch {batch_num} timeout partial stdout", exc.stdout)
            append_log(log_path, f"batch {batch_num} timeout partial stderr", exc.stderr)
            if log_path:
                print(f"  partial output logged to {log_path}", file=sys.stderr, flush=True)
            failed += len(batch)
        except FileNotFoundError:
            print(f"Error: '{opencode_cmd}' not found. Install opencode.",
                  file=sys.stderr, flush=True)
            return 1

    t_total = time.time() - t_start
    print(f"[done] {success} summarized, {failed} failed "
          f"in {t_total/60:.1f}m",
          file=sys.stderr, flush=True)

    print(f"[done] {success} summarized, {failed} failed",
          file=sys.stderr, flush=True)
    cache_con.close()
    return success


# ---------------------------------------------------------------------------
# cli
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--metadata-db")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--class", dest="cls_filter")
    parser.add_argument("--opencode", default="opencode",
                        help="Path to opencode CLI binary")
    parser.add_argument("--log-file", default="cache/gts-index/mod-summarize.log",
                        help="Write raw opencode output/debug details here")

    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in [("export", "Print mod data to stdout for piping to opencode"),
                             ("import", "Read opencode output from stdin and store in DB"),
                             ("run", "Export → call opencode → import in one step")]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--global", "-g", action="store_true", dest="global_",
                       help="Summarize all mods in central cache, not just active game mods")
        p.add_argument("--modids", type=str,
                       help="Comma-separated Nexus mod IDs to summarize (from central cache)")
        if name in {"export", "run"}:
            p.add_argument("--force", action="store_true",
                           help="Regenerate summaries even when ai_summary already exists")
        if name == "run":
            p.add_argument("--model", type=str, default="nvidia/nvidia/nemotron-3-nano-30b-a3b",
                           help="Model to use (default: nvidia/nvidia/nemotron-3-nano-30b-a3b)")
            p.add_argument("--timeout", type=int, default=120,
                           help="Seconds before aborting each opencode batch (default: 120)")

    args = parser.parse_args()

    modids: list[int] | None = None
    if args.modids:
        try:
            modids = [int(x.strip()) for x in args.modids.split(",") if x.strip()]
        except ValueError:
            parser.error("--modids must be comma-separated integers")

    kwargs = {
        "config_path": abs_path(args.config),
        "metadata_db_path": abs_path(args.metadata_db) if args.metadata_db else None,
        "limit": args.limit,
        "cls_filter": args.cls_filter,
        "global_": args.global_,
        "modids": modids,
        "force": getattr(args, "force", False),
    }

    if args.command == "export":
        cmd_export(**kwargs)
    elif args.command == "import":
        cmd_import(config_path=kwargs["config_path"],
                   metadata_db_path=kwargs["metadata_db_path"],
                   global_=kwargs["global_"],
                   modids=kwargs["modids"])
    elif args.command == "run":
        cmd_run(opencode_cmd=args.opencode, opencode_model=args.model,
                timeout=args.timeout,
                log_path=abs_path(args.log_file) if args.log_file else None,
                **kwargs)


if __name__ == "__main__":
    main()
