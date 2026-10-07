#!/usr/bin/env python3
"""Publish every asset and entry (English and French) to a Contentstack environment.

Usage:  python3 scripts/seed/publish_environment.py <environment> [--approve]      e.g.  production

Production is protected by a workflow publishing rule: only entries in the "Approved" stage can be published there
(see docs/workflow.md). Entries in Draft or In review are refused. `--approve` first moves every entry that is not yet
Approved into that stage, so this is an explicit developer decision ("I approve this content"), never a side effect.

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


def approved_stage():
    """UID of the 'Approved' stage of the enabled workflow, or None if there is no workflow."""
    for wf in seed.api("GET", "/workflows").get("workflows", []):
        for st in wf.get("workflow_stages", []):
            if wf.get("enabled") and st["name"] == "Approved":
                return st["uid"]
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    approve = "--approve" in sys.argv
    if len(args) != 1:
        sys.exit(__doc__)
    env = args[0]
    stage = approved_stage() if approve else None
    if approve and not stage:
        sys.exit("--approve given, but no enabled workflow with an 'Approved' stage was found.")
    approved_count = 0
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
                if approve:
                    cur = seed.api("GET", f"/content_types/{ct}/entries/{e['uid']}",
                                   params={"locale": loc, "include_workflow": "true"})["entry"]
                    if (cur.get("_workflow") or {}).get("uid") != stage:
                        try:
                            seed.api("POST", f"/content_types/{ct}/entries/{e['uid']}/workflow", params={"locale": loc},
                                     body={"workflow": {"workflow_stage": {"comment": "Approved by publish_environment.py --approve",
                                                                           "due_date": "", "notify": False, "uid": stage}}})
                            approved_count += 1
                        except SystemExit as err:
                            failures.append((ct, e["uid"], loc, "approve: " + str(err)[:140]))
                            continue
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
    if approve:
        print(f"Moved {approved_count} entr{'y' if approved_count == 1 else 'ies'} to Approved first.")
    if failures:
        print(f"{len(failures)} failure(s):")
        for f in failures[:12]:
            print("  ", f)
        sys.exit(1)


if __name__ == "__main__":
    main()
