import http, { request } from '@/shared/api/http';

export interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface AgentToolCall {
  name: string;
  input: Record<string, unknown>;
  ok: boolean;
  error?: string;
}

export interface AgentReply {
  reply: string;
  tool_calls: AgentToolCall[];
  usage: { input_tokens: number; output_tokens: number; cache_read_input_tokens: number };
}

export function chatWithAgentApi(message: string, history: ChatTurn[]) {
  return request<AgentReply>(
    // The agent may call several tools before answering, so allow more time than normal requests.
    http.post('/agent/chat', { message, history: history.slice(-20) }, { timeout: 90000 })
  );
}
