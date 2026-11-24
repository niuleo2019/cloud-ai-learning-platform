// In the browser the app calls the same origin ("/api", proxied by Vite or Nginx).
// In the Android app there is no same-origin backend, so the build sets VITE_API_BASE_URL,
// e.g. http://192.168.1.110:5173/api (see .env.android.example).
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || '/api';

const API_ORIGIN = API_BASE_URL.replace(/\/api\/?$/, '');

/** Turn a backend path such as "/api/pdf-root-images/x.png" into a full URL when needed. */
export function resolveApiAssetUrl(url: string): string {
  if (!url || /^https?:\/\//i.test(url) || !url.startsWith('/')) return url;
  return `${API_ORIGIN}${url}`;
}
