import { createApp } from 'vue';
import Vant from 'vant';
import 'vant/lib/index.css';
import '@/shared/styles/global.css';

import App from './App.vue';
import router from '@/app/router';

createApp(App).use(router).use(Vant).mount('#app');
