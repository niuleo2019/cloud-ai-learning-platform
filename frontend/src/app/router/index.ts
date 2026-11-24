import { createRouter, createWebHistory } from 'vue-router';
import { getToken } from '@/features/auth/model/authStore';

function getDisplayModeQuery(query: Record<string, unknown>) {
  const mode = Array.isArray(query.mode) ? query.mode[0] : query.mode;
  if (mode === 'h5' || mode === 'frame') {
    return { mode };
  }
  return {};
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/home' },
    { path: '/login', component: () => import('@/pages/auth/LoginPage.vue'), meta: { public: true } },
    { path: '/register', component: () => import('@/pages/auth/RegisterPage.vue'), meta: { public: true } },
    {
      path: '/',
      component: () => import('@/app/layouts/MainLayout.vue'),
      children: [
        { path: 'home', component: () => import('@/pages/home/HomePage.vue') },
        { path: 'overview', component: () => import('@/pages/home/LearningOverviewPage.vue') },
        { path: 'lookup', component: () => import('@/pages/words/WordLookupPage.vue') },
        { path: 'vision', component: () => import('@/pages/vision/VisionExtractPage.vue') },
        { path: 'agent', component: () => import('@/pages/agent/AgentChatPage.vue') },
        { path: 'plan', component: () => import('@/pages/planner/StudyPlanPage.vue') },
        { path: 'listening', component: () => import('@/pages/listening/ListeningListPage.vue') },
        { path: 'listening/:id', component: () => import('@/pages/listening/ListeningPracticePage.vue') },
        { path: 'add-word', component: () => import('@/pages/words/AddWordPage.vue') },
        { path: 'words', component: () => import('@/pages/words/WordListPage.vue') },
        { path: 'reviews', component: () => import('@/pages/reviews/TodayReviewPage.vue') },
        { path: 'me', component: () => import('@/pages/me/MePage.vue') },
        { path: 'settings', component: () => import('@/pages/settings/SettingsPage.vue') },
        { path: 'settings/language', component: () => import('@/pages/settings/LanguageSettingsPage.vue') },
        { path: 'settings/dictionaries', component: () => import('@/pages/settings/DictionariesPage.vue') }
      ]
    }
  ]
});

router.beforeEach((to) => {
  const isPublicPage = Boolean(to.meta.public);
  const hasToken = Boolean(getToken());

  if (!isPublicPage && !hasToken) {
    return { path: '/login', query: getDisplayModeQuery(to.query) };
  }

  if (isPublicPage && hasToken) {
    return { path: '/home', query: getDisplayModeQuery(to.query) };
  }

  return true;
});

export default router;
