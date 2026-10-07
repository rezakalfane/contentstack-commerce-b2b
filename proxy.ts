import { NextResponse, type NextRequest } from "next/server";
import { localeOfCatalogRoot } from "@/lib/i18n";
import { FRAME_ANCESTORS } from "@/providers/cms/meta";
import { previewGate } from "@/providers/cms/gates";

const PREVIEW_HEADERS = { "x-cs-live-preview": "live_preview", "x-cs-content-type": "content_type_uid", "x-cs-entry": "entry_uid", "x-cs-timestamp": "preview_timestamp", "x-cs-release": "release_id" };

/** An iframe navigation whose parent page is Contentstack's app (`Referer` carries its origin). */
function framedByContentstack(request: NextRequest): boolean {
  if (request.headers.get("sec-fetch-dest") !== "iframe") return false;
  try {
    const origin = new URL(request.headers.get("referer") ?? "").origin;
    return FRAME_ANCESTORS.some((pattern) => new RegExp(`^${pattern.replace(/[.]/g, "\\.").replace("*", "[^/]+")}$`).test(origin));
  } catch {
    return false;
  }
}

/**
 * Locale routing. English (default) has clean URLs and is rewritten internally to /en/...;
 * French lives under /fr. An explicit /en prefix redirects to the clean URL so each page has one address.
 * `headers` are the request headers passed on to the page (x-preview, x-catalog-root).
 */
function route(request: NextRequest, headers: Headers) {
  const { pathname } = request.nextUrl;
  const first = pathname.split("/")[1];

  // The editor's content preview URL for the home page is `/<locale>/home` (the `home` page slug): serve it at the home page.
  if (pathname === "/home" || pathname === "/fr/home") {
    const url = request.nextUrl.clone();
    url.pathname = pathname === "/home" ? "/en" : "/fr";
    return NextResponse.rewrite(url, { request: { headers } });
  }

  // Catalog URLs are translated (/products/..., /fr/produits/...). The route lives at /products, so another root is rewritten onto it
  // and the requested root travels in a header (see requestedCatalogRoot in lib/catalog-route.ts).
  const catalogRewrite = (prefix: string, rest: string) => {
    const seg = rest.split("/")[1];
    if (!seg || seg === "products" || !localeOfCatalogRoot(seg)) return null;
    const url = request.nextUrl.clone();
    url.pathname = `${prefix}/products${rest.slice(seg.length + 1)}`;
    const withRoot = new Headers(headers);
    withRoot.set("x-catalog-root", seg);
    return NextResponse.rewrite(url, { request: { headers: withRoot } });
  };

  if (first === "fr") return catalogRewrite("/fr", pathname.slice(3) || "/") ?? NextResponse.next({ request: { headers } });

  if (first === "en") {
    const url = request.nextUrl.clone();
    url.pathname = pathname.replace(/^\/en/, "") || "/";
    return NextResponse.redirect(url, 308);
  }

  const rewritten = catalogRewrite("/en", pathname);
  if (rewritten) return rewritten;
  const url = request.nextUrl.clone();
  url.pathname = `/en${pathname === "/" ? "" : pathname}`;
  return NextResponse.rewrite(url, { request: { headers } });
}

export function proxy(request: NextRequest) {
  // Request headers the app trusts: set here, never taken from the client.
  const headers = new Headers(request.headers);
  headers.delete("x-preview");
  headers.delete("x-editor");
  for (const h of Object.keys(PREVIEW_HEADERS)) headers.delete(h);
  const q = request.nextUrl.searchParams;
  if (previewGate(q)) {
    headers.set("x-preview", "1");
    // Live Preview's parameters (the draft hash and the entry being edited) travel to the data layer as trusted headers.
    for (const [header, param] of Object.entries(PREVIEW_HEADERS)) if (q.get(param)) headers.set(header, q.get(param)!);
  }
  if (q.has("live_preview") || framedByContentstack(request)) headers.set("x-editor", "1");

  const response = route(request, headers);

  // Only Contentstack's app may frame the site (localhost too, in development).
  const dev = process.env.NODE_ENV !== "production";
  const ancestors = ["'self'", ...FRAME_ANCESTORS, ...(dev ? ["http://localhost:*", "https://localhost:*"] : [])];
  response.headers.set("Content-Security-Policy", `frame-ancestors ${ancestors.join(" ")}`);
  // Which Contentstack environment this deployment reads (not a secret). Handy to confirm a switch.
  response.headers.set("X-Content-Environment", process.env.CONTENTSTACK_ENVIRONMENT ?? "unset");
  return response;
}

export const config = {
  // Skip Next internals and any path with a file extension (images, favicon, etc.)
  matcher: ["/((?!_next|api|.*\\..*).*)"],
};
