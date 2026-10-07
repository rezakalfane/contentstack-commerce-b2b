import { API_KEY, APP_HOST, ENVIRONMENT } from "./client";
import { LivePreview } from "./live-preview";

/** Loads Contentstack's Live Preview SDK. Rendered only for verified preview requests, see components/edit-support.tsx. */
export function EditSupport() {
  return <LivePreview apiKey={API_KEY} environment={ENVIRONMENT} appHost={APP_HOST} />;
}
