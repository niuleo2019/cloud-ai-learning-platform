<template>
  <section class="explain-card">
    <button type="button" class="explain-head" @click="expanded = !expanded">
      <div>
        <p class="explain-eyebrow">{{ t('explain.eyebrow') }}</p>
        <h2>{{ t('explain.title') }}</h2>
        <p class="explain-author">{{ t('explain.author') }}</p>
      </div>
      <van-icon :name="expanded ? 'arrow-up' : 'arrow-down'" />
    </button>

    <div v-show="expanded" class="explain-body">
      <van-loading v-if="checking" size="20px">{{ t('explain.checking') }}</van-loading>

      <template v-else-if="explanation">
        <!-- eslint-disable-next-line vue/no-v-html -- sanitised with DOMPurify -->
        <div class="explain-markdown" v-html="html" />
        <p v-if="explanation.truncated" class="explain-warning">{{ t('explain.truncated') }}</p>
        <div class="explain-footer">
          <span>{{ t('explain.generatedBy') }} {{ explanation.model || 'Claude' }}</span>
          <van-button size="mini" round plain icon="replay" :loading="generating" @click="generate(true)">
            {{ t('explain.regenerate') }}
          </van-button>
        </div>
      </template>

      <template v-else>
        <p class="explain-intro">{{ t('explain.intro') }}</p>
        <van-button
          block
          round
          type="primary"
          icon="bulb-o"
          :loading="generating"
          :loading-text="t('explain.generating')"
          @click="generate(false)"
        >
          {{ t('explain.generate') }}
        </van-button>
        <p v-if="generating" class="explain-hint">{{ t('explain.wait') }}</p>
        <p v-if="error" class="explain-warning">{{ error }}</p>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import {
  generateWordExplanationApi,
  getWordExplanationApi,
  type WordExplanation
} from '@/features/words/api/explanationApi';
import { useSettingsStore } from '@/shared/model/settingsStore';

const props = defineProps<{ word: string }>();

const { t } = useSettingsStore();
const explanation = ref<WordExplanation | null>(null);
const checking = ref(false);
const generating = ref(false);
const error = ref('');
const expanded = ref(true);
let requestId = 0;

const html = computed(() => {
  if (!explanation.value) return '';
  const raw = marked.parse(explanation.value.content, { async: false, gfm: true, breaks: false }) as string;
  // Wide tables (the letter-by-letter table has 6 columns) scroll sideways instead of squashing.
  const withScroll = raw.replace(/<table>/g, '<div class="explain-table"><table>').replace(/<\/table>/g, '</table></div>');
  return DOMPurify.sanitize(withScroll);
});

// Show a cached explanation straight away; generating a new one is a deliberate tap because it calls the paid API.
watch(
  () => props.word,
  async (word) => {
    const current = ++requestId;
    explanation.value = null;
    error.value = '';
    if (!word.trim()) return;
    checking.value = true;
    try {
      const cached = await getWordExplanationApi(word.trim());
      if (current === requestId) explanation.value = cached;
    } catch {
      // Not fatal: the generate button is still offered.
    } finally {
      if (current === requestId) checking.value = false;
    }
  },
  { immediate: true }
);

async function generate(regenerate: boolean) {
  if (generating.value) return;
  const current = requestId;
  generating.value = true;
  error.value = '';
  try {
    const result = await generateWordExplanationApi(props.word.trim(), regenerate);
    if (current === requestId) explanation.value = result;
  } catch (failure) {
    const reason = (failure as { response?: { data?: { message?: string } } }).response?.data?.message;
    if (current === requestId) error.value = reason ? `${t('explain.failed')}（${reason}）` : t('explain.failed');
  } finally {
    generating.value = false;
  }
}
</script>

<style scoped>
.explain-card {
  margin-top: 14px;
  overflow: hidden;
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
  color: #1f2937;
}

.explain-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 14px 16px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
}

.explain-head h2 {
  margin: 2px 0 0;
  font-size: 18px;
  color: #0f172a;
}

.explain-author {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.explain-eyebrow {
  margin: 0;
  color: #2563eb;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.explain-body {
  display: grid;
  /* minmax(0, 1fr): a wide table scrolls inside its own box instead of widening the card */
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
  padding: 0 16px 16px;
}

.explain-intro,
.explain-hint {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.explain-warning {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fef3c7;
  color: #92400e;
  font-size: 13px;
  line-height: 1.5;
}

.explain-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: #94a3b8;
  font-size: 12px;
}

.explain-markdown {
  font-size: 15px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.explain-markdown :deep(h2) {
  margin: 18px 0 8px;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
  font-size: 17px;
  color: #1d4ed8;
}

.explain-markdown :deep(h2:first-child) {
  margin-top: 0;
  padding-top: 0;
  border-top: 0;
}

.explain-markdown :deep(h3) {
  margin: 12px 0 6px;
  font-size: 15px;
}

.explain-markdown :deep(p),
.explain-markdown :deep(ul),
.explain-markdown :deep(ol) {
  margin: 6px 0;
}

.explain-markdown :deep(ul),
.explain-markdown :deep(ol) {
  padding-left: 20px;
}

.explain-markdown :deep(code) {
  padding: 1px 5px;
  border-radius: 5px;
  background: #f1f5f9;
  font-size: 13px;
}

.explain-markdown :deep(.explain-table) {
  margin: 8px 0;
  overflow-x: auto;
}

.explain-markdown :deep(table) {
  min-width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  line-height: 1.5;
}

.explain-markdown :deep(th),
.explain-markdown :deep(td) {
  padding: 6px 8px;
  border: 1px solid #e2e8f0;
  text-align: left;
  vertical-align: top;
}

.explain-markdown :deep(th) {
  background: #f8fafc;
  white-space: nowrap;
}
</style>

<style>
.theme-dark .explain-card {
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.82);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
  color: #dbe4f0;
}

.theme-dark .explain-card .explain-author {
  color: #94a3b8;
}

.theme-dark .explain-card .explain-head h2 {
  color: #f8fafc;
}

.theme-dark .explain-card .explain-eyebrow,
.theme-dark .explain-card .explain-markdown h2 {
  color: #93c5fd;
}

.theme-dark .explain-card .explain-markdown h2 {
  border-top-color: rgba(148, 163, 184, 0.2);
}

.theme-dark .explain-card .explain-markdown th {
  background: rgba(148, 163, 184, 0.12);
}

.theme-dark .explain-card .explain-markdown th,
.theme-dark .explain-card .explain-markdown td {
  border-color: rgba(148, 163, 184, 0.24);
}

.theme-dark .explain-card .explain-markdown code {
  background: rgba(148, 163, 184, 0.16);
}

.theme-dark .explain-card .explain-warning {
  background: rgba(245, 158, 11, 0.16);
  color: #fcd34d;
}
</style>
