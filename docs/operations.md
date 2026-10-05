# Operations

## Prerequisites

- Node.js 22+ and npm (the project is built and tested on Node 24).
- Python 3.12+ with Pillow for the seeding scripts (optional for running the site).
- A Contentstack stack (delivery + preview tokens; management token for seeding) and a BigCommerce store with a
  storefront channel and a Storefront API token.

## Environment variables

Copy `.env.example` to `.env.local`. **All are server-side**; none use the `NEXT_PUBLIC_` prefix.

| Variable | Required | Meaning |
|---|---|---|
| `CONTENTSTACK_API_KEY` | yes | stack API key |
| `CONTENTSTACK_DELIVERY_TOKEN` | yes | read-only token for the environment below |
| `CONTENTSTACK_PREVIEW_TOKEN` | for preview | lets Live Preview read unsaved/draft content |
| `CONTENTSTACK_ENVIRONMENT` | yes | environment name (`preview` today) |
| `CONTENTSTACK_REGION` | yes | `us`, `eu`, `au`, `azure-na`, `azure-eu` or `gcp-na` (`eu` today) |
| `CONTENTSTACK_MANAGEMENT_TOKEN` | seeding only | write access; **never** needed to run the site |
| `BIGCOMMERCE_STORE_HASH` | yes | store hash |
| `BIGCOMMERCE_CHANNEL_ID` | yes | channel ID of the headless storefront channel |
| `BIGCOMMERCE_STOREFRONT_TOKEN` | yes | channel-scoped Storefront API token (one allowed origin) |
| `CONTENTSTACK_EDIT_MODE` | optional | `true` loads the editing SDK outside local development |

`.env.local` is gitignored. Do not paste token values into chats, tickets or commit messages.

## Running locally

```bash
npm install
npm run dev            # http://localhost:3000 (English), http://localhost:3000/fr (French)
```

After changing `next.config.ts`, `proxy.ts` or `.env.local`, **restart the dev server**.

Checks:

```bash
npx next typegen && npx tsc --noEmit   # types (typegen refreshes route helper types)
npm run lint
npm run build                          # production build
```

## Routine tasks

| Task | How |
|---|---|
| Change copy, FAQs, guides, banners, nav | Contentstack, then **publish** to `preview` (both locales) |
| Refresh sample content | [seeding.md](seeding.md) |
| Add a UI string | `lib/i18n.ts` (English and French) |
| Rotate the BigCommerce token | create a new token for the origin, update the variable, redeploy; old ones expire by themselves |
| Check live preview | open an entry in Contentstack → Live Preview, or Visual Experience |

### Renewing the BigCommerce Storefront token

The current token expires in **January 2027**. Create a new one for each origin you serve
(`POST /v3/storefront/api-token` with `channel_id`, `expires_at` and a single `allowed_cors_origins` entry), update
`BIGCOMMERCE_STOREFRONT_TOKEN`, and redeploy. A stale token shows up as empty product sections and `[bigcommerce] … failed`
messages in the server log.

## Deployment (for example Vercel)

1. Set every variable above in the hosting project (Production and Preview scopes). Do **not** set the management token.
2. Create a BigCommerce Storefront token whose allowed origin is the **production domain**; use it in production.
3. In Contentstack: add the production base URLs for **both locales** in Live Preview settings
   (`https://your-domain` and `https://your-domain/fr`).
4. The CSP `frame-ancestors` rule already allows Contentstack's editors.
5. Next.js on Vercel needs no extra config. `proxy.ts` runs on the Node.js runtime.

### Production readiness checklist

- [ ] Create a **`production`** environment in Contentstack (today only `preview` exists), a delivery token for it, and
      publish content there; set `CONTENTSTACK_ENVIRONMENT=production`.
- [ ] Replace all fictional sample content (authors, article text, FAQ policies, promotions, contact details).
- [ ] Add **publish webhooks** → Next.js revalidation (tags or paths), then cache Contentstack reads.
- [ ] Add BigCommerce **Store Translations** for French product content (or accept English product names).
- [ ] Decide the B2B account story: customer login, company price lists, quotes ([bigcommerce.md](bigcommerce.md)).
- [ ] `sitemap.xml`, `robots.txt`, canonical host, analytics, error monitoring.
- [ ] Review the cookie notice requirements for the cart cookie (`bc_cart_id`, strictly necessary).
- [ ] Run the checks (tsc, lint, build) and a manual pass on EN and FR: home, listing, product, cart, blog, guides, FAQ.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Pages render without images | image host not allowed | `images.remotePatterns` in `next.config.ts`, then restart |
| Empty product sections, `[bigcommerce] … failed` in the log | expired/wrong Storefront token, wrong channel host, origin mismatch | see "Renewing the token" |
| `api_key is not valid` | wrong `CONTENTSTACK_REGION` | set the region of the stack |
| Content changes not visible | not published to the environment, or the French entry is a stale copy | publish; re-run `seed_fr.py` |
| French page shows English text | no `fr-fr` version (fallback) or a UI string is missing | translate the entry / add the string |
| `Functions cannot be passed directly to Client Components` | a callback prop from a Server Component | pass data (strings), not functions |
| Product page 404 | the BigCommerce path is not on the channel, or the product is not visible | check the product's channel assignment and visibility |
| Cart badge lags | the header reads the cart after the action revalidates (~1 s) | expected |
| Live Preview errors | see [live-preview-and-visual-editor.md](live-preview-and-visual-editor.md) | |
| `Cannot find module` after moving files | stale `.next` | stop the server, delete `.next`, restart |

## Logs and diagnostics

- Server logs include `[bigcommerce] … failed: <message>` and `[cart] … failed` lines. These are the first place to look.
- `curl -s -X POST https://store-<hash>-<channel>.mybigcommerce.com/graphql -H "Authorization: Bearer $TOKEN" …`
  reproduces any GraphQL call.
- Contentstack: `GET https://eu-cdn.contentstack.com/v3/content_types?environment=preview` with `api_key` and
  `access_token` headers lists published content types.

## Known limitations

- No buyer sign-in, per-company pricing, quotes or order history (B2B Edition is not yet integrated).
- Product text is English only.
- Contentstack reads are not cached by Next.js (each request reads the CDN).
- The Contentstack free plan allows 10 content types; all are in use.
- Search on the blog is a simple in-memory text match over the 100 most recent posts.
