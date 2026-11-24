import http, { request } from '@/shared/api/http';

export type PlanTaskType = 'review' | 'dictation' | 'retell' | 'vocabulary';

export interface PlanTask {
  id: string;
  type: PlanTaskType;
  title: string;
  detail: string;
  minutes: number;
  material_id: number | null;
  sentence_index: number | null;
  words: string[];
}

export interface StudyPlan {
  plan_date: string;
  summary: string;
  tasks: PlanTask[];
  done: string[];
  model?: string | null;
}

export interface PracticeAttempt {
  material_id: number;
  sentence_index: number;
  mode: 'dictation' | 'retell';
  score: number;
  expected_text: string;
  attempt_text: string;
  missed: string[];
  wrong: Array<{ expected: string; actual: string }>;
}

/** The learner's local date (plans are per day in their time zone, not the server's). */
export function localDate() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

export function recordPracticeAttemptApi(attempt: PracticeAttempt) {
  return request<{ recorded: boolean }>(http.post('/planner/attempts', attempt));
}

export async function getTodayPlanApi() {
  const plan = await request<StudyPlan | Record<string, never> | null>(http.get('/planner/today', { params: { date: localDate() } }));
  return plan && 'tasks' in plan ? (plan as StudyPlan) : null;
}

export function makePlanApi(minutes: number, focus: string) {
  return request<{ plan: StudyPlan; tool_calls: Array<{ name: string; ok: boolean }> }>(
    http.post('/planner/plan', { date: localDate(), minutes, focus }, { timeout: 180_000 })
  );
}

export function setPlanDoneApi(done: string[]) {
  return request<StudyPlan>(http.put('/planner/today/done', { date: localDate(), done }));
}
