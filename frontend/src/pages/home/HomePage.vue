<template>
  <main class="page mobile-page home-search-page" :style="homeStyle">
    <section class="home-lookup-hero">
      <div class="home-hero-topline">
        <span>{{ language === 'zh' ? '雅思词汇' : 'IELTS Vocabulary' }}</span>
        <van-icon name="fire-o" />
      </div>

      <div class="home-hero-visual" aria-hidden="true">
        <div class="aussie-lookup-icon">
          <span class="lookup-sun" />
          <span class="lookup-orbit orbit-one" />
          <span class="lookup-orbit orbit-two" />
          <span class="lookup-bridge" />
          <span class="lookup-bridge-deck" />
          <span class="lookup-lens" />
          <span class="lookup-handle" />
          <span class="lookup-wave wave-one" />
          <span class="lookup-wave wave-two" />
          <span class="lookup-word word-one">IELTS</span>
          <span class="lookup-word word-two">AUS</span>
          <span class="lookup-word word-three">EN</span>
        </div>
      </div>

      <div class="home-search-box">
        <van-field
          v-model="keyword"
          clearable
          border
          class="home-search-field"
          :placeholder="t('home.placeholder')"
          @keyup.enter="handleSearch"
        >
          <template #left-icon>
            <span class="search-prefix">
              <van-icon name="search" />
            </span>
          </template>
          <template #button>
            <van-button size="small" type="primary" icon="arrow" :disabled="!keyword.trim()" @click="handleSearch">
              {{ t('home.search') }}
            </van-button>
          </template>
        </van-field>

        <div v-if="suggestions.length > 0" class="home-suggestion-chips">
          <button
            v-for="word in suggestions"
            :key="word"
            type="button"
            class="home-suggestion-chip"
            @click="selectSuggestion(word)"
          >
            {{ word }}
          </button>
        </div>
      </div>
    </section>

    <section class="daily-sentence-card">
      <div class="sentence-header">
        <div>
          <p class="eyebrow">{{ language === 'zh' ? '每日一句' : 'Daily Sentence' }}</p>
          <h2>{{ t('home.daily') }}</h2>
        </div>
        <span class="sentence-date">{{ todayLabel }}</span>
      </div>
      <blockquote>{{ dailySentence.en }}</blockquote>
      <p>{{ language === 'zh' ? dailySentence.zh : dailySentence.enNote }}</p>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { showFailToast } from 'vant';
import { getWordSuggestions } from '@/features/words/model/wordSuggestions';
import { useSettingsStore } from '@/shared/model/settingsStore';

const router = useRouter();
const { language, t } = useSettingsStore();
const keyword = ref('');
const activeBackgroundIndex = ref(0);
let backgroundTimer: number | undefined;

const backgroundImages = ['/images/sydney-city-tram.jpg', '/images/sydney-harbour-bridge.jpg'];

const sentences = [
  {
    en: 'Small daily reviews turn difficult words into familiar tools.',
    enNote: 'A few minutes every day makes difficult vocabulary easier to use.',
    zh: '每天一点点复习，会把陌生单词变成你能随手使用的工具。'
  },
  {
    en: 'A word is easier to remember when you meet it in a real sentence.',
    enNote: 'Real sentences help meaning and sound stay together.',
    zh: '单词出现在真实句子里时，更容易被记住。'
  },
  {
    en: 'Vocabulary grows faster when meaning, sound, and context stay together.',
    enNote: 'Meaning, pronunciation and context make review more stable.',
    zh: '把意思、发音和语境放在一起，词汇增长会更稳定。'
  }
];

const suggestions = computed(() => getWordSuggestions(keyword.value, 4));

const homeStyle = computed(() => ({
  '--home-bg-image': `url("${backgroundImages[activeBackgroundIndex.value]}")`
}));

const dailySentence = computed(() => {
  const dayIndex = Math.floor(Date.now() / 86_400_000) % sentences.length;
  return sentences[dayIndex];
});

const todayLabel = computed(() =>
  new Intl.DateTimeFormat('en-AU', {
    month: 'short',
    day: 'numeric'
  }).format(new Date())
);

function selectSuggestion(word: string) {
  keyword.value = word;
  router.push({ path: '/lookup', query: { word } });
}

function handleSearch() {
  const word = keyword.value.trim();
  if (!word) {
    showFailToast(t('home.emptySearch'));
    return;
  }

  router.push({ path: '/lookup', query: { word } });
}

onMounted(() => {
  backgroundTimer = window.setInterval(() => {
    activeBackgroundIndex.value = (activeBackgroundIndex.value + 1) % backgroundImages.length;
  }, 6000);
});

onBeforeUnmount(() => {
  if (backgroundTimer) {
    window.clearInterval(backgroundTimer);
  }
});
</script>
