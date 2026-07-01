<template>
  <main class="auth-page auth-shell">
    <section class="auth-brand">
      <van-tag round type="primary">Vocab MVP</van-tag>
      <h1>{{ t('auth.loginTitle') }}</h1>
      <p>{{ t('auth.loginSubtitle') }}</p>
    </section>

    <section class="form-panel">
      <van-form @submit="handleLogin">
        <van-cell-group inset>
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
          <van-button round block type="primary" native-type="submit" :loading="loading">{{ t('auth.login') }}</van-button>
          <van-button round block plain type="primary" to="/register">{{ t('auth.loginLink') }}</van-button>
        </div>
      </van-form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { showToast } from 'vant';
import { loginApi } from '@/features/auth/api/authApi';
import { setAuth } from '@/features/auth/model/authStore';
import { useSettingsStore } from '@/shared/model/settingsStore';

const router = useRouter();
const { t } = useSettingsStore();
const loading = ref(false);

const form = reactive({
  email: 'test@example.com',
  password: '123456'
});

async function handleLogin() {
  loading.value = true;
  try {
    const result = await loginApi(form);
    setAuth(result.token, result.user);
    showToast(t('auth.loginSuccess'));
    router.push('/home');
  } finally {
    loading.value = false;
  }
}
</script>
