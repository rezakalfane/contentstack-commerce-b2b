#!/usr/bin/env python3
"""Save the content types and all entries (every locale) as JSON before a destructive change such as `prune.py --run`.
Usage: python3 tools/contentstack/backup.py   -> .backups/contentstack-<timestamp>.json (gitignored; never commit it)
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import seed  # noqa: E402

LOCALES = ("en-us", "fr-fr")


def main():
    cts = seed.api("GET", "/content_types", params={"limit": 100})["content_types"]
    entries = {}
    for ct in cts:
        for loc in LOCALES:
            entries[f"{ct['uid']}:{loc}"] = seed.api("GET", f"/content_types/{ct['uid']}/entries", params={"locale": loc, "limit": 100}).get("entries", [])
    out = os.path.join(seed.ROOT, ".backups")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"contentstack-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    with open(path, "w") as f:
        json.dump({"content_types": cts, "entries": entries}, f)
    print(f"saved {len(cts)} content types, {sum(map(len, entries.values()))} entries -> {os.path.relpath(path, seed.ROOT)}")


if __name__ == "__main__":
    main()
