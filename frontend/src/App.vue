<template>
  <div v-if="isH5Mode" class="h5-app">
    <router-view />
  </div>

  <DeviceFrame v-else device="iPhone 17 Pro">
    <router-view />
  </DeviceFrame>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { Capacitor } from '@capacitor/core';
import DeviceFrame from '@/shared/ui/DeviceFrame.vue';
import { useSettingsStore } from '@/shared/model/settingsStore';

type DisplayMode = 'frame' | 'h5';

const route = useRoute();
const displayMode = ref<DisplayMode>('frame');
useSettingsStore();

function normaliseMode(mode: unknown): DisplayMode | null {
  const value = Array.isArray(mode) ? mode[0] : mode;
  if (value === 'h5' || value === 'frame') {
    return value;
  }
  return null;
}

function syncDisplayMode() {
  // Inside the Android app the real phone screen is used, so never draw the demo phone frame.
  if (Capacitor.isNativePlatform()) {
    displayMode.value = 'h5';
    return;
  }

  const modeFromQuery = normaliseMode(route.query.mode);

  if (modeFromQuery) {
    displayMode.value = modeFromQuery;
    localStorage.setItem('vocab-display-mode', modeFromQuery);
    return;
  }

  const storedMode = normaliseMode(localStorage.getItem('vocab-display-mode'));
  displayMode.value = storedMode || 'frame';
}

watch(() => route.fullPath, syncDisplayMode, { immediate: true });

const isH5Mode = computed(() => displayMode.value === 'h5');
</script>

<style scoped>
.h5-app {
  min-height: 100vh;
  background: #f4f7fb;
}

@media (min-width: 768px) {
  .h5-app {
    max-width: 520px;
    margin: 0 auto;
    box-shadow: 0 18px 60px rgba(15, 23, 42, 0.08);
  }

  .h5-app :deep(.van-tabbar) {
    left: 50%;
    width: 100%;
    max-width: 520px;
    transform: translateX(-50%);
  }
}
</style>
