# History

A chronological record of every request made while building this storefront, and what came out of it.
Prompts are quoted or condensed from the conversation; "Screenshot" means the request came with an image of the
browser. Dates are 2026.

> Conventions: **Result** is a summary of what was actually delivered. Things that were investigated and
> rejected, or that turned out different from the first attempt, are called out because they explain later decisions.

---

## 5 October

### 1. How to build a storefront on Contentstack
**Prompt:** "I have a ContentStack stack with an API key as well as a Management key. How can I build a storefront and get content from ContentStack?"

**Result:** Explained the credential model: the stack **API key** identifies the stack, a **delivery token** (read-only,
bound to one environment) is what a storefront uses, and the **management token** is only for writing content (seeding,
automation) and must never reach the browser. Recommended Next.js with `@contentstack/delivery-sdk`, and noted that a
commerce backend is needed for catalog, cart and checkout.

### 2. Credentials arrive (labels only)
**Prompt:** Pasted the labels "Stack API Key / Delivery Token / Preview Token" (no values).

**Result:** Scaffolded `storefront/` with `create-next-app` (TypeScript, App Router, Tailwind) and installed the
Contentstack SDKs. Values were deliberately kept out of the chat.

### 3. "Can you name the environment variable I should create?"
**Result:** Created `.env.local` with `CONTENTSTACK_API_KEY`, `CONTENTSTACK_DELIVERY_TOKEN`, `CONTENTSTACK_PREVIEW_TOKEN`,
`CONTENTSTACK_ENVIRONMENT`, `CONTENTSTACK_REGION` and the client in `lib/contentstack.ts`. No `NEXT_PUBLIC_` prefix, so
tokens stay server-side.

### 4. "filled"
**Result:** Verified the credentials against the Delivery API and listed the content types the stack already had
(`page`, `hero_banner`, `author`, `blog_landing_page`, `blog_listing_page`: Contentstack's starter model).

### 5. "You can use my first BigCommerce store with the products of a channel named after the second"
**Result:** Loaded the BigCommerce admin skill, listed configured environments (names only) and found that the
first store has **no** channel with that name; the name belongs to a separate store. Asked which was meant.

### 6. Choosing the source
**Answer:** the second store (the one with the headless storefront channel).
**Result:** Listed its channels (a Stencil channel, one active headless storefront channel, several terminated/deleted ones) and its
catalog summary (150 products, car batteries first).

### 7. Channel and token
**Prompt:** "Channel is <the headless one>. ok with the process. Can we also populate ContentStack with authors, blog listing page and blog landing pages?"

**Result:** Created a **channel-scoped Storefront API token** (localhost origin, 90 days) and wrote it to `.env.local`
without printing it. Contentstack seeding was blocked on a management token, so a placeholder variable was added.

### 8. Authors, 36 posts and the blog listing
**Prompt:** "updated management token, please create a handful of authors, blog posts about generic b2b commerce topics with the blog listing page and publish. let's make 6 authors with 6 blog posts each, so 36 blog posts"

**Result:** Wrote the idempotent seed (`scripts/seed/seed.py`): 6 fictional authors, 36 articles across six themes
(pricing, buyer experience, integrations, payments, sales, headless), a hero banner and the listing page, all published.
**Findings along the way:** the stack is in the **EU region** with a single environment named **`preview`** (my first
calls used the US host and failed); `featured_image` and `picture` are required file fields so images had to be
generated; the `widget.type` field is an enum (`Blog Archive` / `Related Posts`); publishing a *localized* entry needs a
top-level `locale` in the request body.

### 9. Screenshot: Live Preview shows a 404
**Prompt:** (Screenshot of a blog entry in Contentstack with Live Preview showing "404".)

**Result:** The storefront only had the scaffold home page. Built `/blog` and `/blog/[slug]`, the data layer
(`lib/blog.ts`), JSON-RTE-to-HTML rendering and Live Preview (`livePreviewQuery`, preview host per region).

### 10. Screenshot: the blog listing entry also 404s
**Result:** Same cause, fixed by the same routes.

### 11. "Can you creatively create new useful schemas and use them to create entries for our site?"
**Result:** Designed content types for a B2B site: **FAQ**, **Buying guide**, **Product spotlight**, **Announcement
bar**, **Site navigation** (and a Case study type, later removed). Wrote the schema builder (`schemas.py`), the entry
data (`content_extra.py`) and seeds. Hit the **free-plan limit of 10 content types**, which shaped decision 15.

### 12. Screenshot: hero heading overlaps itself
**Result:** The generated hero image had the title baked in, so the headline was drawn twice. Replaced it with a
text-free background and renamed the hero entry to its real headline.

### 13. "Rename the placeholder site name to Commerce B2B"
**Result:** Renamed in the layout and home page.

### 14. Screenshot: the starter "Contentstack Kickstart" page entry
**Result:** The home page was hard-coded. Rewrote the starter `page` entry (URL `/`) into real home content and made
the home route render from it.

### 15. "Navigation is important so maybe we can remove Case Study, or choose what's more important: Case Study or FAQ?"
**Result:** Chose to keep **FAQ** (answers real buyer questions, referenced by guides) and delete the **empty**
`case_study` type to free a slot for `site_navigation`. Navigation, announcement bar and footer are now CMS-driven.

### 16. Screenshot: "not seeing product images, and contentstack images, buying guides page also needs its own hero banner, FAQ as well"
**Result:** Product cards now use live BigCommerce photos and prices via the Storefront GraphQL API (channel-specific
host). Replaced gradient placeholders with composed product photos. Added a `hero` reference to the `page` type and
created `/faq` and `/guides` page entries, each with its own hero banner entry.

### 17. "product prices are no more hidden for guests"
**Result:** Confirmed guests receive prices from the Storefront API and show them on all product cards.

### 18-19. Screenshots: "make FAQ same page width as the other pages" / "guide page width should be the same as home page. All pages should have the same width"
**Result:** Standardised every page on one container width. Detail pages (guide, post) use a main column plus a sidebar
instead of stretching text. (Later superseded by the 1100px `.page` container, see 24.)

### 20. "You can use images (without titles) from pilesbatteries.com. We also need a nice product detail page"
**Result:** Reviewed the site's imagery, kept the nine text-free photos (cars, motorcycles, chargers, tools,
batteries, solar, a plug) and excluded banners with baked-in text. Built the **product detail page** (gallery, price,
stock, key specs, volume pricing, description, spec table, related guides and products, JSON-LD), the **product
list**, the **cart** and **add-to-cart** (server action + BigCommerce cart mutations). Verified cart create/add/read/remove
against the real store once.

### 21. "I need the whole site to be multi-language. I've defined an additional fr-FR locale (will need a base URL for that), and we need to translate our ContentStack entries in French"
**Result:** Implemented locale routing (`proxy.ts`, `app/[locale]/…`): English at clean URLs, French under `/fr`.
Locale-aware fetchers with fallback to English, a UI dictionary, hreflang metadata, a language switcher and
locale-aware prices and dates. The "base URL" is the **per-locale Live Preview base URL** in Contentstack settings
(`http://localhost:3000` for en-us, `http://localhost:3000/fr` for fr-fr).

### 22. Screenshot: Visual Editor "Can't resolve './globals.css'"
**Result:** A transient error from moving the layout into `app/[locale]/` mid-edit; resolved by the new layout.

### 23. "We'll need to translate ContentStack entries"
**Result:** Wrote French translations of all content (36 posts, 6 bios, 15 FAQs, guides, spotlights, navigation,
banners, pages) and `seed_fr.py`, which localizes and publishes each entry as `fr-fr`. 77 entries published at that point.

### 24. "Using your best design skill, update the storefront style with a nice light theme, 1100px max page width, better pictures on the homepage"
**Result:** Redesigned as **Workbench**: light, cool steel and blue-black ink with one battery-terminal amber accent,
Archivo (condensed display) + IBM Plex Sans, photography-led home page (staggered photo pair, category mosaic), open
product tiles instead of bordered cards, dark footer. Documented in `docs/design-system.md`.

## 6 October

### 25. Screenshot: "buying guides deserves better pictures from pilesbatteries as well, I don't like the banners with product images"
**Result:** Guide hero images are now site photography instead of composed product shots. Fixed the seeder so a changed
image under an existing filename **replaces the asset in place** (it had been silently reusing the old file).

### 26. "Create a HISTORY.md … update the main README.md … create docs/*.md files"
**Result:** This file, the README and the `docs/` folder.

### 27. Screenshot: duplicate React key error in Visual Editor
**Result:** The preview API can return an entry twice. De-duplicated by `uid` in the data layer.

### 28. Screenshot: "can you put a nice editable image in the second box as well?"
**Result:** The second hero photo (the `image` field of the home page) now has an edit tag, so it can be changed
inline in Visual Editor; the seed gives it a real photo instead of the old placeholder.

### 29. "Should be easy to create product listing page as well and a mega menu for products, all coming from BigCommerce and localized."
**Result:** Product listing (`/products`, `/products/<category>`) with sort, brand and price filters from BigCommerce
facets, and a **mega menu** built from the live category tree, with photos, subcategories, counts and French labels.

### 30. "When no product for a category, list sub-categories products"
**Result:** A category's own product list is often empty. Categories now use faceted search by category ID, which
includes all subcategory products (Automotive Batteries lists 38).

### 31. "List 8 facet values max. Select 3 additional facets with good products representation"
**Result:** Measured attribute coverage across the 150 products and added **Technology (93%)**, **Voltage (89%)** and
**Warranty (66%)** facets. Every facet, brand included, shows at most 8 values (selected values always stay visible).

### 32. Screenshot: Live Preview SDK error "Failed to send page context to Visual Builder" (Timeline mode)
**Result:** Replaced `setPageContext` (which posts a message and expects an acknowledgement) with the documented
`<meta name="contentstack:entry-uid">` tags, which need no builder frame.

### 33. "Can you add 3 more nice & localized buying guides?"
**Result:** Added guides for deep-cycle batteries (gel / AGM / dual-purpose), chargers and jump starters, and
motorcycle batteries, in English and French, each recommending real catalog products.

### 34. "Can we automatically apply filters on click and move the Clear filter action at the top"
**Result:** Filters apply as you click (no Apply button), without a page reload or scroll jump. "Clear all" sits in
the toolbar at the top.

### 35. "Also add search as you type (3 char min) and when entering a search, it's added as a filter you can remove (gets cleared on clear filters action)"
**Result:** Search-as-you-type from 3 characters (hint below that), shown as a removable chip, cleared by "Clear all".

### 36. "Add a nice dynamic quantity chooser in the cart"
**Result:** Stepper (− / typeable / +) with instant totals, debounced save to BigCommerce, rollback on error. Verified in
a real browser, including persistence after reload.

### 37. "Enable live editing with sync when we edit the form" and "Read the Visual Editor setup docs … to enable inline editing"
**Result:** Read the Contentstack docs and the SDK reference. Enabled `mode: "builder"`, SSR live sync, `data-cslp` edit
tags on the key fields of every page type (headlines, images, rich text, steps, cards), entry context via meta tags and
a CSP `frame-ancestors` rule. See `docs/live-preview-and-visual-editor.md`.

### 38. Review pass (no prompt): contrast and mobile
**Result:** Measured the palette's contrast ratios and corrected the docs; changed the guide step numbers from deep amber
(2.3:1 on white) to ink; reviewed phone-width screenshots and made the filter panel start collapsed below 1024 px.

---

## Things that did not work the first time (and why it matters)

| Problem | Cause | Fix |
|---|---|---|
| `api_key is not valid` | Called the US host; the stack is in the EU region | Region-aware hosts |
| Publishing a localized entry failed | CMA needs a top-level `locale` in the publish body | Added to `seed_fr.py` |
| Field UID rejected | `recommended_product_ids` is reserved | Renamed `recommended_bc_products` |
| Cannot create 11th content type | Free plan caps stacks at 10 types | Removed unused Case Study |
| GraphQL "JWT channel id doesn't match" | Channel-scoped token needs the channel host | `store-<hash>-<channel>.mybigcommerce.com` |
| Product page 404 | Catch-all route dropped the `products/` prefix of the BigCommerce path | Rebuild `/products/<slug>/` |
| Product page 500 | Passed a function from a Server to a Client Component | Pass a string template |
| Changed image not updating | Seeder reused assets by filename | Replace the asset in place |
| Category page empty | Category's own product list excludes subcategories | Faceted search by category |
| Unused GraphQL variable error | Declared `$before` and `$after` together | Declare only the one in use |
