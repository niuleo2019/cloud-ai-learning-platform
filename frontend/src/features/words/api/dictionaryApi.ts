import http, { request } from '@/shared/api/http';

export interface OfflineDictionaryResult {
  found: boolean;
  word: string;
  text?: string;
  html?: string;
  audio?: string;
  source?: string;
}

export function lookupOfflineDictionaryApi(word: string) {
  return request<OfflineDictionaryResult>(
    http.get('/dictionary/lookup', {
      params: { word }
    })
  );
}
