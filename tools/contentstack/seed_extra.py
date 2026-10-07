#!/usr/bin/env python3
"""Seed the extra content types (FAQ, buying guides, product spotlights, announcements, navigation),
hero banners + page entries for /, /faq and /guides. Idempotent.
Usage: python3 scripts/seed/seed_extra.py

Images: real product photos are pulled from the BigCommerce Storefront API and composed onto branded
backgrounds before upload to Contentstack.
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import seed  # noqa: E402
from content import AUTHORS  # noqa: E402
import photos  # noqa: E402
from content_extra import ANNOUNCEMENTS, FAQS, GUIDES, HOME, NAV, P, SPOTLIGHTS  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

api, ref, rte, slugify = seed.api, seed.ref, seed.rte, seed.slugify
upsert_entry, find_entry = seed.upsert_entry, seed.find_entry

HOME_BLOCK_PRODUCTS = [["exide_agm", "yuasa_efb"], ["exide_truck", "varta_truck"], ["lucas_d26", "fulbat_aux"]]

HEROES = {
    # key: (entry title, description, cta (label, href), theme index, shift)
    "home": ("Commerce B2B", HOME["description"], ("Browse buying guides", "/guides"), 0, 11),
    "faq": ("Frequently asked questions", "Quick answers for trade buyers on ordering, pricing and credit, delivery, accounts and fitment.",
            ("Browse buying guides", "/guides"), 2, 5),
    "guides": ("Buying guides", "Practical, step-by-step checklists for matching the right battery to the job, for workshops, fleets and leisure buyers.",
               ("Read the FAQ", "/faq"), 4, 8),
}


# ---------------------------------------------------------------- BigCommerce product photos
def bc_photos(ids):
    """Download the default image for each BigCommerce product id. Returns {id: local_path}."""
    env = seed.ENV
    url = f"https://store-{env['BIGCOMMERCE_STORE_HASH']}-{env['BIGCOMMERCE_CHANNEL_ID']}.mybigcommerce.com/graphql"
    query = "query($ids:[Int!]){site{products(entityIds:$ids,first:50){edges{node{entityId defaultImage{url(width:800)}}}}}}"
    req = urllib.request.Request(
        url, data=json.dumps({"query": query, "variables": {"ids": sorted(set(ids))}}).encode(),
        headers={"Authorization": f"Bearer {env['BIGCOMMERCE_STOREFRONT_TOKEN']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit("BigCommerce GraphQL error: " + str(data["errors"][0].get("message")))
    out = {}
    for e in data["data"]["site"]["products"]["edges"]:
        n = e["node"]
        if not n["defaultImage"]:
            continue
        path = os.path.join(seed.IMG_DIR, f"bc-{n['entityId']}.png")
        if not os.path.exists(path):
            with urllib.request.urlopen(n["defaultImage"]["url"]) as r, open(path, "wb") as f:
                f.write(r.read())
        out[n["entityId"]] = path
    return out


def compose(photo_paths, colors, size, shift, out):
    """Product photos on white rounded cards, centred on a branded gradient."""
    w, h = size
    img = seed.gradient(w, h, *colors, shift=shift)
    n = len(photo_paths)
    pad, gap = int(h * 0.09), int(h * 0.05)
    card_h = h - 2 * pad
    card_w = min(card_h, (w - 2 * pad - gap * (n - 1)) // n)
    x = (w - (n * card_w + (n - 1) * gap)) // 2
    mask = Image.new("L", (card_w, card_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=int(card_h * 0.05), fill=255)
    for p in photo_paths:
        card = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 255))
        photo = Image.open(p).convert("RGBA")
        photo.thumbnail((card_w - 40, card_h - 40))
        card.alpha_composite(photo, ((card_w - photo.width) // 2, (card_h - photo.height) // 2))
        img.paste(card.convert("RGB"), (x, pad), mask)
        x += card_w + gap
    img.save(out)


# Text-free pilesbatteries.com photography: (photo, crop size). The home hero is a tall portrait, others 4:3.
HERO_PHOTO = {
    "home": ("mea_voiture", (780, 1040)),
    "faq": ("alim", (1200, 900)),
    "guides": ("mea_pile", (1200, 900)),
}
HOME_SECOND_PHOTO = ("mea_moto", (780, 1040))
HOME_BLOCK_PHOTOS = ["mea_chargeur", "mea_outillage", "mea_solaire"]
GUIDE_PHOTOS = ["controle", "mea_voiture", "mea_solaire", "mea_pile", "mea_chargeur", "bat_moto"]  # same order as content_extra.GUIDES


def hero_photo(key):
    name, size = HERO_PHOTO[key]
    return photos.crop(name, size, 0, os.path.join(seed.IMG_DIR, f"hero-{key}-photo.jpg"))


def upload(path, title):
    return seed.upload_asset(path, title)


def main():
    os.makedirs(seed.IMG_DIR, exist_ok=True)
    assets, pub = [], []  # pub: (content_type, uid) in publish order

    # ---- product photos
    keys = {k for g in GUIDES for k in g["products"]} | {s[0] for s in SPOTLIGHTS} | {k for b in HOME_BLOCK_PRODUCTS for k in b}
    bc_images = bc_photos([P[k][0] for k in keys])
    photo = {k: bc_images[P[k][0]] for k in keys if P[k][0] in bc_images}
    print(f"== product photos: {len(photo)}/{len(keys)} downloaded")

    # ---- FAQs
    print("== faqs")
    faq_uid = {}
    for i, (topic, q, paras, featured) in enumerate(FAQS):
        uid, _ = upsert_entry("faq", q, {
            "title": q, "answer": rte([("p", t) for t in paras]), "topic": topic, "sort_order": i, "is_featured": featured,
        })
        faq_uid[q] = uid
        pub.append(("faq", uid))
    print(f"  {len(faq_uid)} faqs")

    # ---- buying guides (hero = up to 3 recommended product photos)
    print("== buying guides")
    for gi, g in enumerate(GUIDES):
        slug = slugify(g["title"])
        path = os.path.join(seed.IMG_DIR, f"guide-photo-{slug[:45]}.jpg")
        photos.crop(GUIDE_PHOTOS[gi], (1600, 600), 0, path)
        hero = upload(path, f"Guide - {g['title']}")
        assets.append(hero)
        author_uid = find_entry("author", AUTHORS[g["author"]]["name"])
        uid, _ = upsert_entry("buying_guide", g["title"], {
            "title": g["title"], "url": f"/guides/{slug}", "summary": g["summary"], "hero_image": hero,
            "audience": g["audience"], "read_minutes": g["minutes"],
            "steps": [{"step_title": t, "step_body": b, "pro_tip": tip or ""} for t, b, tip in g["steps"]],
            "checklist": g["checklist"],
            "recommended_bc_products": [P[k][0] for k in g["products"]], "recommended_skus": [P[k][1] for k in g["products"]],
            "related_faqs": [{"uid": faq_uid[q], "_content_type_uid": "faq"} for q in g["faqs"]],
            "author": ref("author", author_uid),
        })
        pub.append(("buying_guide", uid))
        print(f"  guide: {g['title'][:60]}")

    # ---- product spotlights (editorial image = the product photo on a branded card)
    print("== product spotlights")
    for si, (key, title, tagline, badge, features, uses, _pairs, featured) in enumerate(SPOTLIGHTS):
        pid, sku = P[key]
        path = os.path.join(seed.IMG_DIR, f"spotlight-photo-{key}.png")
        compose([photo[key]], AUTHORS[si % 6]["colors"], (1200, 900), si * 7 + 2, path)
        img = upload(path, f"Spotlight - {title}")
        assets.append(img)
        uid, _ = upsert_entry("product_spotlight", title, {
            "title": title, "bc_product_id": pid, "bc_sku": sku, "tagline": tagline,
            "editorial_summary": rte([
                ("p", f"{tagline}."),
                ("p", "Check the specification against the vehicle's original battery before ordering, and see our buying guide for a step-by-step fitment check."),
            ]),
            "key_features": features, "use_cases": [{"use_case": u, "description": d} for u, d in uses],
            "pairs_well_with_skus": [], "badge": badge, "editorial_image": img, "is_featured": featured,
        })
        pub.append(("product_spotlight", uid))
        print(f"  spotlight: {title[:60]}")

    # ---- announcement bars
    print("== announcement bars")
    for a in ANNOUNCEMENTS:
        uid, _ = upsert_entry("announcement_bar", a["title"], {
            "title": a["title"], "message": a["message"], "cta": {"title": a["cta"][0], "href": a["cta"][1]},
            "style": a["style"], "audience": a["audience"],
            "starts_at": "2026-10-01T00:00:00.000Z", "ends_at": "2026-12-31T23:59:00.000Z", "is_active": True,
        })
        pub.append(("announcement_bar", uid))
        print(f"  {a['title']}")

    # ---- navigation
    print("== navigation")
    uid, _ = upsert_entry("site_navigation", NAV["title"], {
        "title": NAV["title"],
        "header_links": [{"label": l, "href": h, "highlight": False} for l, h in NAV["header"]],
        "footer_columns": [{"heading": h, "links": [{"label": l, "href": u} for l, u in links]} for h, links in NAV["footer"]],
        "contact": {"sales_email": NAV["contact"][0], "support_phone": NAV["contact"][1], "opening_hours": NAV["contact"][2]},
        "legal_text": NAV["legal"],
    })
    pub.append(("site_navigation", uid))

    # ---- hero banners (one per page) -- published before the pages that reference them
    print("== hero banners")
    hero_uid = {}
    for key, (title, desc, cta, theme, shift) in HEROES.items():
        bg = upload(hero_photo(key), f"Hero photo - {title}")
        assets.append(bg)
        uid, _ = upsert_entry("hero_banner", title, {
            "title": title, "banner_image": bg, "banner_description": desc,
            "call_to_action": {"title": cta[0], "href": cta[1]}, "is_banner_image_full_width_": True,
        })
        hero_uid[key] = uid
        pub.append(("hero_banner", uid))
        print(f"  hero: {title}")

    # ---- pages: home (/), FAQ (/faq), buying guides (/guides)
    print("== pages")
    home_uid = find_entry("page", "Contentstack Kickstart") or find_entry("page", HOME["title"])
    blocks = []
    for i, (t, copy, layout, _theme) in enumerate(HOME["blocks"]):
        path = os.path.join(seed.IMG_DIR, f"home-block-photo-{i}.jpg")
        photos.crop(HOME_BLOCK_PHOTOS[i], (1200, 800), 0, path)
        img = upload(path, f"Home block - {t}")
        assets.append(img)
        blocks.append({"block": {"title": t, "copy": copy, "image": img, "layout": layout}})
    second = upload(photos.crop(HOME_SECOND_PHOTO[0], HOME_SECOND_PHOTO[1], 0, os.path.join(seed.IMG_DIR, "home-second-photo.jpg")), "Home hero second photo")
    assets.append(second)
    home = {"title": HOME["title"], "url": "/", "description": HOME["description"],
            "hero": ref("hero_banner", hero_uid["home"]), "image": second, "rich_text": HOME["rich_text"], "blocks": blocks}
    if home_uid:
        api("PUT", f"/content_types/page/entries/{home_uid}", body={"entry": home}, params={"locale": seed.LOCALE})
    else:
        home_uid, _ = upsert_entry("page", HOME["title"], home)
    pub.append(("page", home_uid))
    for key, title, url, desc in (
        ("faq", "FAQ", "/faq", HEROES["faq"][1]),
        ("guides", "Buying Guides", "/guides", HEROES["guides"][1]),
    ):
        uid, _ = upsert_entry("page", title, {"title": title, "url": url, "description": desc, "hero": ref("hero_banner", hero_uid[key])})
        pub.append(("page", uid))
        print(f"  page: {url}")

    # ---- publish (assets first, then entries in dependency order)
    print(f"== publishing to '{seed.STACK_ENV}'")
    for a in assets:
        seed.publish_asset(a)
    for ct, uid in pub:
        seed.publish_entry(ct, uid)
    print(f"  published {len(assets)} assets and {len(pub)} entries")


if __name__ == "__main__":
    main()
