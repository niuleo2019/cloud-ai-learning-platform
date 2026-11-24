<template>
  <router-view />

  <Transition name="tab-buddy">
    <div v-if="showTabBuddy" class="tab-buddy">
      <WordBuddy mini />
    </div>
  </Transition>

  <van-tabbar
    :model-value="activeTabIndex"
    class="app-tabbar"
    :fixed="true"
    :border="false"
    :style="{ '--tab-count': tabs.length, '--tab-index': activeTabIndex }"
  >
    <span class="tabbar-slider" aria-hidden="true" />
    <van-tabbar-item icon="home-o" @click="openTab('/home')">{{ t('tab.home') }}</van-tabbar-item>
    <van-tabbar-item icon="todo-list-o" @click="openTab('/reviews')">{{ t('tab.reviews') }}</van-tabbar-item>
    <van-tabbar-item icon="notes-o" @click="openTab('/words')">{{ t('tab.words') }}</van-tabbar-item>
    <van-tabbar-item icon="music-o" @click="openTab('/listening')">{{ t('tab.listening') }}</van-tabbar-item>
  </van-tabbar>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { hapticSelect } from '@/shared/lib/haptics';
import { useSettingsStore } from '@/shared/model/settingsStore';
import WordBuddy from '@/shared/ui/WordBuddy.vue';

const route = useRoute();
const router = useRouter();
const { t } = useSettingsStore();

const tabs = ['/home', '/reviews', '/words', '/listening'];

// Pages pushed from a tab keep that tab selected, like iOS.
const PARENT_TAB: [string, number][] = [
  ['/lookup', 0],
  ['/vision', 0],
  ['/agent', 0],
  ['/plan', 0], // opened from Me, which sits under Home
  ['/add-word', 2],
  // "Me" left the tab bar for the home menu, so its pages sit under Home.
  ['/me', 0],
  ['/settings', 0],
  ['/overview', 0]
];

const activeTabIndex = computed(() => {
  const path = route.path;
  const own = tabs.findIndex((tab) => path === tab || path.startsWith(`${tab}/`));
  if (own >= 0) return own;
  return PARENT_TAB.find(([prefix]) => path === prefix || path.startsWith(`${prefix}/`))?.[1] ?? 0;
});

// Vant ignores taps on the tab that is already highlighted, but pages such as Me or the study plan
// highlight their parent tab, so route ourselves: tapping a tab always returns to its root page (like iOS).
function openTab(path: string) {
  hapticSelect();
  if (route.path !== path) router.push({ path, query: route.query.mode ? { mode: route.query.mode } : {} });
}

// A tiny buddy sits on top of the tab bar on these pages; tapping it opens the AI chat.
const showTabBuddy = computed(() => ['/reviews', '/words', '/listening'].includes(route.path));

// iOS large titles shrink into the bar once the page scrolls. Pages scroll the window on the phone
// and an inner element inside the desktop phone frame, so listen in the capture phase for both.
function onScroll(event: Event) {
  const target = event.target;
  const top = target instanceof Element ? target.scrollTop : window.scrollY;
  document.documentElement.classList.toggle('ios-scrolled', top > 24);
}

onMounted(() => document.addEventListener('scroll', onScroll, { capture: true, passive: true }));
onBeforeUnmount(() => document.removeEventListener('scroll', onScroll, { capture: true }));
watch(
  () => route.path,
  () => document.documentElement.classList.remove('ios-scrolled')
);
</script>

<style scoped>
.tab-buddy {
  position: fixed;
  z-index: 31;
  bottom: calc(10px + 62px + 2px + env(safe-area-inset-bottom));
  left: 50%;
  transform: translateX(-50%);
}

/* Inside the desktop phone frame the tab bar is absolutely positioned; follow it */
@media (min-width: 768px) {
  .app-device-screen .tab-buddy {
    position: absolute;
    bottom: calc(14px + 62px + 2px);
  }
}

/* Arriving from a page without it (e.g. Home -> Review): it drops in from above,
   squashes on landing and bounces a couple of times before settling. */
.tab-buddy-enter-active {
  transform-origin: 50% 100%;
  animation:
    tab-buddy-fall 1.1s linear both,
    tab-buddy-squash 1.1s ease-in-out both;
}

.tab-buddy-leave-active {
  transition:
    opacity 0.2s ease,
    scale 0.2s ease;
}

.tab-buddy-leave-to {
  opacity: 0;
  scale: 0.6;
}

/* Height over time, like a ball: speeds up falling, slows near the top of each hop */
@keyframes tab-buddy-fall {
  0% {
    opacity: 0;
    translate: 0 -150px;
    animation-timing-function: cubic-bezier(0.5, 0, 1, 0.6);
  }
  12% {
    opacity: 1;
  }
  40% {
    translate: 0 0;
    animation-timing-function: cubic-bezier(0, 0.4, 0.6, 1);
  }
  60% {
    translate: 0 -20px;
    animation-timing-function: cubic-bezier(0.4, 0, 1, 0.6);
  }
  77% {
    translate: 0 0;
    animation-timing-function: cubic-bezier(0, 0.4, 0.6, 1);
  }
  88% {
    translate: 0 -5px;
    animation-timing-function: cubic-bezier(0.4, 0, 1, 0.6);
  }
  97%,
  100% {
    opacity: 1;
    translate: 0 0;
  }
}

/* Shape: a little stretched while falling, a soft squash on each landing */
@keyframes tab-buddy-squash {
  0%,
  34% {
    scale: 0.95 1.06;
  }
  42% {
    scale: 1.14 0.88;
  }
  52% {
    scale: 0.98 1.03;
  }
  62%,
  74% {
    scale: 1 1;
  }
  79% {
    scale: 1.05 0.96;
  }
  86%,
  100% {
    scale: 1 1;
  }
}
</style>
