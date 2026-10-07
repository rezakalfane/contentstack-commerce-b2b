import contentstack, { Region } from "@contentstack/delivery-sdk";
import { addEditableTags, jsonToHTML } from "@contentstack/utils";
import { headers } from "next/headers";
import type { Tags } from "@/core/edit";
import type { Locale } from "@/lib/i18n";

const REGION = (process.env.CONTENTSTACK_REGION ?? "us").trim().toLowerCase();
const REGIONS: Record<string, Region> = {
  us: Region.US, eu: Region.EU, au: Region.AU, "azure-na": Region.AZURE_NA, "azure-eu": Region.AZURE_EU, "gcp-na": Region.GCP_NA,
};
const PREFIX = REGION === "us" ? "" : `${REGION}-`;
const PREVIEW_HOST = `${PREFIX}rest-preview.contentstack.com`;

/** Host of the Contentstack web app, used by the Live Preview frame. */
export const APP_HOST = `${PREFIX}app.contentstack.com`;
export const API_KEY = process.env.CONTENTSTACK_API_KEY ?? "";
export const ENVIRONMENT = process.env.CONTENTSTACK_ENVIRONMENT ?? "";

/** The CMS locale of each storefront locale. */
const CS_LOCALE: Record<Locale, string> = { en: "en-us", fr: "fr-fr" };

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Entry = Record<string, any>;

/** What Contentstack adds to the preview URL inside Live Preview; `proxy.ts` verifies the request and passes these on as `x-cs-*` headers. */
export type PreviewParams = { live_preview: string; content_type_uid?: string; entry_uid?: string; preview_timestamp?: string; release_id?: string };

export async function previewParams(): Promise<PreviewParams | undefined> {
  const h = await headers();
  const live_preview = h.get("x-cs-live-preview");
  if (!live_preview) return undefined;
  return {
    live_preview,
    content_type_uid: h.get("x-cs-content-type") ?? undefined,
    entry_uid: h.get("x-cs-entry") ?? undefined,
    preview_timestamp: h.get("x-cs-timestamp") ?? undefined,
    release_id: h.get("x-cs-release") ?? undefined,
  };
}

const baseConfig = () => ({
  apiKey: API_KEY,
  deliveryToken: process.env.CONTENTSTACK_DELIVERY_TOKEN ?? "",
  environment: ENVIRONMENT,
  region: REGIONS[REGION] ?? Region.US,
});

const sharedStack = contentstack.stack(baseConfig());

/** The shared delivery stack, or a fresh one per request in Live Preview: `livePreviewQuery` mutates the stack, so they must not be shared. */
function getStack(preview?: PreviewParams) {
  if (!preview) return sharedStack;
  const stack = contentstack.stack({ ...baseConfig(), live_preview: { enable: true, preview_token: process.env.CONTENTSTACK_PREVIEW_TOKEN ?? "", host: PREVIEW_HOST } });
  stack.livePreviewQuery(preview);
  return stack;
}

/**
 * Entries of a content type in a locale (falling back to the default locale when untranslated), up to 100, with their edit tags in
 * preview. `refs` are reference fields to resolve (`author`, `related_faqs`...); `url` finds one entry by its URL.
 */
export async function entries(contentType: string, locale: Locale, preview?: PreviewParams, opts: { refs?: string[]; url?: string; order?: string; orderAsc?: string } = {}) {
  const run = async (p?: PreviewParams) => {
    let q = getStack(p).contentType(contentType).entry().locale(CS_LOCALE[locale]).includeFallback();
    if (p) q = q.includeReferenceContentTypeUID(); // referenced entries carry their content type so nested edit tags resolve
    if (opts.refs?.length) q = q.includeReference(...opts.refs);
    let query = q.query(opts.url ? { url: opts.url } : undefined);
    if (opts.order) query = query.orderByDescending(opts.order);
    if (opts.orderAsc) query = query.orderByAscending(opts.orderAsc);
    return (await query.limit(100).find<Entry>()).entries ?? [];
  };
  let found: Entry[];
  try {
    found = (await run(preview)) as Entry[];
  } catch (e) {
    // A stale or invalid Live Preview hash ("tracker no longer exists", code 382) shows the published content instead of failing the page.
    if (!preview || (e as { error_code?: number }).error_code !== 382) throw e;
    return entries(contentType, locale, undefined, opts);
  }
  const seen = new Set<string>(); // the preview API can return an entry twice, which breaks React keys
  const list = found.filter((e) => !e.uid || (!seen.has(e.uid) && seen.add(e.uid)));
  if (preview) for (const e of list) addEditableTags(e as never, contentType, true, CS_LOCALE[locale]);
  return list;
}

// ---------------------------------------------------------------- mapping helpers
export const asset = (a?: Entry): { url: string; alt: string } | undefined => (a?.url ? { url: a.url, alt: a.title || "" } : undefined);
export const text = (v: unknown) => (typeof v === "string" && v ? v : undefined);
export const strings = (v: unknown): string[] => (Array.isArray(v) ? v.map(String).map((s) => s.trim()).filter(Boolean) : []);
export const list = (v: unknown): Entry[] => (Array.isArray(v) ? (v as Entry[]) : v && typeof v === "object" ? [v as Entry] : []);

/** JSON rich text to HTML. */
export function rteToHtml(value: unknown): string {
  if (!value || typeof value !== "object") return "";
  try {
    const holder = { v: JSON.parse(JSON.stringify(value)) } as never;
    jsonToHTML({ entry: holder, paths: ["v"] });
    return (holder as { v: string }).v;
  } catch {
    return "";
  }
}

/** Edit tags of an object from `addEditableTags` (`obj.$.<field>` is `{ "data-cslp": ... }`); `map` renames our field names to the field uid. Empty outside preview. */
export function cslp(obj: Entry | undefined, map: Record<string, string> = {}): Tags {
  const tags = obj?.$ as Entry | undefined;
  if (!tags) return {};
  return new Proxy({}, { get: (_, key) => (typeof key === "string" ? (tags[map[key] ?? key] ?? {}) : undefined) });
}
