import type { User } from '@/shared/types';

const TOKEN_KEY = 'vocab_token';
const USER_KEY = 'vocab_user';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuth(token: string, user: User) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getUser(): User | null {
  const rawUser = localStorage.getItem(USER_KEY);
  return rawUser ? JSON.parse(rawUser) : null;
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
