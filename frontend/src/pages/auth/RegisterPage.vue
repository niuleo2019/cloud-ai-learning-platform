<template>
  <main class="auth-page auth-shell">
    <section class="auth-brand">
      <van-tag round type="primary">Start Learning</van-tag>
      <h1>{{ t('auth.registerTitle') }}</h1>
      <p>{{ t('auth.registerSubtitle') }}</p>
    </section>

    <section class="form-panel">
      <van-form @submit="handleRegister">
        <van-cell-group inset>
          <van-field
            v-model="form.username"
            name="username"
            :label="t('auth.username')"
            :placeholder="t('auth.usernamePlaceholder')"
            :rules="[{ required: true, message: t('auth.requiredUsername') }]"
          />
          <van-field
            v-model="form.email"
            name="email"
            :label="t('auth.email')"
            :placeholder="t('auth.emailPlaceholder')"
            :rules="[{ required: true, message: t('auth.requiredEmail') }]"
          />
          <van-field
            v-model="form.password"
            type="password"
            name="password"
            :label="t('auth.password')"
            :placeholder="t('auth.passwordPlaceholder')"
            :rules="[{ required: true, message: t('auth.requiredPassword') }]"
          />
        </van-cell-group>

        <div class="form-actions">
          <van-button round block type="primary" native-type="submit" :loading="loading">{{ t('auth.register') }}</van-button>
          <van-button round block plain type="primary" to="/login">{{ t('auth.registerLink') }}</van-button>
        </div>
      </van-form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { showToast } from 'vant';
import { registerApi } from '@/features/auth/api/authApi';
import { setAuth } from '@/features/auth/model/authStore';
import { useSettingsStore } from '@/shared/model/settingsStore';

const router = useRouter();
const { t } = useSettingsStore();
const loading = ref(false);

const form = reactive({
  username: '',
  email: '',
  password: ''
});

async function handleRegister() {
  loading.value = true;
  try {
    const result = await registerApi(form);
    setAuth(result.token, result.user);
    showToast(t('auth.registerSuccess'));
    router.push('/home');
  } finally {
    loading.value = false;
  }
}
</script>
