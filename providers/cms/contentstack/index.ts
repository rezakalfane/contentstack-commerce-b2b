import type { ContentProvider } from "@/core/content";
import { previewParams } from "./client";
import * as c from "./mapper";

/** Contentstack: published entries of the stack environment; in Live Preview the draft hash from the editor's URL goes to the preview API. */
export const provider: ContentProvider = {
  id: "contentstack",
  getPage: async (key, locale) => c.getPage(key, locale, await previewParams()),
  getNavigation: async (locale) => c.getNavigation(locale, await previewParams()),
  getAnnouncement: async (locale, audience) => c.getAnnouncement(locale, await previewParams(), audience),
  getPosts: async (locale) => c.getPosts(locale, await previewParams()),
  getPost: async (slug, locale) => c.getPost(slug, locale, await previewParams()),
  getGuides: async (locale) => c.getGuides(locale, await previewParams()),
  getGuide: async (slug, locale) => c.getGuide(slug, locale, await previewParams()),
  getSpotlights: async (locale) => c.getSpotlights(locale, await previewParams()),
};
