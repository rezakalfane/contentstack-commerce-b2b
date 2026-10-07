#!/usr/bin/env python3
"""Add the block-composed model on top of the existing ContentStack content (idempotent, additive: the old fields stay filled).

Adds a `components` modular blocks field to `page` and `content` + `read_time` to `blog_landing_page` (the blog post type), then fills
them in both locales (en-us, fr-fr): the pages home, faq, guides and a new blog page (hero, text, feature and collection blocks,
mirroring the Amplience pages), and for every post a text block with the article. Publishes what it changes to the stack environment.
Usage: python3 tools/contentstack/blocks.py   (run seed.py, seed_extra.py and seed_fr.py first)
"""
import copy
import os
import sys
import textwrap

sys.path.insert(0, os.path.dirname(__file__))
import photos  # noqa: E402
import schemas as S  # noqa: E402
import seed  # noqa: E402
from content import POSTS  # noqa: E402
from content_extra import FAQS, GUIDES, HOME, SPOTLIGHTS  # noqa: E402
from content_fr import HEROES_FR, HOME_FR, PAGES_FR  # noqa: E402
from content_fr_posts import POSTS_FR  # noqa: E402

EN, FR = "en-us", "fr-fr"
DROP = {"uid", "created_at", "updated_at", "created_by", "updated_by", "ACL", "locale", "publish_details", "tags"}
KINDS = ["categories", "spotlights", "guides", "posts", "postListing", "guideListing", "faqs"]
IMG = seed.IMG_DIR


# ---------------------------------------------------------------- model
def blocks_field(uid, name, blocks):
    return S._base(uid, name, "blocks", multiple=True, non_localizable=False,
                   blocks=[{"title": t, "uid": u, "schema": schema} for u, t, schema in blocks],
                   field_metadata={"instruction": "", "description": ""})


def hero_schema():
    return [S.text("title", "Title", required=True), S.text("description", "Description", multiline=True), S.image("image", "Image"),
            S.image("second_image", "Second image (home variant)"), S.link("cta", "Call to action"),
            S.select("variant", "Variant", ["default", "home"], default="default")]


PAGE_BLOCKS = [
    ("hero", "Hero banner", hero_schema()),
    ("feature", "Feature block", [S.text("title", "Title", required=True), S.rte("copy", "Copy"), S.image("image", "Image"),
                                  S.select("layout", "Layout", ["image_left", "image_right"], default="image_left")]),
    ("text", "Text block", [S.rte("text", "Text", required=True)]),
    ("image", "Image block", [S.image("image", "Image", required=True), S.text("alt", "Alt text")]),
    ("video", "Video block", [S.text("video_title", "Video title"), S.text("src", "Video URL", required=True)]),
    ("collection", "Collection block", [
        S.select("kind", "Kind", KINDS, required=True, default="guides"), S.text("title", "Title"), S.text("link_label", "Link label"),
        S.text("search_placeholder", "Search placeholder"), S.text("search_button_label", "Search button label"),
        S.reference("items", "Items (guides, spotlights, posts or FAQs)", ["faq", "buying_guide", "product_spotlight", "blog_landing_page"])]),
]
POST_BLOCKS = [b for b in PAGE_BLOCKS if b[0] in ("text", "image", "video")]


def add_fields(ct_uid, fields):
    ct = seed.api("GET", f"/content_types/{ct_uid}")["content_type"]
    have = {f["uid"] for f in ct["schema"]}
    new = [f for f in fields if f["uid"] not in have]
    if not new:
        print(f"  {ct_uid}: model already up to date")
        return
    body = {"content_type": {k: ct[k] for k in ("title", "uid", "description", "options") if k in ct} | {"schema": ct["schema"] + new}}
    seed.api("PUT", f"/content_types/{ct_uid}", body=body)
    print(f"  {ct_uid}: added {[f['uid'] for f in new]}")


# ---------------------------------------------------------------- helpers
def normalize(v):
    """Asset objects (as GET returns them) -> bare asset UIDs (as PUT expects), recursively."""
    if isinstance(v, dict):
        if "filename" in v and "uid" in v and "url" in v:
            return v["uid"]
        return {k: normalize(x) for k, x in v.items()}
    if isinstance(v, list):
        return [normalize(x) for x in v]
    return v


def asset(path, title):
    return seed.find_asset(os.path.basename(path)) or seed.upload_asset(path, title)


def uids(ct):
    """title -> uid of every entry of a content type (English titles)."""
    out, skip = {}, 0
    while True:
        r = seed.api("GET", f"/content_types/{ct}/entries", params={"locale": EN, "limit": 100, "skip": skip})["entries"]
        out.update({e["title"]: e["uid"] for e in r})
        if len(r) < 100:
            return out
        skip += 100


def entry_of(ct, uid, locale):
    e = seed.api("GET", f"/content_types/{ct}/entries/{uid}", params={"locale": locale})["entry"]
    return {k: normalize(copy.deepcopy(v)) for k, v in e.items() if k not in DROP and not k.startswith("_")}


def put(ct, uid, entry, locale):
    seed.api("PUT", f"/content_types/{ct}/entries/{uid}", body={"entry": entry}, params={"locale": locale})


def publish(ct, uid, locale):
    seed.api("POST", f"/content_types/{ct}/entries/{uid}/publish", body={"entry": {"environments": [seed.STACK_ENV], "locales": [locale]}, "locale": locale})


def fresh_uids(node):
    """A copy of a JSON RTE document with new node uids (ContentStack rejects the same uid twice in one entry)."""
    import uuid
    if isinstance(node, dict):
        return {k: (uuid.uuid4().hex if k == "uid" else fresh_uids(v)) for k, v in node.items()}
    if isinstance(node, list):
        return [fresh_uids(x) for x in node]
    return node


def items(cts_uids):
    return [{"uid": u, "_content_type_uid": ct} for ct, u in cts_uids]


# ---------------------------------------------------------------- content
def page_components(key, lang, refs):
    """The blocks of a page in one language (`lang` is 0 for English, 1 for French)."""
    photo = {"home": ("mea_voiture", (780, 1040), "hero-home-photo.jpg"), "faq": ("alim", (1200, 900), "hero-faq-photo.jpg"),
             "guides": ("mea_pile", (1200, 900), "hero-guides-photo.jpg"), "blog": ("bat_moto", (1200, 900), "blog-hero-photo.jpg")}
    heroes = {
        "home": ("Commerce B2B", HOME["description"], "Browse buying guides", "/guides"),
        "faq": ("Frequently asked questions", "Quick answers for trade buyers on ordering, pricing and credit, delivery, accounts and fitment.", "Browse buying guides", "/guides"),
        "guides": ("Buying guides", "Practical, step-by-step checklists for matching the right battery to the job, for workshops, fleets and leisure buyers.", "Read the FAQ", "/faq"),
        "blog": ("The B2B Commerce Blog", "Practical guidance on pricing, ordering, integrations, payments, sales and headless storefronts for B2B commerce teams.", "Browse articles", "/blog"),
    }
    t, d, cta, href = heroes[key]
    tf, df, cf_, _ = HEROES_FR[key]
    name, size, file = photo[key]
    hero = {"title": (t, tf)[lang], "description": (d, df)[lang], "cta": {"title": (cta, cf_)[lang], "href": href},
            "image": asset(photos.crop(name, size, 0, os.path.join(IMG, file)), t), "variant": "home" if key == "home" else "default"}
    if key == "home":
        hero["second_image"] = asset(photos.crop("mea_moto", (780, 1040), 0, os.path.join(IMG, "home-second-photo.jpg")), t)
    out = [{"hero": hero}]

    def coll(kind, ids=(), **texts):
        c = {"kind": kind, "items": items(ids)}
        c.update({k: v[lang] for k, v in texts.items()})
        return {"collection": c}

    L = {"blog": seed_fr_blog()}
    if key == "home":
        out.append({"text": {"text": rte_html((HOME["rich_text"], HOME_FR["rich_text"])[lang])}})
        out.append(coll("categories", title=("Shop by category", "Acheter par catégorie")))
        for i, ((bt, copy_, layout, _), (bt_fr, copy_fr)) in enumerate(zip(HOME["blocks"], HOME_FR["blocks"])):
            p = os.path.join(IMG, f"home-block-photo-{i}.jpg")
            photos.crop(["mea_chargeur", "mea_outillage", "mea_solaire"][i], (1200, 800), 0, p)
            out.append({"feature": {"title": (bt, bt_fr)[lang], "copy": rte_html((copy_, copy_fr)[lang]), "image": asset(p, bt), "layout": layout}})
        out.append(coll("spotlights", refs["spotlights"], title=("Trade favourites", "Les favoris des pros")))
        out.append(coll("guides", refs["guides"], title=("From the buying guides", "Dans les guides d'achat"), link_label=("Buying guides", "Guides d'achat")))
    elif key == "faq":
        out.append(coll("faqs", refs["faqs"]))
    elif key == "guides":
        out.append(coll("guideListing", title=("Buying guides", "Guides d'achat")))
    else:
        out.append(coll("posts", refs["latest"], title=("Latest articles", L["blog"]["from_blog_title"])))
        out.append(coll("postListing", title=("All articles", "Tous les articles"),
                        search_placeholder=("Search articles", L["blog"]["placeholder"]), search_button_label=("Search", L["blog"]["search_button"])))
    return out


def seed_fr_blog():
    from content_fr import BLOG_LISTING_FR
    return BLOG_LISTING_FR


def rte_html(html):
    """Simple '<p>…</p><p>…</p>' HTML (with <a href> links) as a JSON RTE document."""
    import re
    import uuid

    def node(t, children, attrs=None):
        return {"type": t, "uid": uuid.uuid4().hex, "attrs": attrs or {}, "children": children}

    def inline(text):
        out, pos = [], 0
        for m in re.finditer(r'<a href="([^"]+)">(.*?)</a>', text):
            if m.start() > pos:
                out.append({"text": text[pos:m.start()]})
            out.append(node("a", [{"text": m.group(2)}], {"href": m.group(1), "target": "_self", "url": m.group(1)}))
            pos = m.end()
        if pos < len(text):
            out.append({"text": text[pos:]})
        return out

    paras = re.findall(r"<p>(.*?)</p>", html, flags=re.S)
    return {"type": "doc", "uid": uuid.uuid4().hex, "_version": 1, "attrs": {}, "children": [node("p", inline(p)) for p in paras]}


def main():
    print("== model")
    add_fields("page", [blocks_field("components", "Components (top to bottom)", PAGE_BLOCKS)])
    add_fields("blog_landing_page", [blocks_field("content", "Content blocks", POST_BLOCKS), S.number("read_time", "Read time (minutes)")])

    faq, guide, spot, post = uids("faq"), uids("buying_guide"), uids("product_spotlight"), uids("blog_landing_page")
    flat = [(ai, pi, p) for ai, posts in enumerate(POSTS) for pi, p in enumerate(posts)]
    post_ids = [post[t] for _ai, _pi, (t, *_r) in flat]
    refs = {
        "faqs": [("faq", faq[q]) for (_t, q, _p, _f) in FAQS],
        "guides": [("buying_guide", guide[g["title"]]) for g in GUIDES][:3],
        "spotlights": [("product_spotlight", spot[sp[1]]) for sp in SPOTLIGHTS if sp[7]][:3],
        "latest": [("blog_landing_page", post_ids[i]) for i in sorted(range(len(flat)), key=lambda i: -(flat[i][1] * 6 + flat[i][0]))[:3]],
    }

    print("== posts: the article becomes a text block")
    flat_fr = [p for posts in POSTS_FR for p in posts]
    for (ai, pi, (title, intro, s1, s2, _tk)), fr in zip(flat, flat_fr):
        uid = post[title]
        words = len(intro.split()) + len(s1[1].split()) + len(s2[1].split())
        for loc, text_ in ((EN, intro), (FR, fr[1])):
            e = entry_of("blog_landing_page", uid, loc)
            e.setdefault("seo", {})["meta_description"] = textwrap.shorten(text_, 180, placeholder="…")  # same summary length as the other seeds
            e["content"] = [{"text": {"text": fresh_uids(e["body"])}}]
            e["read_time"] = max(3, round(words * 3 / 200))
            put("blog_landing_page", uid, e, loc)
            publish("blog_landing_page", uid, loc)
    print(f"  {len(flat)} posts, both locales")

    print("== pages")
    pages = uids("page")
    for key, title in (("home", "Commerce B2B"), ("faq", "FAQ"), ("guides", "Buying Guides"), ("blog", "Blog")):
        if key == "blog" and "Blog" not in pages:
            t_fr, d_fr = "Blog", HEROES_FR["blog"][1]
            r = seed.api("POST", "/content_types/page/entries", params={"locale": EN}, body={"entry": {
                "title": "Blog", "url": "/blog", "description": "Practical guidance on pricing, ordering, integrations, payments, sales and headless storefronts for B2B commerce teams."}})
            pages["Blog"] = r["entry"]["uid"]
            created = True
        else:
            created = False
        uid = pages[title]
        for lang, loc in enumerate((EN, FR)):
            if loc == FR and created:
                e = {"title": "Blog", "url": "/blog", "description": HEROES_FR["blog"][1]}
            else:
                e = entry_of("page", uid, loc) if not (loc == FR and key == "blog") else {"title": "Blog", "url": "/blog", "description": HEROES_FR["blog"][1]}
            e["components"] = page_components(key, lang, refs)
            put("page", uid, e, loc)
            publish("page", uid, loc)
        print(f"  page {key}: {len(e['components'])} components")


if __name__ == "__main__":
    main()
