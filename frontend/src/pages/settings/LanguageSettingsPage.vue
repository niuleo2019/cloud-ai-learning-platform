<template>
  <main class="page mobile-page settings-page">
    <van-nav-bar :title="t('language.title')" :left-text="t('common.back')" left-arrow @click-left="router.back()" />

    <section class="settings-hero">
      <p class="eyebrow">Language</p>
      <h1>{{ t('language.heading') }}</h1>
      <p>{{ t('language.description') }}</p>
    </section>

    <section class="language-switch-card">
      <div>
        <p class="eyebrow">{{ t('language.display') }}</p>
        <h2>{{ language === 'zh' ? '中文' : 'English' }}</h2>
      </div>

      <button class="language-segment" type="button" :data-active="language" @click="toggleLanguage">
        <span>{{ language === 'zh' ? '中' : 'ZH' }}</span>
        <span>EN</span>
        <i />
      </button>
    </section>
  </main>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useSettingsStore } from '@/shared/model/settingsStore';

const router = useRouter();
const { language, setLanguage, t } = useSettingsStore();

function toggleLanguage() {
  setLanguage(language.value === 'zh' ? 'en' : 'zh');
}
</script>
