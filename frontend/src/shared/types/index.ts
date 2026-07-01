export interface ApiResponse<T> {
  success: boolean;
  code?: number;
  data: T;
  message: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  created_at: string;
}

export interface AuthResult {
  user: User;
  token: string;
}

export interface Word {
  id: number;
  word: string;
  meaning: string;
  example: string;
  source: string;
  review_stage?: number;
  next_review_at?: string;
  remember_level?: 'known' | 'fuzzy' | 'unknown';
  created_at: string;
  updated_at: string;
}

export type RememberLevel = 'known' | 'fuzzy' | 'unknown';

export interface RootMemory {
  root: string;
  meaning: string;
  memory: string;
}

export interface MediaScene {
  title: string;
  context: string;
  line: string;
}
