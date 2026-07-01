<template>
  <router-view />

  <van-tabbar route class="app-tabbar" :style="{ '--tab-index': activeTabIndex }">
    <div class="tabbar-slider" />
    <van-tabbar-item to="/home" icon="home-o" @click="setActiveTab(0)">{{ t('tab.home') }}</van-tabbar-item>
    <van-tabbar-item to="/reviews" icon="todo-list-o" @click="setActiveTab(1)">{{ t('tab.reviews') }}</van-tabbar-item>
    <van-tabbar-item to="/words" icon="notes-o" @click="setActiveTab(2)">{{ t('tab.words') }}</van-tabbar-item>
    <van-tabbar-item to="/me" icon="user-o" @click="setActiveTab(3)">{{ t('tab.me') }}</van-tabbar-item>
  </van-tabbar>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useSettingsStore } from '@/shared/model/settingsStore';

const route = useRoute();
const { t } = useSettingsStore();

const tabs = ['/home', '/reviews', '/words', '/me'];
const activeTabIndex = ref(getRouteTabIndex(route.path));

function getRouteTabIndex(pathname: string) {
  const index = tabs.findIndex((path) => pathname === path || pathname.startsWith(`${path}/`));
  return index >= 0 ? index : 0;
}

function setActiveTab(index: number) {
  activeTabIndex.value = index;
}

watch(
  () => route.path,
  (pathname) => {
    activeTabIndex.value = getRouteTabIndex(pathname);
  }
);
</script>
