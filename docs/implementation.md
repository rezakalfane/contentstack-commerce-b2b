# Implementation details

How each feature works and where to find it. Paths are relative to `storefront/`.

## 1. Data layer

### Contentstack: `lib/content.ts` and `providers/cms/contentstack/`

`lib/content.ts` is the facade the pages call (`getPage`, `getNavigation`, `getAnnouncement`, `getPosts`, `getPost`, `getGuides`, `getGuide`,
`getSpotlights`, all locale-first); it reads through the Contentstack provider and returns the content model of `core/content.ts` (`Page`, `Block`,
`Post`, `Guide`...), so components never see an entry. The provider has four parts:

- **`client.ts`**: `getStack(preview?)` returns a shared delivery stack, or, for a Live Preview request, a *fresh* stack configured with the preview
  token and the region's preview host, with `livePreviewQuery(...)` applied (required because it mutates the stack). `previewParams()` reads the
  draft hash and the entry being edited from the trusted `x-cs-*` headers that `proxy.ts` sets. `entries(contentType, locale, preview, opts)` is the
  single entry point for reading: it selects the Contentstack locale (`en-us` / `fr-fr`), enables `includeFallback()` (an untranslated entry falls back
  to English), resolves the references asked for, removes duplicate entries (the preview API can return one twice), and in preview adds the edit tags
  (`addEditableTags`) and calls `includeReferenceContentTypeUID()` so nested references tag correctly. A stale hash (error 382) falls back to published
  content. Helpers: `asset`, `text`, `strings`, `list`, `rteToHtml` (JSON rich text to HTML with `jsonToHTML` from `@contentstack/utils`), `cslp`
  (edit tags of an entry).
- **`mapper.ts`**: entries to the model. A `page` entry becomes a `Page` whose `components` are mapped block by block; a `collection` block's `items` are
  joined by uid to the entries of its `kind` (spotlights, guides, posts, FAQs), each list fetched once per request and locale.
- **`index.ts`**: the provider object that adds the preview parameters to each mapper call.
- **`live-preview.tsx`** and **`edit-support.tsx`**: the SDK initialisation, see [live-preview-and-visual-editor.md](live-preview-and-visual-editor.md).

Detail entries are looked up by their **`url` field** (`/blog/<slug>`, `/guides/<slug>`), pages by `/<key>` (`/` for `home`). Slugs are identical in every
locale (see [decisions.md](decisions.md)). `lib/blog.ts`, `lib/site.ts`, `lib/cslp.ts` and `lib/rte.ts` of the earlier version no longer exist.

### BigCommerce: `lib/bigcommerce.ts`

A thin GraphQL client (`gql()`), the query fragments, and typed functions. Details in [bigcommerce.md](bigcommerce.md).

## 2. Pages

| Route | File | Data |
|---|---|---|
| `/` | `app/[locale]/page.tsx` | the Page with key `home`: its blocks, with BigCommerce cards where a block needs them |
| `/faq`, `/guides`, `/blog`, any page an editor adds | `[...slug]/page.tsx` | the `page` entry whose `url` is `/<key>`, rendered block by block (404 if there is none) |
| `/blog/[slug]` | `blog/[slug]/page.tsx` | one `blog_landing_page` (`PostView`: content blocks, author sidebar, related posts by the same author) |
| `/guides/[slug]` | `guides/[slug]/page.tsx` | one `buying_guide` (`GuideView`), related FAQs, live BigCommerce products |
| `/products` | `products/page.tsx` | BigCommerce faceted search over the whole catalog |
| `/products/<category>…` | `products/[...slug]/page.tsx` | category **or** product (see below) |
| `/cart` | `cart/page.tsx` | BigCommerce cart |

`components/page-content.tsx` holds `PageContent`, `PostContent` and `GuideContent`; `components/page-blocks.tsx` has one view per block type.
All pages accept `?live_preview=…` (preview); the layout renders `<EditSupport>`, which loads the editing SDK for preview requests and for requests
framed by Contentstack's app.

### The catalog routes

BigCommerce translates catalog URLs, so the catalog lives at `/products/...` in English and `/fr/produits/...` in French (the root category
"Products" is "Produits" in French, and every category and product slug below it is translated too). The routes are
`app/[locale]/products/page.tsx` (listing) and `app/[locale]/products/[...slug]/page.tsx` (category or product). The route is static: `proxy.ts`
rewrites a language's translated root onto it (`/fr/produits/...` to `/fr/products/...`) and passes the requested root in the `x-catalog-root` header
(`requestedCatalogRoot()` in `lib/catalog-route.ts`), compared with `CATALOG_ROOT` in `lib/i18n.ts`. Keeping the catalog off a dynamic `[root]` segment
leaves `[...slug]` free for the content pages.

- The page rebuilds the BigCommerce path from `root` and the slug (`/produits/batteries-automobiles/...`) and resolves it **in the page's
  language**: a path only resolves in its own language. **One or two segments are categories, three or more are products.** If the guess is
  wrong the other interpretation is tried, and `notFound()` is raised if neither resolves.
- `ensureCatalogRoot()` (`lib/catalog-route.ts`): another language's root (an old or content-stored link such as `/fr/products/...`) is
  **permanently redirected** to the same page in this language; any other first segment is a 404.
- Product and category reads include `locales`, BigCommerce's list of the page's path in every language. It feeds `hreflang` / canonical
  tags (`alternatesFromPaths`) and the language switcher.
- **Language switcher:** on a catalog page it links to `/api/switch-locale?to=fr&path=<current path>`, which looks up the page's path in the
  target language and redirects (307), keeping the other query parameters and dropping attribute filters (`f.*`, whose values are translated).
  Other pages just swap the `/fr` prefix.
- `localePath(locale, "/products")` (the bare catalog link used in navigation, footer, buttons and breadcrumbs) maps to the language's root.
  Tiles and the mega menu use the translated paths from the category tree; tile photos are matched by category id.

## 3. Home page

The `page` entry with url `/` drives it, as a list of `components` blocks in the order the editor chose (the seeded order is below):

- **Hero block** (`components/hero.tsx`, `variant: home`): headline, description, button, `image` and `second_image` (the two staggered photos, both
  editable inline). A secondary "All products" button is added in code.
- **Text block**: the intro.
- **Collection block, kind `categories`** (`components/category-tiles.tsx`): the five top-level catalog categories as a photo mosaic. The
  photos are static files in `public/images/categories/`; labels are localized (`categoryLabel`).
- **Feature blocks** (title, copy, image, layout `image_left` / `image_right`); consecutive ones share one band.
- **Collection block, kind `spotlights`** (trade favourites): the referenced `product_spotlight` entries, enriched with live BigCommerce price, photo and link.
- **Collection block, kind `guides`**: the referenced guides (the first three as seeded).

![Trade favourites](images/home-spotlights.jpg)
*Trade favourites: editorial content from Contentstack with live price, photo and link from BigCommerce.*

![A value block](images/home-blocks.jpg)
*A value block (a feature block: title, copy, image, layout).*

![From the buying guides](images/home-guides.jpg)
*The guides strip: the first three guides, with photo, audience and read time.*

## 4. Navigation, mega menu and announcement bar

- **Header links** come from the `site_navigation` entry. The link whose `href` is `/products` is replaced by the
  **mega menu**.
- **Mega menu** (`components/mega-menu.tsx`, columns built in `components/site-chrome.tsx → megaColumns`): the live
  BigCommerce category tree (top level with subcategories and product counts), localized labels and a photo per top-level
  category. Hover previews it; a click pins it open; Escape, an outside click or navigating closes it. The panel is
  absolutely positioned under the header.
- **Announcement bar**: the first `announcement_bar` that is active, inside its date window and aimed at guests
  (`audience` is `everyone` or `guests`); style `info` (ink), `promo` or `warning` (amber).
- **Footer** columns, contact details and legal line come from `site_navigation`.
- **Cart link** shows the item count by reading the cart cookie and asking BigCommerce (`CartLink`, in a `Suspense`).

![Product mega menu](images/mega-menu.jpg)
*The mega menu: five top-level categories with photos, subcategories and live product counts.*

## 5. Product listing and categories

`components/plp.tsx` renders: search box, result count, **active filter chips**, "Clear all", sort, facets, product
grid and pager. It is a plain GET `<form>`, wrapped by `components/plp-form.tsx`.

![Product listing](images/plp.jpg)
*A category with a search term and a technology filter applied: result count, chips with "Clear all", sort, facets, product grid.*

### Query parameters

| Parameter | Meaning |
|---|---|
| `q` | search text (3+ characters) |
| `brand` (repeatable) | brand entity IDs |
| `f.Technology`, `f.Voltage`, `f.Warranty` (repeatable) | attribute facet values |
| `min`, `max` | price range |
| `sort` | `featured` (default), `newest`, `best_selling`, `price_asc`, `price_desc`, `name_asc` |
| `after` / `before` | cursor pagination |

`parseCatalogParams()` reads them; `searchCatalog()` runs the query ([bigcommerce.md](bigcommerce.md)).

### Interaction model

- **Filters apply on click.** `PlpForm` listens for checkbox changes, serialises the form to a URL and calls
  `router.push(url, { scroll: false })` inside `useTransition`. The grid dims (`group-data-[pending=true]:opacity-50`)
  while the server re-renders. Without JavaScript the form still works as a normal GET form (a `<noscript>` button).
- **Search as you type** (`components/search-box.tsx`): submits 350 ms after typing stops, only for 3+ characters (or
  when emptied). One or two characters show a hint and do nothing; Enter is ignored below three.
- **Price range** (`components/price-range.tsx`): applies 700 ms after typing stops.
- **Chips and "Clear all"** are server-rendered links computed from the current parameters. Removing a chip changes the
  URL; the checkboxes, search box and price inputs then **reset themselves** to match: checkboxes via a `key` that
  includes their selected state, the search box and price range by comparing the URL value with the last value they sent.
- **Cursors reset on any filter change** (only `after`/`before` links keep them), because a cursor is valid only for the
  same filters and sort.
- Each facet shows at most **8 values** (`MAX_FACET_VALUES`), most populated first, and always keeps selected values.
- On screens narrower than 1024 px the filter panel starts **collapsed** (`components/filters-details.tsx`) so the grid is
  visible first; it stays open on desktop and without JavaScript.

![Filter sidebar](images/plp-filters.jpg)
*The filter sidebar for a category: brand, technology, voltage and warranty facets (at most 8 values each) and a price range.*

### Categories include subcategory products

A category's own product list is often empty (products sit in subcategories). The category page therefore runs the
faceted search with `categoryEntityId`, which includes all descendants, instead of reading `category.products`.

## 6. Product detail page

`ProductView` in `products/[...slug]/page.tsx`:

![Product page](images/pdp.jpg)
*The product page: gallery, brand, price with stock indicator, spotlight tagline, key specs and add to cart.*

- **Gallery** (`product-gallery.tsx`): main image + thumbnails (client state).
- **Header**: brand, name, SKU / MPN, price (sale and retail "was" price when applicable), stock indicator.
- **Spotlight join**: if a `product_spotlight` entry has `bc_product_id` equal to this product, its **tagline**, badge and
  **"Best for"** use cases appear. **Guides join**: guides whose `recommended_bc_products` contains the ID are listed.
- **Key specs** (Voltage, Capacity, CCA, Technology, Warranty) and the full **specification table** come from
  BigCommerce custom fields; names and common values are translated by `translateSpec()`.
- **Volume pricing** table renders when BigCommerce returns bulk-pricing tiers.
- **Add to cart** (`components/add-to-cart.tsx`) respects the product's min/max purchase quantity.
- **Related products** from BigCommerce's `relatedProducts`.
- **Structured data**: a `schema.org/Product` JSON-LD block (price, currency, availability, SKU, GTIN, brand, images).
- **Metadata**: title, description, Open Graph image and hreflang alternates.

![Description and specifications](images/pdp-details.jpg)
*Description, "Best for" use cases from the product spotlight, and the specification table from BigCommerce custom fields.*

## 7. Cart

- **State** lives in BigCommerce; the browser keeps only the cart ID in an httpOnly cookie `bc_cart_id` (30 days).
- **Server actions** (`app/actions/cart.ts`): `addToCartAction`, `setCartQuantityAction`, `removeFromCartAction`. Each
  creates the cart if needed, calls the BigCommerce mutation and `revalidatePath("/", "layout")` so the header badge refreshes.
- **`CartView`** (`components/cart-view.tsx`) edits optimistically:
  1. A quantity change updates the line total and the subtotal immediately.
  2. The save is debounced 500 ms per line; "Updating…" shows while anything is pending; checkout is disabled meanwhile.
  3. On success it calls `router.refresh()` to reload the server's numbers; on failure it shows an error and the server's
     numbers return on the next refresh. The subtotal shows the optimistic total until those fresh numbers arrive, so it never flashes
     the previous value in between.
  4. Removing is quantity 0 (saved immediately).
- **`QtyStepper`**: −, a typeable field (commits on blur/Enter), +; Arrow Up/Down keys; clamped to 1–999; accessible labels.
- **Checkout**: the cart's `redirectedCheckoutUrl` (BigCommerce hosted checkout) is created on each cart read.

![Cart](images/cart.jpg)
*The cart with quantity steppers: totals update instantly and save to BigCommerce after a short pause.*

## 8. Content pages

- **Blog**: the `/blog` page is a `page` entry: a hero, a `posts` collection (latest articles) and a `postListing` collection (search, a
  text match over title and description, and all posts). A post page shows its `content` blocks (text, image, video), `read_time`, a main column
  with an author sidebar and related posts. Dates and labels follow the locale.
- **Buying guides**: the `/guides` page is a hero plus a `guideListing` collection (guide cards); guide page with numbered steps (a true sequence), pro tips, a checklist, related FAQs and
  **recommended products** that link to product pages with live price.
- **FAQ**: the `/faq` page is a hero plus a `faqs` collection, grouped by `topic` (the select value is English; `topicLabel()` shows the French label), native
  `<details>` accordions.

![A buying guide](images/guide.jpg)
*A buying guide: numbered steps, pro tips, a checklist panel and recommended products with live prices.*

![FAQ page](images/faq.jpg)
*The FAQ page: hero banner, then questions grouped by topic.*

![A blog post](images/blog-post.jpg)
*A blog post: main column plus an author card.*

## 9. Editing support

`components/edit-support.tsx` loads the editing SDK (`providers/cms/contentstack/live-preview.tsx`) for preview requests and for requests the proxy
marked `x-editor`; `data-cslp` attributes are spread with `tag(entity, field)` (`core/edit.ts`) on key elements, and the component list of a page
is wrapped (`tag(page, "components")`) so blocks can be reordered. See [live-preview-and-visual-editor.md](live-preview-and-visual-editor.md).

## 10. Internationalization

Routing in `proxy.ts`, strings and helpers in `lib/i18n.ts`. See [i18n.md](i18n.md).

## 11. Where to change things

| I want to… | Change |
|---|---|
| Edit wording, banners, FAQs, guides, nav | Contentstack (no code) |
| Add a UI string | `lib/i18n.ts` (`en` and `fr` objects, type-checked to match) |
| Add a filterable attribute | `FACET_NAMES` in `lib/bigcommerce.ts` (+ French label in `SPEC_NAMES_FR`) |
| Change the mega menu | `megaColumns()` in `components/site-chrome.tsx`, `components/mega-menu.tsx` |
| Change colours, type, spacing | tokens in `app/globals.css` |
| Add a page | create a `page` entry (url `/<key>`) with `components` in Contentstack: `[...slug]` renders it, no code |
| Add a block type | a field in `page.components` (`tools/contentstack/blocks.py`), the type in `core/content.ts`, the mapper (`block()`), a case in `components/page-blocks.tsx` |
| Add a content route | new route under `app/[locale]/`, a read in the provider (`mapper.ts`, `index.ts`, `core/content.ts`), edit tags, a seed |
