import http, { request } from '@/shared/api/http';

export interface PdfRootPage {
  pdf_id: string;
  page_num: number;
  title: string;
  image_url: string;
  note?: string;
}

export interface PdfRootsResult {
  available: boolean;
  pages: PdfRootPage[];
}

export async function searchPdfRoots(word: string): Promise<PdfRootsResult> {
  return request<PdfRootsResult>(
    http.get('/pdf-roots/search', { params: { word }, timeout: 30000 })
  );
}
