#!/usr/bin/env python3
"""Remove what the block-composed model replaced (the fixed layout of pages and posts). Dry run by default: lists what would go.

  page               image, rich_text, blocks, hero   (the page is now its `components`)
  blog_landing_page  body, related_post, is_archived, comments, social_share   (the post is now its `content` blocks)
  blog_listing_page, hero_banner   (entries, then the content types: the blog index and the heroes are pages now)

Run `backup.py` first, deploy the storefront that reads `components`/`content`, then `python3 tools/contentstack/prune.py --run`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import seed  # noqa: E402

FIELDS = {
    "page": ["image", "rich_text", "blocks", "hero"],
    "blog_landing_page": ["body", "related_post", "is_archived", "comments", "social_share"],
}
TYPES = ["blog_listing_page", "hero_banner"]


def main():
    run = "--run" in sys.argv
    have = {c["uid"] for c in seed.api("GET", "/content_types", params={"limit": 100})["content_types"]}
    for uid, drop in FIELDS.items():
        ct = seed.api("GET", f"/content_types/{uid}")["content_type"]
        gone = [f["uid"] for f in ct["schema"] if f["uid"] in drop]
        print(f"{uid}: remove {', '.join(gone) or 'nothing'}")
        if run and gone:
            ct["schema"] = [f for f in ct["schema"] if f["uid"] not in drop]
            seed.api("PUT", f"/content_types/{uid}", body={"content_type": {k: ct[k] for k in ("title", "uid", "description", "schema", "options")}})
    for uid in TYPES:
        if uid not in have:
            print(f"{uid}: already gone")
            continue
        n = {loc: len(seed.api("GET", f"/content_types/{uid}/entries", params={"locale": loc, "limit": 100}).get("entries", [])) for loc in ("en-us", "fr-fr")}
        print(f"{uid}: delete {n} entries, then the content type")
        if run:
            seed.api("DELETE", f"/content_types/{uid}", params={"force": "true"})
    if not run:
        print("(dry run: pass --run to apply)")


if __name__ == "__main__":
    main()
