import { EditSupport as Contentstack } from "@/providers/cms/contentstack/edit-support";
import { inEditor, isPreviewRequest } from "@/lib/request";

/**
 * Loads Contentstack's Live Preview SDK for verified preview requests (x-preview) and for any request framed by Contentstack's app:
 * the pane's first request carries no draft hash yet, but the SDK must already be on that page to take over afterwards.
 */
export async function EditSupport() {
  return (await isPreviewRequest()) || (await inEditor()) ? <Contentstack /> : null;
}
