import http, { request } from '@/shared/api/http';

export interface WordExplanation {
  word: string;
  content: string;
  model?: string | null;
  truncated?: boolean;
  cached?: boolean;
  updated_at?: string;
}

/** Cached explanation only (never calls the AI). The API returns an empty object when there is none. */
export async function getWordExplanationApi(word: string) {
  const data = await request<WordExplanation | Record<string, never> | null>(
    http.get(`/explanations/${encodeURIComponent(word)}`)
  );
  return data && 'content' in data && data.content ? (data as WordExplanation) : null;
}

/** Generate with the AI (30–90 s) unless already cached; `regenerate` replaces the cached one. */
export function generateWordExplanationApi(word: string, regenerate = false) {
  return request<WordExplanation>(
    http.post(`/explanations/${encodeURIComponent(word)}`, null, {
      params: { regenerate },
      timeout: 180_000
    })
  );
}
