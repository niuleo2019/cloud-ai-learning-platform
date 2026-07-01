import http, { request } from '@/shared/api/http';
import type { Word } from '@/shared/types';

export interface WordPayload {
  word: string;
  meaning: string;
  example?: string;
  source?: string;
}

export function getWordsApi() {
  return request<Word[]>(http.get('/words'));
}

export function addWordApi(payload: WordPayload) {
  return request<Word>(http.post('/words', payload));
}

export function updateWordApi(id: number, payload: WordPayload) {
  return request<Word>(http.put(`/words/${id}`, payload));
}

export function deleteWordApi(id: number) {
  return request<{ id: number }>(http.delete(`/words/${id}`));
}
