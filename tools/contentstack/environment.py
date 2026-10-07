#!/usr/bin/env python3
"""Point the Live Preview base URLs of the stack environments at this site (idempotent).
Usage: python3 tools/contentstack/environment.py

Each environment has one base URL per locale (Settings > Environments), which Live Preview and the Visual Editor open for the
environment picked in the editor. The stack plan allows 3 environments (preview, local, production), so this site takes over
their base URLs instead of adding one: `preview` -> the staging site, `production` -> the production site; `local` is left alone.
The previous values are in .backups/contentstack-environments-*.json (written by the step that replaced them).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import seed  # noqa: E402

STAGING = os.environ.get("PREVIEW_STAGING", "https://content-commerce-b2b-git-staging-rza-kalfanes-projects.vercel.app").rstrip("/")
PRODUCTION = os.environ.get("PREVIEW_PRODUCTION", "https://content-commerce-b2b.vercel.app").rstrip("/")
TARGETS = {"preview": STAGING, "production": PRODUCTION}


def main():
    envs = {e["name"]: e for e in seed.api("GET", "/environments")["environments"]}
    for name, site in TARGETS.items():
        urls = [{"locale": "en-us", "url": site}, {"locale": "fr-fr", "url": f"{site}/fr"}]
        current = [{"locale": u["locale"], "url": u["url"].rstrip("/")} for u in envs[name].get("urls", [])]
        if sorted(current, key=lambda u: u["locale"]) == urls:
            print(f"  {name}: already points at {site}")
            continue
        seed.api("PUT", f"/environments/{name}", body={"environment": {"name": name, "servers": envs[name].get("servers", []), "urls": urls,
                                                                        "deploy_content": envs[name].get("deploy_content", True)}})
        print(f"  {name}: en-us -> {site}, fr-fr -> {site}/fr")


if __name__ == "__main__":
    main()
