<template>
  <main class="page mobile-page settings-page">
    <van-nav-bar :title="t('settings.title')" :left-text="t('common.back')" left-arrow @click-left="router.back()" />

    <section class="quick-actions settings-list">
      <van-cell :title="t('settings.language')" :label="languageLabel" icon="chat-o" is-link to="/settings/language" />
      <van-cell
        :title="t('dictionaries.title')"
        :label="t('dictionaries.settingsLabel')"
        icon="bookmark-o"
        is-link
        to="/settings/dictionaries"
      />
      <van-cell
        v-if="isNative"
        :title="language === 'zh' ? '复习提醒' : 'Review reminders'"
        :label="language === 'zh' ? '按复习进度提醒，点通知直接开始复习' : 'Notifies you when words are due; tap to start reviewing'"
        icon="bell"
      >
        <template #right-icon>
          <van-switch :model-value="reminders" size="24px" @update:model-value="toggleReminders" />
        </template>
      </van-cell>
      <van-cell
        :title="language === 'zh' ? '按时间自动切换' : 'Automatic (by time of day)'"
        icon="clock-o"
      >
        <template #right-icon>
          <van-switch
            :model-value="themeMode === 'auto'"
            size="24px"
            @update:model-value="(on: boolean) => setThemeMode(on ? 'auto' : 'manual')"
          />
        </template>
      </van-cell>
      <van-cell
        :title="t('settings.theme')"
        :label="themeLabel"
        icon="brush-o"
      >
        <template #right-icon>
          <van-switch v-model="darkModeProxy" size="24px" />
        </template>
      </van-cell>
    </section>

  </main>
</template>

<script setup lang="ts">
import { Capacitor } from '@capacitor/core';
import { remindersEnabled, setRemindersEnabled } from '@/shared/lib/reviewReminders';
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useSettingsStore } from '@/shared/model/settingsStore';

// Review reminders only exist in the phone app (local notifications).
const isNative = Capacitor.isNativePlatform();
const reminders = ref(remindersEnabled());

function toggleReminders(on: boolean) {
  reminders.value = on;
  setRemindersEnabled(on);
}

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
