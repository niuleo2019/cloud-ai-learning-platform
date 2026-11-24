import { API_BASE_URL } from '@/shared/api/config';

export type Accent = 'gb' | 'us';

const ACCENT_KEY = 'vocab.pronunciation.accent';

export function getPreferredAccent(): Accent {
  try {
    return localStorage.getItem(ACCENT_KEY) === 'us' ? 'us' : 'gb';
  } catch {
    return 'gb';
  }
}

export function setPreferredAccent(accent: Accent) {
  try {
    localStorage.setItem(ACCENT_KEY, accent);
  } catch {
    // Storage unavailable: the choice only lasts for this page view.
  }
}

/** Longman (LDOCE) recording served by the backend from the local .mdd file. */
export function longmanAudioUrl(word: string, accent: Accent = getPreferredAccent()) {
  // v: bump when the server-side audio conversion changes, so browsers drop cached copies
  // (v2: libspeex decoder; v1 clips were distorted and are cached for a week).
  const params = new URLSearchParams({ word: word.trim().toLowerCase(), accent, v: '2' });
  return `${API_BASE_URL}/dictionary/audio?${params.toString()}`;
}

/** Longman has clips for headwords and some compounds, not for sentences. */
export function isSingleHeadword(text: string) {
  return /^[a-z][a-z'-]*( [a-z][a-z'-]*){0,2}$/i.test(text.trim());
}

// One <audio> element per word+accent, reused on every tap, so repeat plays start instantly
// and a preloaded word does not wait for the network at all.
const MAX_CACHED = 60;
const cache = new Map<string, HTMLAudioElement>();
const missing = new Set<string>();
let current: HTMLAudioElement | null = null;

function cacheKey(word: string, accent: Accent) {
  return `${accent}:${word.trim().toLowerCase()}`;
}

function audioFor(word: string, accent: Accent) {
  const key = cacheKey(word, accent);
  let audio = cache.get(key);
  if (audio) {
    cache.delete(key); // re-insert to keep most recently used last
  } else {
    audio = new Audio();
    audio.preload = 'auto';
    audio.addEventListener('error', () => {
      missing.add(key); // 404: no Longman clip, go straight to the fallback next time
      cache.delete(key);
    });
    audio.src = longmanAudioUrl(word, accent);
  }
  cache.set(key, audio);
  if (cache.size > MAX_CACHED) cache.delete(cache.keys().next().value as string);
  return audio;
}

/** Start downloading a word's pronunciation before the user taps the speaker button. */
export function preloadLongmanAudio(word: string, accent: Accent = getPreferredAccent()) {
  if (!isSingleHeadword(word) || missing.has(cacheKey(word, accent))) return;
  audioFor(word, accent);
}

/** Play the Longman pronunciation; resolves false when there is no clip so the caller can fall back. */
export function playLongmanAudio(word: string, accent: Accent = getPreferredAccent()): Promise<boolean> {
  if (!isSingleHeadword(word) || missing.has(cacheKey(word, accent))) return Promise.resolve(false);
  if (current && !current.paused) current.pause();
  const audio = audioFor(word, accent);
  current = audio;
  audio.currentTime = 0;
  return audio.play().then(
    () => true,
    (error: DOMException) => {
      // NotSupportedError = the clip could not be loaded (404); other errors (e.g. autoplay
      // blocked) are temporary, so only remember real misses.
      if (error?.name === 'NotSupportedError') missing.add(cacheKey(word, accent));
      return false;
    }
  );
}
