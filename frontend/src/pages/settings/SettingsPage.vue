<template>
  <main class="page mobile-page settings-page">
    <van-nav-bar :title="t('settings.title')" :left-text="t('common.back')" left-arrow @click-left="router.back()" />

    <section class="settings-hero">
      <p class="eyebrow">{{ t('settings.eyebrow') }}</p>
      <h1>{{ t('settings.heading') }}</h1>
      <p>{{ t('settings.description') }}</p>
    </section>

    <section class="quick-actions settings-list">
      <van-cell :title="t('settings.language')" :label="languageLabel" icon="chat-o" is-link to="/settings/language" />
      <van-cell
        :title="t('settings.theme')"
        :label="themeLabel"
        icon="brush-o"
      >
        <template #right-icon>
          <van-switch v-model="darkModeProxy" size="24px" active-color="#60a5fa" inactive-color="#cbd5e1" />
        </template>
      </van-cell>
    </section>

    <section class="theme-preview-card">
      <div>
        <p class="eyebrow">{{ t('settings.previewEyebrow') }}</p>
        <h2>{{ darkMode ? t('settings.darkOn') : t('settings.lightOn') }}</h2>
        <p>{{ darkMode ? t('settings.darkDescription') : t('settings.lightDescription') }}</p>
        <van-button class="theme-mode-button" round size="small" plain type="primary" @click="setThemeMode('auto')">
          {{ language === 'zh' ? '恢复自动跟随时间' : 'Use automatic schedule' }}
        </van-button>
      </div>
      <van-icon :name="darkMode ? 'moon-o' : 'sunny-o'" />
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useSettingsStore } from '@/shared/model/settingsStore';

const router = useRouter();
const { language, darkMode, themeMode, setDarkMode, setThemeMode, t } = useSettingsStore();

const languageLabel = computed(() => (language.value === 'zh' ? '中文' : 'English'));
const themeLabel = computed(() => {
  if (themeMode.value === 'manual') {
    if (language.value === 'zh') {
      return darkMode.value ? '手动深色模式' : '手动浅色模式';
    }
    return darkMode.value ? 'Manual dark mode' : 'Manual light mode';
  }

  return language.value === 'zh' ? '自动：夜晚深色，白天浅色' : 'Auto: dark at night, light during the day';
});

const darkModeProxy = computed({
  get: () => darkMode.value,
  set: (value: boolean) => setDarkMode(value)
});
</script>
