<template>
  <main class="page mobile-page">
    <van-nav-bar :title="t('reviews.title')" />

    <section class="review-summary">
      <div>
        <p class="eyebrow">{{ language === 'zh' ? '复习队列' : 'Review Queue' }}</p>
        <h1>{{ totalCount }} {{ t('reviews.due') }}</h1>
      </div>
    </section>

    <div v-if="totalCount > 0" class="review-progress">
      <van-progress
        :percentage="progressPercent"
        stroke-width="6"
        :show-pivot="false"
        color="var(--van-primary-color)"
        track-color="#f0f0f0"
      />
      <span class="review-progress-label">{{ doneCount }} / {{ totalCount }}</span>
    </div>

    <van-empty v-if="loaded && reviews.length === 0 && totalCount === 0" image="search" :description="t('reviews.empty')">
      <van-button round type="primary" to="/add-word">{{ t('reviews.addWord') }}</van-button>
    </van-empty>

    <van-empty v-else-if="loaded && reviews.length === 0 && totalCount > 0" image="success" :description="t('reviews.done')">
      <van-button round type="primary" to="/words">{{ t('reviews.viewLibrary') }}</van-button>
    </van-empty>

    <!-- Only when there is a card to show (nothing renders while today's reviews are still loading) -->
    <section v-else-if="current" class="flip-card-wrapper" @click="flip">
      <div class="flip-card" :class="{ flipped }">
        <div class="flip-card-face flip-card-front">
          <van-tag plain type="primary" class="stage-tag">{{ t('reviews.stage') }} {{ current.review_stage ?? 0 }}</van-tag>
          <h2 class="card-word">{{ current.word }}</h2>
          <p class="flip-hint">{{ t('reviews.flip') }}</p>
        </div>

        <div class="flip-card-face flip-card-back">
          <van-tag plain type="primary" class="stage-tag">{{ t('reviews.stage') }} {{ current.review_stage ?? 0 }}</van-tag>
          <h2 class="card-word">{{ current.word }}</h2>
          <p class="card-meaning">{{ current.meaning }}</p>
          <blockquote v-if="current.example" class="card-example">{{ current.example }}</blockquote>
          <div v-if="current.source" class="card-source">
            <span>{{ t('reviews.source') }}</span>
            <strong>{{ current.source }}</strong>
          </div>
        </div>
      </div>
    </section>

    <transition name="fade-up">
      <section v-if="reviews.length > 0 && flipped" class="review-actions">
        <van-button round block type="success" :loading="loading" @click.stop="submit('known')">
          {{ t('reviews.known') }}
        </van-button>
        <van-button round block type="warning" :loading="loading" @click.stop="submit('fuzzy')">
          {{ t('reviews.fuzzy') }}
        </van-button>
        <van-button round block type="danger" :loading="loading" @click.stop="submit('unknown')">
          {{ t('reviews.unknown') }}
        </van-button>
      </section>
    </transition>

    <p v-if="reviews.length > 0 && !flipped" class="flip-prompt">{{ t('reviews.prompt') }}</p>
  </main>
</template>

<script setup lang="ts">
import { syncReviewReminders } from '@/shared/lib/reviewReminders';
import { hapticSuccess, hapticTap } from '@/shared/lib/haptics';
import { computed, onMounted, ref } from 'vue';
import { showToast } from 'vant';
import { getTodayReviewsApi, submitReviewApi } from '@/features/reviews/api/reviewApi';
import { useSettingsStore } from '@/shared/model/settingsStore';
import type { RememberLevel, Word } from '@/shared/types';

const { language, t } = useSettingsStore();
const reviews = ref<Word[]>([]);
const loading = ref(false);
// Don't flash the empty-state picture before today's reviews have arrived.
const loaded = ref(false);
const flipped = ref(false);
const totalCount = ref(0);

const doneCount = computed(() => totalCount.value - reviews.value.length);
const progressPercent = computed(() =>
  totalCount.value === 0 ? 0 : Math.round((doneCount.value / totalCount.value) * 100)
);
const current = computed(() => reviews.value[0]);

function flip() {
  if (!flipped.value) hapticTap();
  if (!flipped.value) flipped.value = true;
}

async function loadReviews() {
  try {
    reviews.value = await getTodayReviewsApi();
    totalCount.value = reviews.value.length;
  } finally {
    loaded.value = true;
  }
}

async function submit(level: RememberLevel) {
  if (!current.value) return;
  if (level === 'known') hapticSuccess();
  else hapticTap();

  loading.value = true;
  try {
    await submitReviewApi(current.value.id, level);
    reviews.value.shift();
    syncReviewReminders(); // the next due time just moved
    flipped.value = false;
    showToast(t('reviews.saved'));
  } finally {
    loading.value = false;
  }
}

onMounted(loadReviews);
</script>

<style scoped>
.review-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px 12px;
}
.review-progress-label {
  font-size: 12px;
  color: var(--van-gray-6);
  white-space: nowrap;
}

.flip-card-wrapper {
  perspective: 1000px;
  padding: 16px;
  cursor: pointer;
}
.flip-card {
  position: relative;
  width: 100%;
  min-height: 280px;
  transform-style: preserve-3d;
  transition: transform 0.55s cubic-bezier(0.4, 0, 0.2, 1);
}
.flip-card.flipped {
  transform: rotateY(180deg);
}
.flip-card-face {
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}
.flip-card-front {
  background:
    radial-gradient(circle at 18% 12%, rgba(96, 165, 250, 0.14), transparent 36%),
    #ffffff;
}
.flip-card-back {
  background:
    radial-gradient(circle at 18% 12%, rgba(34, 197, 94, 0.12), transparent 38%),
    #f8fffe;
  transform: rotateY(180deg);
  align-items: flex-start;
  justify-content: flex-start;
  padding: 28px 24px;
}

.stage-tag {
  align-self: flex-start;
}
.card-word {
  font-size: 32px;
  font-weight: 700;
  text-align: center;
  width: 100%;
  word-break: break-word;
}
.flip-card-back .card-word {
  font-size: 24px;
  text-align: left;
}
.flip-hint {
  font-size: 13px;
  color: var(--van-gray-5);
}
.card-meaning {
  font-size: 16px;
  line-height: 1.6;
  color: var(--van-text-color);
}
.card-example {
  font-size: 14px;
  color: var(--van-gray-6);
  border-left: 3px solid var(--van-primary-color);
  padding-left: 12px;
  margin: 0;
  font-style: italic;
  line-height: 1.6;
}
.card-source {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--van-gray-6);
}

.review-actions {
  padding: 8px 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.flip-prompt {
  text-align: center;
  font-size: 13px;
  color: var(--van-gray-5);
  padding: 8px 0 24px;
}

:global(.theme-dark) .review-progress-label {
  color: #cbd5e1;
}

:global(.theme-dark) .review-progress :deep(.van-progress) {
  background: rgba(30, 41, 59, 0.82) !important;
}

:global(.theme-dark) .review-summary {
  border-color: rgba(96, 165, 250, 0.22);
  background:
    radial-gradient(circle at 88% 8%, rgba(37, 99, 235, 0.3), transparent 34%),
    linear-gradient(135deg, rgba(15, 23, 42, 0.94), rgba(30, 41, 59, 0.82));
}

:global(.theme-dark) .review-summary .eyebrow {
  color: #93c5fd;
}

:global(.theme-dark) .flip-card-face {
  border-color: rgba(147, 197, 253, 0.22);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.08),
    0 18px 42px rgba(0, 0, 0, 0.34);
}

:global(.theme-dark) .flip-card-front {
  background:
    radial-gradient(circle at 18% 12%, rgba(96, 165, 250, 0.24), transparent 38%),
    linear-gradient(145deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.88));
}

:global(.theme-dark) .flip-card-back {
  background:
    radial-gradient(circle at 86% 12%, rgba(34, 197, 94, 0.18), transparent 34%),
    linear-gradient(145deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.9));
}

:global(.theme-dark) .card-word {
  color: #f8fafc;
  text-shadow: 0 12px 34px rgba(96, 165, 250, 0.24);
}

:global(.theme-dark) .flip-hint,
:global(.theme-dark) .flip-prompt,
:global(.theme-dark) .card-example,
:global(.theme-dark) .card-source {
  color: #cbd5e1;
}

:global(.theme-dark) .card-meaning {
  color: #e5edf7;
}

:global(.theme-dark) .card-example {
  border-left-color: #60a5fa;
}

:global(.theme-dark) .stage-tag {
  color: #bfdbfe;
  border-color: rgba(96, 165, 250, 0.7);
  background: rgba(37, 99, 235, 0.14);
}

.fade-up-enter-active {
  transition: all 0.3s ease;
}
.fade-up-enter-from {
  opacity: 0;
  transform: translateY(16px);
}
</style>
