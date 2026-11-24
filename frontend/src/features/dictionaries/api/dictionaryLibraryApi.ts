import http, { request } from '@/shared/api/http';

export interface ImportedDictionary {
  id: number;
  title: string;
  mdx_file: string;
  mdd_files: string[];
  entry_count: number;
  enabled: boolean;
  sort_order: number;
}

export interface DictionaryLookupResult {
  id: number;
  title: string;
  found: boolean;
  entries?: string[];
  /** Signed path (relative to the API base) for the entry's css, images and audio. */
  resource_base?: string | null;
  error?: string;
}

export interface DictionaryLookup {
  word: string;
  enabled_count: number;
  results: DictionaryLookupResult[];
}

export interface ScanResult {
  added: ImportedDictionary[];
  errors: Array<{ folder: string; message: string }>;
}

export function getDictionariesApi() {
  return request<ImportedDictionary[]>(http.get('/dictionaries'));
}

export function importDictionaryApi(files: File[], onProgress?: (percent: number) => void) {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file, file.name));
  return request<ImportedDictionary[]>(
    http.post('/dictionaries', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 0, // a 1GB .mdd can take minutes over Wi-Fi
      onUploadProgress: (event) => {
        if (onProgress && event.total) onProgress(Math.round((event.loaded / event.total) * 100));
      }
    })
  );
}

export function scanDictionariesApi() {
  return request<ScanResult>(http.post('/dictionaries/scan', null, { timeout: 120_000 }));
}

export function updateDictionaryApi(id: number, payload: { title?: string; enabled?: boolean }) {
  return request<ImportedDictionary>(http.patch(`/dictionaries/${id}`, payload));
}

export function reorderDictionariesApi(ids: number[]) {
  return request<ImportedDictionary[]>(http.put('/dictionaries/order', { ids }));
}

export function deleteDictionaryApi(id: number) {
  return request<{ id: number }>(http.delete(`/dictionaries/${id}`));
}

export function lookupDictionariesApi(word: string) {
  return request<DictionaryLookup>(http.get('/dictionaries/lookup', { params: { word }, timeout: 20_000 }));
}

export interface RecordedExample {
  text: string;
  /** Sound file inside the dictionary's resources (played via resource_base). */
  audio: string;
}

export interface RecordedExamples {
  dictionary: string | null;
  resource_base: string | null;
  examples: RecordedExample[];
}

/** Example sentences that have a real recording in an imported dictionary (e.g. LDOCE). */
export function getRecordedExamplesApi(word: string) {
  return request<RecordedExamples>(http.get('/dictionaries/examples', { params: { word }, timeout: 20_000 }));
}
