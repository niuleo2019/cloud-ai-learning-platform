<template>
  <main class="page mobile-page">
    <van-nav-bar :title="t('overview.title')" :left-text="t('common.back')" left-arrow @click-left="router.back()" />

    <section class="home-hero">
      <div>
        <p class="eyebrow">Today</p>
        <h1 class="home-title">{{ t('overview.heading') }}</h1>
        <p class="home-copy">{{ t('overview.description') }}</p>
      </div>
      <van-button round type="primary" icon="plus" to="/add-word">{{ t('overview.add') }}</van-button>
    </section>

    <section class="metric-grid">
      <div class="metric-panel primary">
        <span class="metric-label">{{ t('overview.today') }}</span>
        <strong>{{ reviewCount }}</strong>
        <span class="metric-unit">{{ t('overview.unit') }}</span>
      </div>
      <div class="metric-panel">
        <span class="metric-label">{{ t('overview.total') }}</span>
        <strong>{{ wordCount }}</strong>
        <span class="metric-unit">{{ t('overview.unit') }}</span>
      </div>
    </section>

    <section class="quick-actions">
      <van-cell :title="t('overview.startReview')" :label="t('overview.startReviewLabel')" icon="todo-list-o" is-link to="/reviews" />
      <van-cell :title="t('overview.viewLibrary')" :label="t('overview.viewLibraryLabel')" icon="notes-o" is-link to="/words" />
      <van-cell :title="t('overview.addWord')" :label="t('overview.addWordLabel')" icon="plus" is-link to="/add-word" />
    </section>

    <section class="learning-card">
      <div class="section-heading">
        <h2>{{ t('overview.rules') }}</h2>
        <span>{{ t('overview.mvp') }}</span>
      </div>
      <div class="rule-list">
        <div class="rule-item">
          <van-tag type="success" plain>{{ t('overview.known') }}</van-tag>
          <p>{{ t('overview.knownRule') }}</p>
        </div>
        <div class="rule-item">
          <van-tag type="warning" plain>{{ t('overview.fuzzy') }}</van-tag>
          <p>{{ t('overview.fuzzyRule') }}</p>
        </div>
        <div class="rule-item">
          <van-tag type="danger" plain>{{ t('overview.unknown') }}</van-tag>
          <p>{{ t('overview.unknownRule') }}</p>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { showFailToast } from 'vant';
import { getTodayReviewsApi } from '@/features/reviews/api/reviewApi';
import { getWordsApi } from '@/features/words/api/wordApi';
import { useSettingsStore } from '@/shared/model/settingsStore';

const router = useRouter();
const { t } = useSettingsStore();
const reviewCount = ref(0);
const wordCount = ref(0);

onMounted(async () => {
  try {
    const [reviews, words] = await Promise.all([getTodayReviewsApi(), getWordsApi()]);
    reviewCount.value = reviews.length;
    wordCount.value = words.length;
  } catch {
    showFailToast(t('overview.loadError'));
  }
});
</script>
