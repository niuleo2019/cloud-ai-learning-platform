import http, { request } from '@/shared/api/http';
import type { RememberLevel, Word } from '@/shared/types';

export function getTodayReviewsApi() {
  return request<Word[]>(http.get('/reviews/today'));
}

export function submitReviewApi(wordId: number, rememberLevel: RememberLevel) {
  return request(http.post(`/reviews/${wordId}/submit`, { rememberLevel }));
}
