"use client";

import ContentstackLivePreview from "@contentstack/live-preview-utils";
import { useEffect } from "react";

// The SDK must be initialised exactly once per page load.
let ready: Promise<unknown> | undefined;

/**
 * Boots Contentstack Live Preview (SSR mode): every edit in the entry form makes the preview pane request fresh HTML, which the server
 * renders from the unsaved draft (the draft hash comes from the editor's URL, see `proxy.ts`). `data-cslp` attributes make fields
 * click-to-edit. `mode: "builder"` points "Start Editing" at the Visual Editor.
 */
export function LivePreview({ apiKey, environment, appHost }: { apiKey: string; environment: string; appHost: string }) {
  useEffect(() => {
    ready ??= ContentstackLivePreview.init({
      ssr: true,
      enable: true,
      mode: "builder",
      stackDetails: { apiKey, environment },
      clientUrlParams: { protocol: "https", host: appHost, port: 443 },
      editButton: { enable: true, position: "top-right" },
      editInVisualBuilderButton: { enable: true, position: "bottom-right" },
      // Hero images sit under a gradient overlay: let the SDK see fields that are visually covered.
      overlayPropagation: { enable: true },
    });
  }, [apiKey, environment, appHost]);
  return null;
}
