<template>
  <main class="page mobile-page">
    <van-nav-bar :title="t('me.title')" />

    <section class="profile-card account-card">
      <div class="avatar">{{ userInitial }}</div>
      <div class="account-copy">
        <p class="eyebrow">{{ language === 'zh' ? '账户' : 'Account' }}</p>
        <h1>{{ user?.username || 'Learner' }}</h1>
        <p>{{ user?.email || '-' }}</p>
      </div>
      <van-button
        class="settings-icon-button"
        icon="setting-o"
        round
        type="primary"
        plain
        :aria-label="t('me.settings')"
        @click="router.push('/settings')"
      />
    </section>

    <section class="quick-actions">
      <van-cell :title="t('me.overview')" :label="t('me.overviewLabel')" icon="chart-trending-o" is-link to="/overview" />
      <van-cell :title="t('me.project')" :label="t('me.projectLabel')" icon="records-o" />
      <van-cell :title="t('me.method')" :label="t('me.methodLabel')" icon="clock-o" />
      <van-cell :title="t('me.currentAccount')" :label="user?.email || '-'" icon="user-o" />
    </section>

    <div class="form-actions">
      <van-button round block type="danger" plain @click="logout">{{ t('me.logout') }}</van-button>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { getMeApi } from '@/features/auth/api/authApi';
import { clearAuth, getUser } from '@/features/auth/model/authStore';
import { useSettingsStore } from '@/shared/model/settingsStore';
import type { User } from '@/shared/types';

const router = useRouter();
const { language, t } = useSettingsStore();
const user = ref<User | null>(getUser());

const userInitial = computed(() => user.value?.username?.slice(0, 1).toUpperCase() || 'V');

async function loadUser() {
  user.value = await getMeApi();
}

function logout() {
  clearAuth();
  router.push('/login');
}

onMounted(loadUser);
</script>
