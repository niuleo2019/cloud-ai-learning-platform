<template>
  <main class="page mobile-page plan-page">
    <van-nav-bar :title="t('plan.title')" :left-text="t('common.back')" left-arrow @click-left="router.back()" />

    <section v-if="!loading && !plan" class="plan-card plan-hero">
      <p class="eyebrow">{{ t('plan.eyebrow') }}</p>
      <h1>{{ t('plan.heading') }}</h1>
      <p>{{ t('plan.description') }}</p>
    </section>

    <van-loading v-if="loading" class="plan-loading" vertical>{{ t('plan.loading') }}</van-loading>

    <!-- Today's plan -->
    <template v-else-if="plan">
      <section class="plan-card plan-summary">
        <div class="plan-summary-head">
          <strong>{{ t('plan.analysis') }}</strong>
          <span>{{ doneCount }} / {{ plan.tasks.length }} · {{ totalMinutes }} {{ t('plan.minutes') }}</span>
        </div>
        <p>{{ plan.summary }}</p>
        <van-progress :percentage="progress" :show-pivot="false" stroke-width="6" />
      </section>

      <section class="plan-card plan-tasks">
        <article v-for="task in plan.tasks" :key="task.id" class="plan-task" :class="{ done: isDone(task) }">
          <van-checkbox :model-value="isDone(task)" @update:model-value="toggle(task)" />
          <div class="plan-task-main" @click="openTask(task)">
            <div class="plan-task-head">
              <van-tag round :type="tagType(task)">{{ t(`plan.type.${task.type}`) }}</van-tag>
              <span>{{ task.minutes }} {{ t('plan.minutes') }}</span>
            </div>
            <strong>{{ task.title }}</strong>
            <p>{{ task.detail }}</p>
            <div v-if="task.words.length" class="plan-words">
              <button v-for="word in task.words" :key="word" type="button" @click.stop="router.push({ path: '/lookup', query: { word } })">
                {{ word }}
              </button>
            </div>
          </div>
          <van-icon name="arrow" class="plan-go" @click="openTask(task)" />
        </article>
      </section>

      <van-button block round plain type="primary" icon="replay" class="plan-again" @click="showForm = !showForm">
        {{ t('plan.regenerate') }}
      </van-button>
    </template>

    <!-- Generate -->
    <section v-if="!loading && (!plan || showForm)" class="plan-card plan-form">
      <strong>{{ t('plan.howLong') }}</strong>
      <SegmentedControl
        v-model="minutes"
        :options="MINUTE_OPTIONS.map((value) => ({ label: `${value} ${t('plan.minutes')}`, value }))"
      />
      <van-field v-model="focus" :placeholder="t('plan.focusPlaceholder')" maxlength="200" class="plan-focus" />
      <van-button
        block
        round
        type="primary"
        icon="guide-o"
        :loading="generating"
        :loading-text="t('plan.generating')"
        @click="generate"
      >
        {{ plan ? t('plan.regenerate') : t('plan.generate') }}
      </van-button>
      <p v-if="generating" class="plan-hint">{{ t('plan.wait') }}</p>
      <p v-if="error" class="plan-error">{{ error }}</p>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { getTodayPlanApi, makePlanApi, setPlanDoneApi, type PlanTask, type StudyPlan } from '@/features/planner/api/plannerApi';
import { useSettingsStore } from '@/shared/model/settingsStore';
import SegmentedControl from '@/shared/ui/SegmentedControl.vue';
import { hapticSuccess, hapticTap } from '@/shared/lib/haptics';

const MINUTE_OPTIONS = [15, 30, 45, 60];

const router = useRouter();
const { t } = useSettingsStore();
const plan = ref<StudyPlan | null>(null);
const loading = ref(true);
const generating = ref(false);
const showForm = ref(false);
const minutes = ref(30);
const focus = ref('');
const error = ref('');

const doneCount = computed(() => plan.value?.tasks.filter((task) => isDone(task)).length || 0);
const progress = computed(() => (plan.value?.tasks.length ? Math.round((doneCount.value / plan.value.tasks.length) * 100) : 0));
const totalMinutes = computed(() => plan.value?.tasks.reduce((sum, task) => sum + task.minutes, 0) || 0);

function isDone(task: PlanTask) {
  return plan.value?.done.includes(task.id) || false;
}

function tagType(task: PlanTask) {
  return task.type === 'review' ? 'success' : task.type === 'vocabulary' ? 'warning' : 'primary';
}

async function toggle(task: PlanTask) {
  if (!plan.value) return;
  const done = isDone(task) ? plan.value.done.filter((id) => id !== task.id) : [...plan.value.done, task.id];
  if (done.length === plan.value.tasks.length && done.length > plan.value.done.length) hapticSuccess();
  else hapticTap();
  plan.value = { ...plan.value, done };
  try {
    plan.value = await setPlanDoneApi(done);
  } catch {
    // keep the local tick; it is saved again on the next change
  }
}

function openTask(task: PlanTask) {
  if ((task.type === 'dictation' || task.type === 'retell') && task.material_id) {
    router.push({ path: `/listening/${task.material_id}`, query: { sentence: String(task.sentence_index ?? 0), mode: task.type } });
  } else if (task.type === 'review') {
    router.push('/reviews');
  } else if (task.words.length) {
    router.push({ path: '/lookup', query: { word: task.words[0] } });
  }
}

async function generate() {
  if (generating.value) return;
  generating.value = true;
  error.value = '';
  try {
    const result = await makePlanApi(minutes.value, focus.value);
    plan.value = result.plan;
    showForm.value = false;
  } catch (failure) {
    const reason = (failure as { response?: { data?: { message?: string } } }).response?.data?.message;
    error.value = reason ? `${t('plan.failed')}（${reason}）` : t('plan.failed');
  } finally {
    generating.value = false;
  }
}

onMounted(async () => {
  try {
    plan.value = await getTodayPlanApi();
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.plan-card {
  margin-top: 14px;
  padding: 16px;
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
  color: #334155;
}

.plan-hero h1 {
  margin: 4px 0 6px;
  font-size: 20px;
  color: #0f172a;
}

.plan-hero p,
.plan-summary p {
  margin: 0;
  line-height: 1.6;
}

.plan-loading {
  padding: 40px 0;
}

.plan-summary {
  display: grid;
  gap: 10px;
}

.plan-summary-head {
  display: flex;
  justify-content: space-between;
  color: #0f172a;
}

.plan-summary-head span {
  color: #64748b;
  font-size: 13px;
}

.plan-tasks {
  display: grid;
  gap: 4px;
  padding: 6px 12px;
}

.plan-task {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid #f1f5f9;
}

.plan-task:last-child {
  border-bottom: 0;
}

.plan-task.done .plan-task-main {
  opacity: 0.5;
}

.plan-task.done strong {
  text-decoration: line-through;
}

.plan-task-main {
  display: grid;
  flex: 1;
  gap: 4px;
  min-width: 0;
}

.plan-task-head {
  display: flex;
  justify-content: space-between;
  color: #64748b;
  font-size: 12px;
}

.plan-task-main strong {
  color: #0f172a;
  font-size: 15px;
}

.plan-task-main p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.55;
}

.plan-words {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.plan-words button {
  padding: 2px 10px;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
}

.plan-go {
  margin-top: 26px;
  color: #94a3b8;
}

.plan-again {
  margin-top: 14px;
}

.plan-form {
  display: grid;
  gap: 12px;
}

.plan-form strong {
  color: #0f172a;
}

.plan-minutes {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.plan-minutes button {
  padding: 8px 0;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  background: transparent;
  color: #334155;
  font-size: 13px;
}

.plan-minutes button.on {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 600;
}

.plan-focus {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.plan-hint,
.plan-error {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
}

.plan-hint {
  color: #64748b;
}

.plan-error {
  padding: 10px 12px;
  border-radius: 10px;
  background: #fef3c7;
  color: #92400e;
}
</style>

<style>
.theme-dark .plan-page .plan-card {
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.82);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
  color: #cbd5e1;
}

.theme-dark .plan-page .plan-hero h1,
.theme-dark .plan-page .plan-summary-head,
.theme-dark .plan-page .plan-task-main strong,
.theme-dark .plan-page .plan-form strong {
  color: #f8fafc;
}

.theme-dark .plan-page .plan-task-main p {
  color: #94a3b8;
}

.theme-dark .plan-page .plan-task {
  border-bottom-color: rgba(148, 163, 184, 0.14);
}

.theme-dark .plan-page .plan-words button {
  border-color: rgba(96, 165, 250, 0.4);
  background: rgba(37, 99, 235, 0.15);
  color: #bfdbfe;
}

.theme-dark .plan-page .plan-minutes button {
  border-color: rgba(148, 163, 184, 0.35);
  color: #cbd5e1;
}

.theme-dark .plan-page .plan-minutes button.on {
  border-color: #60a5fa;
  background: rgba(37, 99, 235, 0.2);
  color: #bfdbfe;
}

.theme-dark .plan-page .plan-focus {
  border-color: rgba(148, 163, 184, 0.3);
}

.theme-dark .plan-page .plan-error {
  background: rgba(245, 158, 11, 0.16);
  color: #fcd34d;
}
</style>
