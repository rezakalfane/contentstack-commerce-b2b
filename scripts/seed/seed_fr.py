#!/usr/bin/env python3
"""Create and publish the French (fr-fr) localized versions of every entry. Idempotent.
Usage: python3 scripts/seed/seed_fr.py [--only author,faq,...]

For each English entry it fetches the master, overrides the translated fields and saves it as an fr-fr
localization (PUT ...?locale=fr-fr). Non-text fields (images, references, dates, enums) are inherited.
"""
import copy
import os
import sys
import textwrap

sys.path.insert(0, os.path.dirname(__file__))
import seed  # noqa: E402
from content import AUTHORS, POSTS  # noqa: E402
from content_extra import ANNOUNCEMENTS, FAQS, GUIDES, HOME, NAV, SPOTLIGHTS  # noqa: E402
from content_fr import (  # noqa: E402
    ANNOUNCEMENTS_FR, AUTHOR_BIOS_FR, BLOG_LISTING_FR, FAQS_FR, GUIDES_FR, HEROES_FR, HOME_FR, NAV_FR,
    PAGES_FR, SPOTLIGHT_SUMMARY_FR, SPOTLIGHTS_FR, THEME_KEYWORDS_FR,
)
from content_fr_posts import POSTS_FR  # noqa: E402

FR = "fr-fr"
EN = seed.LOCALE
DROP = {"uid", "created_at", "updated_at", "created_by", "updated_by", "ACL", "locale", "publish_details", "tags"}
rte = seed.rte
published = []  # (content_type, uid) in publish order


def normalize(v):
    """Asset objects (as returned by GET) -> bare asset UIDs (as expected by PUT), recursively."""
    if isinstance(v, dict):
        if "filename" in v and "uid" in v and "url" in v:
            return v["uid"]
        return {k: normalize(x) for k, x in v.items()}
    if isinstance(v, list):
        return [normalize(x) for x in v]
    return v


def uid_of(ct, en_title):
    uid = seed.find_entry(ct, en_title)
    if not uid:
        sys.exit(f"English entry not found: {ct} / {en_title!r} (run the English seeds first)")
    return uid


def localize(ct, en_title, mutate):
    uid = uid_of(ct, en_title)
    master = seed.api("GET", f"/content_types/{ct}/entries/{uid}", params={"locale": EN})["entry"]
    entry = {k: normalize(copy.deepcopy(v)) for k, v in master.items() if k not in DROP and not k.startswith("_")}
    mutate(entry)
    seed.api("PUT", f"/content_types/{ct}/entries/{uid}", body={"entry": entry}, params={"locale": FR})
    published.append((ct, uid))
    return uid


def section(name, only):
    return only is None or name in only


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))

    # ---- authors
    if section("author", only):
        print("== authors")
        for a, bio in zip(AUTHORS, AUTHOR_BIOS_FR):
            localize("author", a["name"], lambda e, bio=bio: e.update(bio=bio))
        print(f"  {len(AUTHORS)} authors")

    # ---- hero banners
    en_hero_titles = {"home": "Commerce B2B", "faq": "Frequently asked questions", "guides": "Buying guides", "blog": "The B2B Commerce Blog"}
    if section("hero_banner", only):
        print("== hero banners")
        for key, (title, desc, cta, href) in HEROES_FR.items():
            def m(e, title=title, desc=desc, cta=cta, href=href):
                e.update(title=title, banner_description=desc, call_to_action={"title": cta, "href": href})
            localize("hero_banner", en_hero_titles[key], m)
            print(f"  {title}")

    # ---- blog posts (ascending, so referenced posts publish first)
    if section("blog_landing_page", only):
        print("== blog posts")
        flat = [(ai, pi, p) for ai, posts in enumerate(POSTS) for pi, p in enumerate(posts)]
        flat_fr = [p for posts in POSTS_FR for p in posts]
        for idx, ((ai, pi, en), fr) in enumerate(zip(flat, flat_fr)):
            title, intro, s1, s2, takeaways = fr

            def m(e, title=title, intro=intro, s1=s1, s2=s2, takeaways=takeaways, ai=ai):
                e["title"] = title
                e["body"] = rte([
                    ("p", intro), ("h2", s1[0]), ("p", s1[1]), ("h2", s2[0]), ("p", s2[1]),
                    ("h2", "À retenir"), ("ul", takeaways),
                ])
                e["seo"] = {
                    "meta_title": title,
                    "meta_description": textwrap.shorten(intro, 155, placeholder="…"),
                    "keywords": "commerce b2b, " + THEME_KEYWORDS_FR[ai],
                    "enable_search_indexing": True,
                }
            localize("blog_landing_page", en[0], m)
        print(f"  {len(flat)} posts")

    # ---- blog listing page
    if section("blog_listing_page", only):
        print("== blog listing")
        L = BLOG_LISTING_FR

        def m(e):
            e["title"] = L["title"]
            e["search"] = {"placeholder_text": L["placeholder"], "search_button": {"title": L["search_button"], "href": "/blog"}}
            for comp in e.get("page_components", []):
                if "from_blog" in comp:
                    comp["from_blog"]["title_h2"] = L["from_blog_title"]
                    comp["from_blog"]["view_articles"] = {"title": L["view_articles"], "href": "/blog"}
                if "widget" in comp:
                    comp["widget"]["title_h2"] = L["widget_title"]
        localize("blog_listing_page", "Blog", m)

    # ---- FAQs
    if section("faq", only):
        print("== faqs")
        for (topic, q_en, *_), (q_fr, answers) in zip(FAQS, FAQS_FR):
            localize("faq", q_en, lambda e, q=q_fr, a=answers: e.update(title=q, answer=rte([("p", t) for t in a])))
        print(f"  {len(FAQS)} faqs")

    # ---- buying guides
    if section("buying_guide", only):
        print("== buying guides")
        for g, gf in zip(GUIDES, GUIDES_FR):
            def m(e, gf=gf):
                e["title"] = gf["title"]
                e["summary"] = gf["summary"]
                e["steps"] = [{"step_title": t, "step_body": b, "pro_tip": tip or ""} for t, b, tip in gf["steps"]]
                e["checklist"] = gf["checklist"]
            localize("buying_guide", g["title"], m)
            print(f"  {gf['title'][:60]}")

    # ---- product spotlights
    if section("product_spotlight", only):
        print("== product spotlights")
        for sp, (tagline, feats, uses) in zip(SPOTLIGHTS, SPOTLIGHTS_FR):
            def m(e, tagline=tagline, feats=feats, uses=uses):
                e["tagline"] = tagline
                e["editorial_summary"] = rte([("p", tagline + "."), ("p", SPOTLIGHT_SUMMARY_FR)])
                e["key_features"] = feats
                e["use_cases"] = [{"use_case": u, "description": d} for u, d in uses]
            localize("product_spotlight", sp[1], m)
        print(f"  {len(SPOTLIGHTS)} spotlights")

    # ---- announcement bars
    if section("announcement_bar", only):
        print("== announcement bars")
        for a, (title, msg, cta) in zip(ANNOUNCEMENTS, ANNOUNCEMENTS_FR):
            def m(e, title=title, msg=msg, cta=cta):
                e["title"] = title
                e["message"] = msg
                e["cta"] = {"title": cta, "href": e.get("cta", {}).get("href", "/faq")}
            localize("announcement_bar", a["title"], m)

    # ---- navigation
    if section("site_navigation", only):
        print("== navigation")
        N = NAV_FR

        def m(e):
            e["title"] = N["title"]
            e["header_links"] = [{"label": l, "href": h, "highlight": False} for l, h in N["header"]]
            e["footer_columns"] = [{"heading": h, "links": [{"label": l, "href": u} for l, u in links]} for h, links in N["footer"]]
            e["contact"] = {**e.get("contact", {}), "opening_hours": N["hours"]}
            e["legal_text"] = N["legal"]
        localize("site_navigation", NAV["title"], m)

    # ---- pages: home, FAQ, buying guides
    if section("page", only):
        print("== pages")

        def home(e):
            e["description"] = HOME_FR["description"]
            e["rich_text"] = HOME_FR["rich_text"]
            for blk, (t, copy_) in zip(e.get("blocks", []), HOME_FR["blocks"]):
                blk["block"]["title"] = t
                blk["block"]["copy"] = copy_
        localize("page", HOME["title"], home)
        for url, en_title in (("/faq", "FAQ"), ("/guides", "Buying Guides")):
            t, d = PAGES_FR[url]
            localize("page", en_title, lambda e, t=t, d=d: e.update(title=t, description=d))

    # ---- publish fr-fr (references publish before the entries that use them: order above is dependency-safe)
    print(f"== publishing fr-fr to '{seed.STACK_ENV}'")
    for ct, uid in published:
        seed.api("POST", f"/content_types/{ct}/entries/{uid}/publish",
                 body={"entry": {"environments": [seed.STACK_ENV], "locales": [FR]}, "locale": FR})
    print(f"  published {len(published)} entries")


if __name__ == "__main__":
    main()
