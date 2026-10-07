# Documentation

| Document | Read it when you want to… |
|---|---|
| [architecture.md](architecture.md) | understand how Contentstack, BigCommerce and Next.js fit together, and how a request is served |
| [implementation.md](implementation.md) | see how each feature works (listing, filters, product page, cart, hero, guides…) and where the code lives |
| [contentstack.md](contentstack.md) | work with the stack: environments, locales, the content types and the block model, publishing, limits |
| [live-preview-and-visual-editor.md](live-preview-and-visual-editor.md) | set up and debug live editing, inline (click-to-edit) editing, the editor header and per-locale preview URLs |
| [bigcommerce.md](bigcommerce.md) | work with the catalog: channel, token, the GraphQL queries, facets, categories, cart |
| [i18n.md](i18n.md) | add a language or translate content: URL strategy, fallback, dictionaries, hreflang |
| [workflow.md](workflow.md) | review content on the staging site and approve it before it goes live |
| [seeding.md](seeding.md) | create or refresh sample content with the Python scripts; the block model, backup and the prune |
| [design-system.md](design-system.md) | build UI in the "Workbench" look: tokens, type, components, imagery |
| [operations.md](operations.md) | set up environment variables, run, deploy and troubleshoot |
| [decisions.md](decisions.md) | learn why choices were made, and what was rejected |

Also see the top-level [README](../README.md) and [HISTORY](../HISTORY.md) (every request and its outcome).

## Vocabulary

- **Entry**: one piece of Contentstack content (an article, an FAQ). **Content type**: its schema.
- **Block**: an item of a modular blocks field, in an ordered list (`page.components`, `blog_landing_page.content`). A **collection block** shows a list (guides, FAQs...) by its `kind`.
- **Page key**: the URL of a `page` entry without its slash (`home` is `/`, `faq` is `/faq`, `blog` is `/blog`).
- **Locale**: a language version. Contentstack codes are `en-us` and `fr-fr`; URL prefixes are `en` (hidden) and `fr`.
- **CDA / CMA**: Contentstack's Content *Delivery* API (read, published) and Content *Management* API (write).
- **Preview**: a Contentstack environment (read by the staging site and local development), *and* the Live Preview
  feature that shows unsaved edits. Context makes clear which is meant.
- **Staging**: the Vercel site built from the `staging` branch that reads the `preview` environment ([workflow.md](workflow.md)).
- **Workflow stage**: Draft, In review or Approved; only Approved entries can be published to `production`.
- **PLP / PDP**: product listing page / product detail page.
- **Edit tag**: a `data-cslp` attribute that tells Visual Editor which field an element shows.
