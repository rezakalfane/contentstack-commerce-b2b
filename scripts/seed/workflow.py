#!/usr/bin/env python3
"""Create the "Review before live" workflow and its production publishing rule (idempotent).

Usage:  python3 scripts/seed/workflow.py [--baseline]

  --baseline   also mark every existing entry (English and French) as Approved. Use it once on a stack whose content is
               already live, otherwise the publishing rule would lock all existing entries (they have no stage yet).

What it sets up (see docs/workflow.md):
  * workflow "Review before live" with stages Draft -> In review -> Approved on all content types of the main branch
  * a publishing rule: publishing to `production` is only allowed for entries in the Approved stage, by the Admin role
Nothing is changed if the workflow and rule already exist.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import seed  # noqa: E402

NAME = "Review before live"
ENVIRONMENT = "production"
LOCALES = ["en-us", "fr-fr"]


def lookup():
    roles = {r["name"]: r["uid"] for r in seed.api("GET", "/roles")["roles"]}
    envs = {e["name"]: e["uid"] for e in seed.api("GET", "/environments")["environments"]}
    cts = [c["uid"] for c in seed.api("GET", "/content_types", params={"limit": 100})["content_types"]]
    return roles, envs, cts


def stage(name, color, admin_only_role=None):
    """A stage open to everyone, or (for Approved) restricted to one role."""
    open_to_all = admin_only_role is None
    return {
        "name": name,
        "color": color,
        "SYS_ACL": {"roles": {"uids": [] if open_to_all else [admin_only_role]},
                    "users": {"uids": ["$all"] if open_to_all else []}, "others": {}},
        "next_available_stages": ["$all"],
        "allow_all_stages": True,
        "allow_all_users": open_to_all,
        "entry_lock": "$none",
    }


def ensure_workflow(cts, admin):
    for wf in seed.api("GET", "/workflows").get("workflows", []):
        if wf["name"] == NAME:
            print(f"workflow exists: {NAME} ({wf['uid']}), enabled={wf.get('enabled')}")
            return wf
    body = {"workflow": {
        "name": NAME,
        "description": "Entries start as Draft, are checked on the staging site (preview), and only Approved entries "
                       "can be published to production.",
        "enabled": True, "branches": ["main"], "content_types": cts, "admin_users": {"users": []},
        "workflow_stages": [stage("Draft", "#8a96a3"), stage("In review", "#f7b500"), stage("Approved", "#1c7d52", admin)],
    }}
    wf = seed.api("POST", "/workflows", body=body)["workflow"]
    print(f"workflow created: {NAME} ({wf['uid']})")
    return wf


def ensure_rule(wf, env_uid, admin, cts):
    approved = next(s["uid"] for s in wf["workflow_stages"] if s["name"] == "Approved")
    for r in seed.api("GET", "/workflows/publishing_rules").get("publishing_rules", []):
        if r.get("workflow") == wf["uid"] and r.get("environment") == env_uid:
            print(f"publishing rule exists: {r['uid']}")
            return approved
    # Notes: the endpoint is `publishing_rules`; `content_types` must be listed (the workflow is not "all");
    # approvers are plain role/user UIDs (a user must be a real stack member, so a role is used).
    body = {"publishing_rule": {
        "workflow": wf["uid"], "actions": [], "branches": ["main"], "content_types": cts, "locales": LOCALES,
        "environment": env_uid, "approvers": {"users": [], "roles": [admin]},
        "workflow_stage": approved, "disable_approver_publishing": False,
    }}
    r = seed.api("POST", "/workflows/publishing_rules", body=body)["publishing_rule"]
    print(f"publishing rule created: {r['uid']}  ({ENVIRONMENT} requires the Approved stage)")
    return approved


def baseline(approved_uid):
    ordered = ["author", "hero_banner", "faq", "blog_landing_page", "buying_guide", "product_spotlight",
               "announcement_bar", "site_navigation", "blog_listing_page", "page"]
    moved = skipped = 0
    for ct in ordered:
        for loc in LOCALES:
            for e in seed.api("GET", f"/content_types/{ct}/entries", params={"locale": loc, "limit": 100, "include_workflow": "true"})["entries"]:
                if (e.get("_workflow") or {}).get("uid") == approved_uid:
                    skipped += 1
                    continue
                seed.api("POST", f"/content_types/{ct}/entries/{e['uid']}/workflow", params={"locale": loc},
                         body={"workflow": {"workflow_stage": {"comment": "Baseline: already live", "due_date": "",
                                                                  "notify": False, "uid": approved_uid}}})
                moved += 1
    print(f"baseline: {moved} entries moved to Approved, {skipped} already were")


def main():
    roles, envs, cts = lookup()
    admin = roles["Admin"]
    wf = ensure_workflow(cts, admin)
    approved = ensure_rule(wf, envs[ENVIRONMENT], admin, cts)
    if "--baseline" in sys.argv:
        baseline(approved)


if __name__ == "__main__":
    main()
