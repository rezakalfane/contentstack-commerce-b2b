#!/usr/bin/env python3
"""Publish every asset and entry (English and French) to a Contentstack environment.

Usage:  python3 scripts/seed/publish_environment.py <environment>      e.g.  production

Safe to re-run: publishing an already published entry just republishes it. Entries are published in dependency order
(authors and banners before the pages that reference them), because Contentstack validates references on publish.
Reads credentials from ../../.env.local (never printed).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import seed  # noqa: E402

# Referenced types first; blog posts in creation order (a post only references earlier ones).
ORDER = [
    "author", "hero_banner", "faq", "blog_landing_page", "buying_guide",
    "product_spotlight", "announcement_bar", "site_navigation", "blog_listing_page", "page",
]
LOCALES = ["en-us", "fr-fr"]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    env = sys.argv[1]
    names = [e["name"] for e in seed.api("GET", "/environments")["environments"]]
    if env not in names:
        sys.exit(f"Unknown environment {env!r}. Available: {', '.join(names)}")

    # ---- assets (locale-independent files; published for the master locale, French falls back to it)
    assets = seed.api("GET", "/assets", params={"limit": 250})["assets"]
    for a in assets:
        seed.api("POST", f"/assets/{a['uid']}/publish", body={"asset": {"environments": [env], "locales": ["en-us"]}})
    print(f"assets: published {len(assets)} to {env}")

    # ---- entries
    failures = []
    totals = {loc: 0 for loc in LOCALES}
    for ct in ORDER:
        entries = seed.api("GET", f"/content_types/{ct}/entries", params={"locale": "en-us", "limit": 100})["entries"]
        entries.sort(key=lambda e: e["created_at"])
        counts = {loc: 0 for loc in LOCALES}
        for e in entries:
            for loc in LOCALES:
                try:
                    seed.api("POST", f"/content_types/{ct}/entries/{e['uid']}/publish",
                             body={"entry": {"environments": [env], "locales": [loc]}, "locale": loc})
                    counts[loc] += 1
                except SystemExit as err:  # seed.api exits with a redacted message on HTTP errors
                    failures.append((ct, e["uid"], loc, str(err)[:160]))
        for loc in LOCALES:
            totals[loc] += counts[loc]
        print(f"{ct:20s} {len(entries):3d} entries -> " + ", ".join(f"{loc}: {counts[loc]}" for loc in LOCALES))

    print(f"\nPublished to '{env}': " + ", ".join(f"{loc}: {n}" for loc, n in totals.items()))
    if failures:
        print(f"{len(failures)} failure(s):")
        for f in failures[:12]:
            print("  ", f)
        sys.exit(1)


if __name__ == "__main__":
    main()
