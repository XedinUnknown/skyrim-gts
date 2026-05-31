#!/usr/bin/env python3
"""Fetch Gate to Sovngarde wiki source pages via MediaWiki API."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


API_URL = "https://gatetosovngarde.wiki.gg/api.php"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "wiki-cache"
USER_AGENT = "skyrim-gts-skill/1.0 (public wiki sync)"


def safe_name(title: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", title.strip()).strip("_")
    return name or "page"


def api_get(params: dict[str, str], retries: int = 3) -> dict:
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt >= retries:
                raise
            retry_after = error.headers.get("Retry-After")
            sleep_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 5 * (attempt + 1)
            time.sleep(sleep_seconds)
    raise RuntimeError("unreachable retry state")


def list_pages() -> list[str]:
    titles: list[str] = []
    params = {
        "action": "query",
        "list": "allpages",
        "apnamespace": "0",
        "aplimit": "max",
        "format": "json",
    }

    while True:
        data = api_get(params)
        pages = data.get("query", {}).get("allpages", [])
        titles.extend(page["title"] for page in pages if "title" in page)
        cont = data.get("continue", {})
        if "apcontinue" not in cont:
            return titles
        params["apcontinue"] = cont["apcontinue"]


def fetch_page(title: str) -> tuple[str | None, str | None]:
    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
    }
    data = api_get(params)

    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if "missing" in page:
            return None, f"missing: {title}"
        revisions = page.get("revisions") or []
        if not revisions:
            return None, f"no revisions: {title}"
        slots = revisions[0].get("slots", {})
        content = slots.get("main", {}).get("*")
        if content is None:
            return None, f"no content: {title}"
        return content, None
    return None, f"not found: {title}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("titles", nargs="*", help="Wiki page titles to fetch")
    parser.add_argument("--all", action="store_true", help="Fetch all public article pages")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory")
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between page fetches in seconds")
    args = parser.parse_args()

    if not args.all and not args.titles:
        parser.error("provide page titles or use --all")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    titles = list_pages() if args.all else args.titles
    errors: list[str] = []
    manifest: list[dict[str, str]] = []
    for title in titles:
        content, error = fetch_page(title)
        if error:
            errors.append(error)
            continue
        path = out / f"{safe_name(title)}.wiki"
        path.write_text(content + "\n", encoding="utf-8")
        manifest.append(
            {
                "title": title,
                "file": path.name,
                "source": f"https://gatetosovngarde.wiki.gg/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
            }
        )
        print(path)
        if args.delay > 0:
            time.sleep(args.delay)

    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(manifest_path)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
