<template>
  <main class="page mobile-page">
    <van-nav-bar :title="t('reviews.title')" />

    <section class="review-summary">
      <div>
        <p class="eyebrow">{{ language === 'zh' ? '复习队列' : 'Review Queue' }}</p>
        <h1>{{ totalCount }} {{ t('reviews.due') }}</h1>
      </div>
      <van-tag round type="primary">{{ t('reviews.ruleTag') }}</van-tag>
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

    <van-empty v-if="reviews.length === 0 && totalCount === 0" image="search" :description="t('reviews.empty')">
      <van-button round type="primary" to="/add-word">{{ t('reviews.addWord') }}</van-button>
    </van-empty>

    <van-empty v-else-if="reviews.length === 0 && totalCount > 0" image="success" :description="t('reviews.done')">
      <van-button round type="primary" to="/words">{{ t('reviews.viewLibrary') }}</van-button>
    </van-empty>

    <section v-else class="flip-card-wrapper" @click="flip">
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
import { computed, onMounted, ref } from 'vue';
import { showToast } from 'vant';
import { getTodayReviewsApi, submitReviewApi } from '@/features/reviews/api/reviewApi';
import { useSettingsStore } from '@/shared/model/settingsStore';
import type { RememberLevel, Word } from '@/shared/types';

const { language, t } = useSettingsStore();
const reviews = ref<Word[]>([]);
const loading = ref(false);
const flipped = ref(false);
const totalCount = ref(0);

const doneCount = computed(() => totalCount.value - reviews.value.length);
const progressPercent = computed(() =>
  totalCount.value === 0 ? 0 : Math.round((doneCount.value / totalCount.value) * 100)
);
const current = computed(() => reviews.value[0]);

function flip() {
  if (!flipped.value) flipped.value = true;
}

async function loadReviews() {
  reviews.value = await getTodayReviewsApi();
  totalCount.value = reviews.value.length;
}

async function submit(level: RememberLevel) {
  if (!current.value) return;

  loading.value = true;
  try {
    await submitReviewApi(current.value.id, level);
    reviews.value.shift();
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
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}
.flip-card-front {
  background: #fff;
}
.flip-card-back {
  background: #f8fffe;
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

.fade-up-enter-active {
  transition: all 0.3s ease;
}
.fade-up-enter-from {
  opacity: 0;
  transform: translateY(16px);
}
</style>
