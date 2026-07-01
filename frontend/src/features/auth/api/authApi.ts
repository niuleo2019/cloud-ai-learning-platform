import http, { request } from '@/shared/api/http';
import type { AuthResult, User } from '@/shared/types';

export function registerApi(payload: { username: string; email: string; password: string }) {
  return request<AuthResult>(http.post('/auth/register', payload));
}

export function loginApi(payload: { email: string; password: string }) {
  return request<AuthResult>(http.post('/auth/login', payload));
}

export function getMeApi() {
  return request<User>(http.get('/auth/me'));
}
