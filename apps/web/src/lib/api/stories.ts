import { apiFetch } from "./client";

export interface StoryEntry {
  id: string;
  brand_id: string;
  title: string | null;
  source_type: string;
  raw_content: string;
  extracted_stories: ExtractedStory[];
  tags: string[];
  story_tags: string[];
  pinned: boolean;
  created_at: string;
}

export interface ExtractedStory {
  summary: string;
  theme: string;
  emotion: string;
  key_quote: string;
  usable_hook: string;
}

export interface SearchResult {
  stories: ExtractedStory[];
  total: number;
}

export const storiesApi = {
  /** Create a new Story Bank entry with auto-extraction */
  async ingest(data: {
    brand_id: string;
    title?: string;
    source_type: string;
    raw_content: string;
    tags?: string[];
  }): Promise<StoryEntry> {
    return apiFetch("/stories/ingest", { method: "POST", body: JSON.stringify(data) });
  },

  /** List all Story Bank entries for a brand */
  async list(brandId: string, sourceType?: string, limit = 50): Promise<StoryEntry[]> {
    const params = new URLSearchParams({ brand_id: brandId, limit: String(limit) });
    if (sourceType) params.set("source_type", sourceType);
    return apiFetch(`/stories?${params}`);
  },

  /** Search extracted stories by topic */
  async search(brandId: string, topic: string, limit = 5): Promise<SearchResult> {
    const params = new URLSearchParams({ brand_id: brandId, topic, limit: String(limit) });
    return apiFetch(`/stories/search?${params}`);
  },

  /** Re-extract stories from an existing entry */
  async extract(entryId: string): Promise<ExtractedStory[]> {
    return apiFetch(`/stories/${entryId}/extract`, { method: "POST" });
  },

  /** Delete a Story Bank entry */
  async delete(entryId: string): Promise<void> {
    return apiFetch(`/stories/${entryId}`, { method: "DELETE" });
  },
};
