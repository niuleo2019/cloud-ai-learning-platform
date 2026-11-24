// Recently looked-up words, newest first. Kept on this device only (localStorage).
import { ref } from 'vue';

export interface SearchHistoryItem {
  word: string;
  meaning: string;
  at: number;
}

const STORAGE_KEY = 'vocab-search-history';
const MAX_ITEMS = 30;

function load(): SearchHistoryItem[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    return Array.isArray(parsed) ? parsed.filter((item) => item && typeof item.word === 'string') : [];
  } catch {
    return [];
  }
}

const history = ref<SearchHistoryItem[]>(load());

function save() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history.value));
  } catch {
    // storage unavailable (private mode); history just won't persist
  }
}

export function useSearchHistory() {
  return history;
}

export function recordSearch(word: string, meaning = '') {
  const clean = word.trim();
  if (!clean) return;
  const key = clean.toLowerCase();
  history.value = [
    { word: clean, meaning: meaning.trim(), at: Date.now() },
    ...history.value.filter((item) => item.word.toLowerCase() !== key)
  ].slice(0, MAX_ITEMS);
  save();
}

/** True once this device has ever saved a history (even an empty, cleared one). */
export function hasStoredHistory() {
  try {
    return localStorage.getItem(STORAGE_KEY) !== null;
  } catch {
    return true;
  }
}

/** First run only: start the list from words already saved in the library, newest first. */
export function seedSearchHistory(words: { word: string; meaning: string; created_at: string }[]) {
  if (hasStoredHistory() || history.value.length) return;
  history.value = words
    .map((item) => ({ word: item.word.trim(), meaning: item.meaning.trim(), at: Date.parse(item.created_at) || 0 }))
    .sort((a, b) => b.at - a.at)
    .filter((item, index, all) => item.word && all.findIndex((other) => other.word.toLowerCase() === item.word.toLowerCase()) === index)
    .slice(0, MAX_ITEMS);
  save();
}

export function removeSearch(word: string) {
  const key = word.toLowerCase();
  history.value = history.value.filter((item) => item.word.toLowerCase() !== key);
  save();
}

export function clearSearchHistory() {
  history.value = [];
  save();
}
