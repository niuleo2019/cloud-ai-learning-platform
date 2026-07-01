import axios from 'axios';
import { showFailToast } from 'vant';
import router from '@/app/router';
import { clearAuth, getToken } from '@/features/auth/model/authStore';
import { useSettingsStore } from '@/shared/model/settingsStore';
import type { ApiResponse } from '@/shared/types';

const http = axios.create({
  baseURL: '/api',
  timeout: 10000
});

http.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status;
    const businessMessage = error.response?.data?.message;
    const { t } = useSettingsStore();

    if (!error.response) {
      showFailToast(t('common.networkError'));
      return Promise.reject(error);
    }

    if (status === 401) {
      clearAuth();
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login');
      }
      showFailToast(businessMessage || t('common.loginExpired'));
      return Promise.reject(error);
    }

    if (status && status >= 500) {
      showFailToast(t('common.serverBusy'));
      return Promise.reject(error);
    }

    showFailToast(businessMessage || t('common.requestFailed'));
    return Promise.reject(error);
  }
);

export async function request<T>(promise: Promise<unknown>) {
  const response = (await promise) as ApiResponse<T>;
  return response.data;
}

export default http;
