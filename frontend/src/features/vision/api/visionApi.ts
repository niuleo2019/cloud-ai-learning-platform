import http, { request } from '@/shared/api/http';

export interface ExtractedVisionWord {
  word: string;
  count: number;
}

export interface VisionExtractionResult {
  filename?: string;
  text: string;
  words: ExtractedVisionWord[];
  total_candidates: number;
  preprocessing: string[];
  engine: string;
}

export function extractWordsFromImageApi(file: File) {
  const formData = new FormData();
  formData.append('image', file);

  return request<VisionExtractionResult>(
    http.post('/vision/extract-words', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 30000
    })
  );
}
