import { cache } from "react";
import type { Announcement, Author, Block, Faq, Guide, Hero, Img, Navigation, Page, Post, PostBlock, Spotlight } from "@/core/content";
import type { Tags } from "@/core/edit";
import type { Locale } from "@/lib/i18n";
import { asset, cslp, entries, list, rteToHtml, strings, text, type Entry, type PreviewParams } from "./client";

// Entries -> the canonical content model (core/content.ts). `$` carries Live Preview edit tags for preview requests only.
const img = (a: Entry | undefined, alt?: string): Img | undefined => {
  const x = asset(a);
  return x ? { url: x.url, alt: alt || x.alt } : undefined;
};
const t = (obj: Entry | undefined, map: Record<string, string> = {}): { $?: Tags } => (obj?.$ ? { $: cslp(obj, map) } : {});

const author = (e: Entry): Author => ({ name: e.title, avatar: img(e.picture, e.title), bio: text(e.bio), ...t(e, { name: "title", avatar: "picture" }) });

const faq = (e: Entry): Faq => ({
  id: e.uid,
  question: e.title,
  answerHtml: rteToHtml(e.answer),
  topic: e.topic,
  sortOrder: typeof e.sort_order === "number" ? e.sort_order : 0,
  featured: !!e.is_featured,
  ...t(e, { question: "title", answerHtml: "answer" }),
});

const guide = (e: Entry, order: number): Guide => {
  const skus = strings(e.recommended_skus);
  return {
    id: e.uid,
    url: e.url,
    title: e.title,
    summary: e.summary,
    image: img(e.hero_image, e.title),
    audience: text(e.audience),
    readMinutes: typeof e.read_minutes === "number" ? e.read_minutes : undefined,
    sortOrder: order,
    steps: list(e.steps).map((s) => ({ title: s.step_title, body: s.step_body, proTip: text(s.pro_tip), ...t(s, { title: "step_title", body: "step_body", proTip: "pro_tip" }) })),
    checklist: strings(e.checklist),
    recommendedProducts: (Array.isArray(e.recommended_bc_products) ? e.recommended_bc_products : []).map((id: number, i: number) => ({ bcProductId: id, sku: skus[i] })),
    relatedFaqs: list(e.related_faqs).filter((f) => f.title).map(faq),
    author: list(e.author)[0] ? author(list(e.author)[0]) : undefined,
    ...t(e, { image: "hero_image" }),
  };
};

const spotlight = (e: Entry): Spotlight => ({
  id: e.uid,
  title: e.title,
  bcProductId: Number(e.bc_product_id),
  bcSku: text(e.bc_sku),
  tagline: e.tagline,
  badge: text(e.badge),
  image: img(e.editorial_image, e.title),
  featured: !!e.is_featured,
  keyFeatures: strings(e.key_features),
  useCases: list(e.use_cases).map((u) => ({ title: u.use_case, description: text(u.description), ...t(u, { title: "use_case" }) })),
  ...t(e, { image: "editorial_image" }),
});

const postBlocks = (blocks: unknown): PostBlock[] =>
  list(blocks).flatMap((b): PostBlock[] => {
    if (b.text) return [{ type: "text", html: rteToHtml(b.text.text), ...t(b.text, { html: "text" }) }];
    if (b.image) {
      const i = img(b.image.image, text(b.image.alt));
      return i ? [{ type: "image", img: i, ...t(b.image, { img: "image" }) }] : [];
    }
    if (b.video) return [{ type: "video", title: b.video.video_title ?? "", src: b.video.src, ...t(b.video, { title: "video_title" }) }];
    return [];
  });

const post = (e: Entry): Post => ({
  id: e.uid,
  url: e.url,
  title: e.title,
  description: text(e.seo?.meta_description),
  date: text(e.date),
  readTime: typeof e.read_time === "number" ? e.read_time : undefined,
  image: img(e.featured_image, e.title),
  authors: list(e.author).filter((a) => a.title).map(author),
  blocks: postBlocks(e.content),
  ...t(e, { image: "featured_image", blocks: "content" }),
});

// ---------------------------------------------------------------- lists (once per request and locale), joined to collections by uid
const GUIDE_REFS = ["author", "related_faqs"];
const faqMap = cache(async (l: Locale, p?: string) => new Map((await entries("faq", l, pp(p))).map((e) => [e.uid, faq(e)])));
const guideMap = cache(async (l: Locale, p?: string) => new Map((await entries("buying_guide", l, pp(p), { refs: GUIDE_REFS, orderAsc: "created_at" })).map((e, i) => [e.uid, guide(e, i)])));
const spotlightMap = cache(async (l: Locale, p?: string) => new Map((await entries("product_spotlight", l, pp(p), { orderAsc: "created_at" })).map((e) => [e.uid, spotlight(e)])));
const postMap = cache(async (l: Locale, p?: string) => new Map((await entries("blog_landing_page", l, pp(p), { refs: ["author"], order: "date" })).map((e) => [e.uid, post(e)])));
// React `cache()` keys on primitives: the preview parameters travel as a JSON string.
const pp = (p?: string) => (p ? (JSON.parse(p) as PreviewParams) : undefined);
const ps = (p?: PreviewParams) => (p ? JSON.stringify(p) : undefined);

// ---------------------------------------------------------------- blocks
const hero = (b: Entry): Hero => ({
  title: b.title,
  description: text(b.description),
  image: img(b.image, b.title),
  secondImage: img(b.second_image, b.title),
  cta: b.cta?.title || b.cta?.href ? { label: text(b.cta.title), href: text(b.cta.href) } : undefined,
  variant: b.variant === "home" ? "home" : "default",
  ...t(b, { cta: "cta", secondImage: "second_image" }),
});

async function collection(b: Entry, l: Locale, p?: PreviewParams): Promise<Block[]> {
  const tg = t(b, { linkLabel: "link_label", searchPlaceholder: "search_placeholder", searchButtonLabel: "search_button_label" });
  const uids = list(b.items).map((i) => i.uid as string);
  const pick = <T,>(m: Map<string, T>) => uids.map((u) => m.get(u)).filter((x): x is T => !!x);
  switch (b.kind) {
    case "categories":
      return [{ type: "categories", title: text(b.title), ...tg }];
    case "spotlights":
      return [{ type: "spotlights", title: text(b.title), items: pick(await spotlightMap(l, ps(p))), ...tg }];
    case "guides":
      return [{ type: "guides", title: text(b.title), linkLabel: text(b.link_label), items: pick(await guideMap(l, ps(p))), ...tg }];
    case "posts":
      return [{ type: "posts", title: text(b.title), items: pick(await postMap(l, ps(p))), ...tg }];
    case "postListing":
      return [{ type: "postListing", title: text(b.title), searchPlaceholder: text(b.search_placeholder), searchButtonLabel: text(b.search_button_label), ...tg }];
    case "guideListing":
      return [{ type: "guideListing", title: text(b.title), ...tg }];
    case "faqs":
      return [{ type: "faqs", items: pick(await faqMap(l, ps(p))).sort((x, y) => x.sortOrder - y.sortOrder), ...tg }];
    default:
      return [];
  }
}

async function block(item: Entry, l: Locale, p?: PreviewParams): Promise<Block[]> {
  if (item.hero) return [{ type: "hero", hero: hero(item.hero), ...t(item.hero, { cta: "cta", secondImage: "second_image" }) }];
  if (item.feature) {
    const f = item.feature;
    return [{ type: "feature", title: f.title, html: rteToHtml(f.copy), image: img(f.image, f.title), layout: f.layout === "image_right" ? "image_right" : "image_left", ...t(f, { html: "copy" }) }];
  }
  if (item.text) return [{ type: "text", html: rteToHtml(item.text.text), ...t(item.text, { html: "text" }) }];
  if (item.image) {
    const i = img(item.image.image, text(item.image.alt));
    return i ? [{ type: "image", img: i, ...t(item.image, { img: "image" }) }] : [];
  }
  if (item.video) return [{ type: "video", title: item.video.video_title ?? "", src: item.video.src, ...t(item.video, { title: "video_title" }) }];
  if (item.collection) return collection(item.collection, l, p);
  return [];
}

// ---------------------------------------------------------------- queries
export async function getPage(key: string, locale: Locale, preview?: PreviewParams): Promise<Page | undefined> {
  const [e] = await entries("page", locale, preview, { url: key === "home" ? "/" : `/${key}` });
  if (!e) return undefined;
  const blocks = (await Promise.all(list(e.components).map((c) => block(c, locale, preview)))).flat();
  return { title: e.title, description: text(e.description), blocks, ...t(e, { blocks: "components" }) };
}

async function announcements(locale: Locale, preview?: PreviewParams): Promise<Announcement[]> {
  const now = Date.now();
  return (await entries("announcement_bar", locale, preview, { orderAsc: "created_at" }))
    .filter((e) => e.is_active !== false && (!e.starts_at || Date.parse(e.starts_at) <= now) && (!e.ends_at || Date.parse(e.ends_at) >= now))
    .map((e) => ({
      message: e.message,
      cta: e.cta?.title || e.cta?.href ? { label: text(e.cta.title), href: text(e.cta.href) } : undefined,
      style: e.style,
      audience: e.audience,
      ...t(e),
    }));
}

export async function getNavigation(locale: Locale, preview?: PreviewParams): Promise<Navigation | undefined> {
  const [e] = await entries("site_navigation", locale, preview);
  if (!e) return undefined;
  return {
    headerLinks: list(e.header_links).map((l) => ({ label: l.label, href: l.href, highlight: !!l.highlight })),
    footerColumns: list(e.footer_columns).map((c) => ({ heading: c.heading, links: list(c.links).map((l) => ({ label: l.label, href: l.href })) })),
    contact: { salesEmail: text(e.contact?.sales_email), supportPhone: text(e.contact?.support_phone), openingHours: text(e.contact?.opening_hours) },
    legalText: text(e.legal_text),
    announcements: await announcements(locale, preview),
  };
}

export async function getAnnouncement(locale: Locale, preview?: PreviewParams, audience: "guests" | "logged_in" = "guests") {
  return (await announcements(locale, preview)).find((a) => a.audience === "everyone" || a.audience === audience);
}

export async function getPosts(locale: Locale, preview?: PreviewParams) {
  return [...(await postMap(locale, ps(preview))).values()];
}

export async function getPost(slug: string, locale: Locale, preview?: PreviewParams) {
  const [e] = await entries("blog_landing_page", locale, preview, { refs: ["author"], url: `/blog/${slug}` });
  return e ? post(e) : undefined;
}

export async function getGuides(locale: Locale, preview?: PreviewParams) {
  return [...(await guideMap(locale, ps(preview))).values()];
}

export async function getGuide(slug: string, locale: Locale, preview?: PreviewParams) {
  const [e] = await entries("buying_guide", locale, preview, { refs: GUIDE_REFS, url: `/guides/${slug}` });
  return e ? guide(e, 0) : undefined;
}

export async function getSpotlights(locale: Locale, preview?: PreviewParams) {
  return [...(await spotlightMap(locale, ps(preview))).values()];
}
