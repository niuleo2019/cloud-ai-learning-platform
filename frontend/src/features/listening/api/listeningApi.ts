import http, { request } from '@/shared/api/http';

export type ListeningStatus = 'processing' | 'ready' | 'failed';

export interface ListeningSentence {
  index: number;
  start: number;
  end: number;
  text: string;
  edited?: boolean;
}

export interface ListeningMaterialSummary {
  id: number;
  title: string;
  original_filename?: string;
  status: ListeningStatus;
  error_message?: string | null;
  duration_seconds?: number | null;
  sentence_count?: number | null;
  created_at: string;
}

export interface ListeningMaterial extends ListeningMaterialSummary {
  sentences: ListeningSentence[] | null;
}

export function getListeningMaterialsApi() {
  return request<ListeningMaterialSummary[]>(http.get('/listening/materials'));
}

export function getListeningMaterialApi(id: number) {
  return request<ListeningMaterial>(http.get(`/listening/materials/${id}`));
}

export function uploadListeningMaterialApi(file: File, title: string, onProgress?: (percent: number) => void) {
  const formData = new FormData();
  formData.append('audio', file);
  formData.append('title', title);
  return request<ListeningMaterialSummary>(
    http.post('/listening/materials', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 5 * 60_000,
      onUploadProgress: (event) => {
        if (onProgress && event.total) onProgress(Math.round((event.loaded / event.total) * 100));
      }
    })
  );
}

export function deleteListeningMaterialApi(id: number) {
  return request<{ id: number }>(http.delete(`/listening/materials/${id}`));
}

export function updateListeningSentenceApi(id: number, index: number, text: string) {
  return request<ListeningSentence>(http.put(`/listening/materials/${id}/sentences/${index}`, { text }));
}

/** The audio needs the login token, so it is fetched as a blob and played from an object URL. */
export async function fetchListeningAudioUrl(id: number) {
  const blob = (await http.get(`/listening/materials/${id}/audio`, {
    responseType: 'blob',
    timeout: 5 * 60_000
  })) as unknown as Blob;
  return URL.createObjectURL(blob);
}

export function recogniseRetellApi(recording: Blob, filename: string) {
  const formData = new FormData();
  formData.append('audio', recording, filename);
  return request<{ text: string }>(
    http.post('/listening/retell', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60_000
    })
  );
}
