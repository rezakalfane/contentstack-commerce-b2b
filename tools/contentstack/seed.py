#!/usr/bin/env python3
"""Seed Contentstack with authors, blog posts, a hero banner and a blog listing page.

Idempotent: entries and assets are looked up by title/filename and reused.
Credentials come from ../../.env.local (never printed). Usage:  python3 scripts/seed/seed.py
"""
import datetime as dt
import json
import mimetypes
import os
import re
import sys
import textwrap
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from content import AUTHORS, POSTS  # noqa: E402
import photos  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IMG_DIR = os.environ.get("SEED_IMG_DIR", os.path.join(ROOT, ".seed-images"))
LOCALE = "en-us"

HOSTS = {
    "us": "api.contentstack.io",
    "eu": "eu-api.contentstack.com",
    "au": "au-api.contentstack.com",
    "azure-na": "azure-na-api.contentstack.com",
    "azure-eu": "azure-eu-api.contentstack.com",
    "gcp-na": "gcp-na-api.contentstack.com",
}


def load_env():
    env = {}
    with open(os.path.join(ROOT, ".env.local")) as f:
        for line in f:
            m = re.match(r"^([A-Z0-9_]+)=(.*)$", line.strip())
            if m:
                env[m.group(1)] = m.group(2)
    return env


ENV = load_env()
BASE = f"https://{HOSTS[ENV.get('CONTENTSTACK_REGION', 'us')]}/v3"
STACK_ENV = ENV["CONTENTSTACK_ENVIRONMENT"]
HEADERS = {"api_key": ENV["CONTENTSTACK_API_KEY"], "authorization": ENV["CONTENTSTACK_MANAGEMENT_TOKEN"]}


def secrets_redacted(text):
    for v in HEADERS.values():
        text = text.replace(v, "***")
    return text


def api(method, path, body=None, params=None, multipart=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = dict(HEADERS)
    data = None
    if multipart:
        boundary = uuid.uuid4().hex
        parts = []
        for name, value in multipart["fields"].items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
        fpath = multipart["file"]
        ctype = mimetypes.guess_type(fpath)[0] or "application/octet-stream"
        with open(fpath, "rb") as f:
            content = f.read()
        parts.append(
            (f'--{boundary}\r\nContent-Disposition: form-data; name="asset[upload]"; '
             f'filename="{os.path.basename(fpath)}"\r\nContent-Type: {ctype}\r\n\r\n').encode()
            + content + b"\r\n"
        )
        parts.append(f"--{boundary}--\r\n".encode())
        data = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    for attempt in range(6):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
                time.sleep(0.12)
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            if e.code == 429 and attempt < 5:
                time.sleep(2 + attempt * 2)
                continue
            sys.exit(secrets_redacted(f"{method} {path} -> HTTP {e.code}: {raw[:800]}"))
    sys.exit("retries exhausted")


# ---------------------------------------------------------------- images
def font(size, bold=True):
    for p in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"):
        try:
            return ImageFont.truetype(p, size, index=1 if bold and p.endswith(".ttc") else 0)
        except OSError:
            continue
    return ImageFont.load_default(size)


def gradient(w, h, c1, c2, shift=0):
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = min(1, max(0, (x / w * 0.6 + y / h * 0.4)))
            px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
    d = ImageDraw.Draw(img, "RGBA")
    for k in range(4):  # soft decorative circles, shifted per image for variety
        r = (140 + 60 * k + shift * 9) % 420 + 80
        cx = (w * (0.15 + 0.22 * k) + shift * 53) % w
        cy = (h * (0.2 + 0.2 * k) + shift * 31) % h
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 14))
    return img


def wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def make_avatar(author, path):
    img = gradient(400, 400, *author["colors"])
    d = ImageDraw.Draw(img)
    initials = "".join(p[0] for p in author["name"].split()[:2])
    f = font(150)
    w = d.textlength(initials, font=f)
    d.text(((400 - w) / 2, 110), initials, font=f, fill="white")
    img.save(path)


def make_cover(text, theme, colors, shift, path, size=(1600, 900)):
    w, h = size
    img = gradient(w, h, *colors, shift=shift)
    if not text:  # background-only image (the page overlays real text)
        img.save(path)
        return
    d = ImageDraw.Draw(img)
    d.text((90, 90), theme.upper(), font=font(34), fill=(255, 255, 255, 200))
    tf = font(84)
    y = 260
    for line in wrap(d, text, tf, w - 180):
        d.text((90, y), line, font=tf, fill="white")
        y += 104
    img.save(path)


# ---------------------------------------------------------------- helpers
def find_asset(filename):
    r = api("GET", "/assets", params={"query": json.dumps({"filename": filename})})
    return r["assets"][0]["uid"] if r.get("assets") else None


def upload_asset(path, title):
    """Uploads a file as an asset. If an asset with that filename exists, its file is replaced in place
    (same UID, so every entry referencing it keeps working) -- an updated image under the same name must not be ignored."""
    fn = os.path.basename(path)
    uid = find_asset(fn)
    if uid:
        api("PUT", f"/assets/{uid}", multipart={"fields": {"asset[title]": title}, "file": path})
        return uid
    r = api("POST", "/assets", multipart={"fields": {"asset[title]": title}, "file": path})
    return r["asset"]["uid"]


def find_entry(ct, title):
    r = api("GET", f"/content_types/{ct}/entries", params={"query": json.dumps({"title": title}), "locale": LOCALE})
    return r["entries"][0]["uid"] if r.get("entries") else None


def upsert_entry(ct, title, entry):
    uid = find_entry(ct, title)
    if uid:
        api("PUT", f"/content_types/{ct}/entries/{uid}", body={"entry": entry}, params={"locale": LOCALE})
        return uid, False
    r = api("POST", f"/content_types/{ct}/entries", body={"entry": entry}, params={"locale": LOCALE})
    return r["entry"]["uid"], True


def publish_entry(ct, uid):
    api("POST", f"/content_types/{ct}/entries/{uid}/publish",
        body={"entry": {"environments": [STACK_ENV], "locales": [LOCALE]}})


def publish_asset(uid):
    api("POST", f"/assets/{uid}/publish", body={"asset": {"environments": [STACK_ENV], "locales": [LOCALE]}})


def ref(ct, uid):
    return [{"uid": uid, "_content_type_uid": ct}]


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def rte(children_spec):
    def uid():
        return uuid.uuid4().hex

    def node(t, children):
        return {"type": t, "uid": uid(), "attrs": {}, "children": children}

    def text(t):
        return {"text": t}

    kids = []
    for kind, val in children_spec:
        if kind in ("p", "h2"):
            kids.append(node(kind, [text(val)]))
        elif kind == "ul":
            kids.append(node("ul", [node("li", [node("p", [text(item)])]) for item in val]))
    return {"type": "doc", "uid": uid(), "_version": 1, "attrs": {}, "children": kids}


# ---------------------------------------------------------------- main
def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    published = {"assets": [], "authors": [], "posts": []}

    # 1. authors (avatar assets first)
    print("== authors")
    author_uid = []
    for a in AUTHORS:
        slug = slugify(a["name"])
        p = os.path.join(IMG_DIR, f"author-{slug}.png")
        make_avatar(a, p)
        asset = upload_asset(p, f"Avatar - {a['name']}")
        published["assets"].append(asset)
        uid, created = upsert_entry("author", a["name"], {"title": a["name"], "picture": asset, "bio": a["bio"]})
        author_uid.append(uid)
        published["authors"].append(uid)
        print(f"  {'created' if created else 'updated'} {a['name']} ({uid})")

    # 2. blog posts
    print("== blog posts")
    flat = []  # (author_index, post_index_within_author, data)
    for ai, posts in enumerate(POSTS):
        for pi, post in enumerate(posts):
            flat.append((ai, pi, post))
    post_uid = []
    start = dt.datetime(2026, 1, 12, 9, 0, tzinfo=dt.timezone.utc)
    for idx, (ai, pi, (title, intro, s1, s2, takeaways)) in enumerate(flat):
        a = AUTHORS[ai]
        slug = slugify(title)
        p = os.path.join(IMG_DIR, f"post-photo-{slug[:60]}.jpg")
        photos.crop(photos.PHOTOS[(ai * 2 + pi) % len(photos.PHOTOS)], (1600, 900), idx, p)
        asset = upload_asset(p, title)
        published["assets"].append(asset)
        when = start + dt.timedelta(days=7 * (pi * 6 + ai))  # interleave authors over time
        body = rte([
            ("p", intro),
            ("h2", s1[0]), ("p", s1[1]),
            ("h2", s2[0]), ("p", s2[1]),
            ("h2", "Key takeaways"), ("ul", takeaways),
        ])
        entry = {
            "title": title,
            "url": f"/blog/{slug}",
            "author": ref("author", author_uid[ai]),
            "date": when.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "featured_image": asset,
            "body": body,
            "is_archived": False,
            "seo": {"meta_title": title, "meta_description": textwrap.shorten(intro, 180, placeholder="…"), "keywords": "b2b commerce, " + a["theme"].lower(), "enable_search_indexing": True},
        }
        uid, created = upsert_entry("blog_landing_page", title, entry)
        post_uid.append(uid)
        print(f"  [{idx + 1:02d}/36] {'created' if created else 'updated'} {title[:60]}")

    # 3. related posts (always points at an earlier post so publish order works)
    print("== related posts")
    for idx, (ai, pi, post) in enumerate(flat):
        rel = idx - 7 if idx >= 7 else (idx - 1 if idx >= 1 else None)
        if rel is None:
            continue
        api("PUT", f"/content_types/blog_landing_page/entries/{post_uid[idx]}",
            body={"entry": {"title": post[0], "related_post": ref("blog_landing_page", post_uid[rel])}},
            params={"locale": LOCALE})
    print("  done")

    # 4. hero banner + listing page
    print("== listing page")
    hero_path = os.path.join(IMG_DIR, "blog-hero-photo.jpg")
    photos.crop("bat_moto", (1200, 900), 0, hero_path)
    hero_asset = upload_asset(hero_path, "Blog hero photo")
    published["assets"].append(hero_asset)
    hero_uid, _ = upsert_entry("hero_banner", "The B2B Commerce Blog", {
        "title": "The B2B Commerce Blog",
        "banner_image": hero_asset,
        "banner_description": "Practical guidance on pricing, ordering, integrations, payments, sales and headless storefronts for B2B commerce teams.",
        "call_to_action": {"title": "Browse articles", "href": "/blog"},
        "is_banner_image_full_width_": True,
    })
    latest = sorted(range(36), key=lambda i: -((flat[i][1] * 6 + flat[i][0])))
    featured = [post_uid[i] for i in latest[:3]]
    related = [post_uid[i] for i in latest[3:6]]
    listing = {
        "title": "Blog",
        "url": "/blog",
        "search": {"placeholder_text": "Search articles", "search_button": {"title": "Search", "href": "/blog"}},
        "page_components": [
            {"hero_banner": {"hero_banner": ref("hero_banner", hero_uid)}},
            {"from_blog": {"title_h2": "Latest articles", "featured_blogs": [{"uid": u, "_content_type_uid": "blog_landing_page"} for u in featured],
                           "view_articles": {"title": "View all articles", "href": "/blog"}}},
            {"widget": {"title_h2": "Keep reading", "type": "Related Posts","related_blogs": [{"uid": u, "_content_type_uid": "blog_landing_page"} for u in related]}},
        ],
        "seo": {"meta_title": "The B2B Commerce Blog", "meta_description": "Articles on B2B pricing, ordering, integrations, payments, sales and composable storefronts.", "keywords": "b2b commerce, blog", "enable_search_indexing": True},
    }
    listing_uid, created = upsert_entry("blog_listing_page", "Blog", listing)
    print(f"  {'created' if created else 'updated'} listing page ({listing_uid})")

    # 5. publish: assets, authors, hero, posts (ascending, so references go first), listing
    print(f"== publishing to '{STACK_ENV}'")
    for uid in published["assets"]:
        publish_asset(uid)
    for uid in published["authors"]:
        publish_entry("author", uid)
    publish_entry("hero_banner", hero_uid)
    for uid in post_uid:
        publish_entry("blog_landing_page", uid)
    publish_entry("blog_listing_page", listing_uid)
    print(f"  published {len(published['assets'])} assets, {len(published['authors'])} authors, 1 hero, {len(post_uid)} posts, 1 listing page")


if __name__ == "__main__":
    main()
