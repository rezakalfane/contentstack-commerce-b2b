import { headers } from "next/headers";
import { cache } from "react";

/** True when `proxy.ts` verified the editor's preview credentials for this request (`x-preview`, never taken from the client). */
export const isPreviewRequest = cache(async (): Promise<boolean> => (await headers()).get("x-preview") === "1");

/** True when `proxy.ts` saw the request framed by Contentstack's app (`x-editor`, never taken from the client). */
export const inEditor = cache(async (): Promise<boolean> => (await headers()).get("x-editor") === "1");
