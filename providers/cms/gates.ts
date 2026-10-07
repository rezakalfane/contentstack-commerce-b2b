/**
 * Draft gate: does this request carry Live Preview's parameters? Run by `proxy.ts`, which then sets the trusted `x-preview` header.
 * Live Preview adds `live_preview=<hash>` (plus the entry being edited); the Preview token stays on the server, and the hash is only
 * useful together with it.
 */
export const previewGate = (params: URLSearchParams): boolean => !!params.get("live_preview");
