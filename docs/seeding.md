# Seeding sample content

The Python scripts in `tools/contentstack/` create and refresh all sample content in Contentstack through the **Management API**
(CMA). They are **idempotent**: entries are looked up by `title` and updated rather than duplicated, so they are safe to
re-run.

## Prerequisites

- Python 3.12+ with Pillow (`pip install pillow`).
- `storefront/.env.local` containing `CONTENTSTACK_API_KEY`, `CONTENTSTACK_MANAGEMENT_TOKEN`, `CONTENTSTACK_ENVIRONMENT`,
  `CONTENTSTACK_REGION`, plus `BIGCOMMERCE_STORE_HASH`, `BIGCOMMERCE_CHANNEL_ID`, `BIGCOMMERCE_STOREFRONT_TOKEN`
  (`seed_extra.py` downloads product photos from BigCommerce).
- The management token needs create, update and **publish** rights on the `preview` environment.

Credentials are read from `.env.local` and are never printed (error output is redacted).

## Run order

```bash
python3 tools/contentstack/schemas.py      # 1. content types (faq, buying_guide, product_spotlight, announcement_bar, site_navigation)
python3 tools/contentstack/seed.py         # 2. 6 authors, 36 posts, hero + blog listing
python3 tools/contentstack/seed_extra.py   # 3. FAQs, guides, spotlights, announcements, navigation, hero banners, pages
python3 tools/contentstack/seed_fr.py      # 4. French (fr-fr) versions of everything
python3 tools/contentstack/blocks.py       # 5. the block model, added on top (additive), both locales
```

Steps 1 to 4 still create the earlier fixed-layout content (the `hero_banner`, `blog_listing_page` and `page` fields the block model replaced);
`blocks.py` then adds `page.components` and `blog_landing_page.content` + `read_time` and fills them (the pages `home`, `faq`, `guides` and a new `blog`
page, each with its blocks, and for every post a text block copied from its `body`), in English and French, publishing what it changes. It is idempotent
and leaves the earlier fields filled, so the old site kept working until the prune (run on 7 October 2026).

`seed_fr.py` accepts `--only author,hero_banner,blog_landing_page,blog_listing_page,faq,buying_guide,product_spotlight,announcement_bar,site_navigation,page`
to localize a subset.

> **Order matters.** French entries are **copies** of the English ones at the moment they are localized. After changing
> anything non-translatable in English (an image, a reference), run `seed_fr.py` again.

## Workflow and publishing

New entries start in the **Draft** stage, and production only accepts **Approved** ones ([workflow.md](workflow.md)):

```bash
python3 tools/contentstack/workflow.py [--baseline]                 # create the workflow and publishing rule (idempotent)
python3 tools/contentstack/publish_environment.py preview           # publish everything to the staging environment
python3 tools/contentstack/publish_environment.py production --approve # approve, then publish everything to production
```

## Files

| File | Role |
|---|---|
| `schemas.py` | field builders (`text`, `select`, `rte`, `group`, `reference`…) and the five content type definitions; creates or updates them |
| `seed.py` | API helper, asset upload, entry upsert, publish; seeds authors, posts, related posts, blog hero and listing |
| `seed_extra.py` | FAQs, buying guides, product spotlights, announcement bars, navigation, hero banners, `page` entries (home, FAQ, guides) |
| `seed_fr.py` | localizes and publishes the French versions |
| `blocks.py` | adds the block model (`page.components`, `blog_landing_page.content` and `read_time`) and fills it, both locales; additive and idempotent |
| `backup.py` | saves every content type and the entries of both locales to `.backups/contentstack-<timestamp>.json` (gitignored, never commit it) |
| `prune.py` | removes what the block model replaced; a dry run unless `--run` (see below) |
| `content.py` | English authors and the 36 posts (title, intro, two sections, takeaways) |
| `content_extra.py` | FAQs, product keys (`P`), guides, spotlights, announcements, home page, navigation |
| `content_fr.py`, `content_fr_posts.py` | French translations, in the same order and shape as the English data |
| `photos.py`, `photos/*.jpg` | the nine text-free photos and a cropper that produces varied crops |

## How the pieces work

### API helper (`seed.py`)
`api(method, path, body, params, multipart)` signs requests with the management token, retries on HTTP 429, and exits with
a redacted message on failure. The base host comes from `CONTENTSTACK_REGION`.

### Assets
`upload_asset(path, title)` looks for an asset with the same **filename**; if found, it **replaces the file in place**
(`PUT /assets/<uid>`), keeping the UID so every reference stays valid; otherwise it creates one. (An earlier version
reused the old file, which silently ignored updated crops.) Generated images are written to `.seed-images/` (gitignored).

### Images
- **Photos** (`photos.py`): `crop(name, size, variant, out)` crops a source photo to a size with a zoom and pan chosen by
  `variant`, so 36 posts can use nine photos without looking identical.
- **Posts**: `photos.PHOTOS[(author*2 + post) % 9]` with `variant = post index`.
- **Heroes**: home = tall portrait of a car (780×1040) and the page's second image = motorcycle; FAQ = plug;
  guides = batteries; blog = motorcycle on a road.
- **Guides**: one photo each (controle, car, solar, batteries, charger, motorcycle), 1600×600.
- **Spotlights**: the product photo (downloaded from BigCommerce) composed onto a branded card, used as a fallback image.
- **Authors**: gradient avatars with initials.
- **Blocks on the home page**: three photos (charger, tool, solar).

### Entries
`upsert_entry(content_type, title, entry)` finds by `title` and `PUT`s, or `POST`s. References use
`{"uid": …, "_content_type_uid": …}`; assets are bare UIDs; JSON RTE bodies are built by `rte([("p", "…"), ("h2", "…"), ("ul", […])])`.

### Related posts
Each post links to an **earlier** post (`idx - 7`, or `idx - 1` for the first few) so referenced entries are always
published first. Posts are published in ascending order.

### Dates
Posts are spread one per week from 12 January 2026, interleaving authors.

### Localizing (`seed_fr.py`)
For each English entry: `GET` the master → drop system fields → convert asset objects to UIDs → apply the French
overrides → `PUT …?locale=fr-fr` → publish with `locale: "fr-fr"`. French titles are new (they are unique per locale),
so entries are found by their **English** title.

## Common tasks

### Add a blog post
1. Append a tuple to the right author's list in `content.POSTS` (title, intro, (heading, paragraph) ×2, takeaways).
2. Append its French translation at the same position in `content_fr_posts.POSTS_FR`.
3. Update the count assertions if you keep them (`assert len(...) == 6`), then run `seed.py`, `seed_fr.py --only blog_landing_page` and `blocks.py` (which gives the post its `content` block and `read_time`).

### Add a buying guide
1. Add recommended products to `P` in `content_extra.py` (`"key": (bigcommerce_product_id, "SKU")`). Look IDs up with
   `searchCatalog`, or in BigCommerce.
2. Append a guide dict to `GUIDES` (title, audience, minutes, summary, steps, checklist, products, faqs, author).
3. Append the French dict to `content_fr.GUIDES_FR` with the **same number of steps and checklist items**.
4. Add its photo to `GUIDE_PHOTOS` in `seed_extra.py`.
5. Run `seed_extra.py`, then `seed_fr.py --only buying_guide`.

### Add or change an FAQ
Edit `FAQS` / `FAQS_FR` (same order), run `seed_extra.py` then `seed_fr.py --only faq`. `topic` must be one of the five allowed values.

### Change the home page
To change the seeded content, edit `HOME`, `HEROES`, `HOME_BLOCK_PHOTOS` in `seed_extra.py` / `content_extra.py` and the French in `content_fr.py`
(`HOME_FR`, `HEROES_FR`). Run `seed_extra.py`, `seed_fr.py --only page,hero_banner` and `blocks.py` (the home blocks are built in `page_components()` in `blocks.py`, from the same data).

### Backup and prune

The block model was added **next to** the earlier fixed-layout model, and the site now reads only the new one. The earlier model was in the stack until the prune:
`page.image`, `rich_text`, `blocks`, `hero`; `blog_landing_page.body`, `related_post`, `is_archived`, `comments`, `social_share`; and the `blog_listing_page`
and `hero_banner` types with their entries. The order for removing it (followed on 7 October 2026):

1. `python3 tools/contentstack/backup.py`: saves content types and entries (both locales) to `.backups/`.
2. Deploy the storefront that reads `components` / `content`, and check production and staging.
3. `python3 tools/contentstack/prune.py`: a **dry run** that lists, for each content type, the fields it would remove and, for the two superseded types,
   how many entries it would delete.
4. `python3 tools/contentstack/prune.py --run`: removes those fields, then deletes the two types (`force`, which deletes their entries). The stack goes
   from ten content types to eight.

**Status: the prune was run on 7 October 2026, after the new code was deployed.** Note that `seed.py`, `seed_extra.py` and `seed_fr.py`
still write the earlier model, so run them only before the prune (or adapt them first); re-run `blocks.py` after them.

### Start over
There is no destructive reset (apart from the prune above). To remove content, delete entries in the Contentstack app (or via CMA) and re-run the
seeds. Deleting assets that are still referenced is rejected by Contentstack; list references with
`GET /assets/<uid>/references` first.

## Pitfalls (each of these happened)

| Symptom | Cause |
|---|---|
| `api_key is not valid` | wrong region host |
| `… is a reserved value` for a field UID | UIDs like `*_product_ids` are reserved |
| `Max content_types limit reached` | free plan caps at 10 content types |
| `X is not a valid enum value` | select fields only accept their defined choices |
| `picture: is not a valid upload` when localizing | PUT needs asset **UIDs**, GET returns asset objects (`normalize()` in `seed_fr.py`) |
| `Localised entries can not be published from master locale` | publish body needs top-level `"locale": "fr-fr"` |
| Updated image not showing | the asset was reused by filename (fixed: replaced in place); French copies need `seed_fr.py` again |
| A guide page shows fewer products than expected | a product key in `P` points at an ID that is not on the channel |
