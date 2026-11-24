<template>
  <main class="page mobile-page lookup-detail-page">
    <van-nav-bar :title="t('lookup.title')" :left-text="t('common.back')" left-arrow @click-left="goBack" />

    <section class="lookup-search-card autocomplete-host">
      <van-field v-model="keyword" :placeholder="t('lookup.input')" @keyup.enter="loadWord()">
        <template #right-icon>
          <button
            v-if="keyword"
            type="button"
            class="lookup-clear-button"
            :aria-label="t('lookup.clearSearch')"
            @click="clearLookup"
          >
            <van-icon name="clear" aria-hidden="true" />
          </button>
        </template>
        <template #button>
          <van-button size="small" type="primary" :loading="loading" :disabled="!keyword.trim()" @click="loadWord()">
            {{ t('home.search') }}
          </van-button>
        </template>
      </van-field>

      <div v-if="suggestions.length > 0" class="word-suggestion-list compact">
        <button
          v-for="word in suggestions"
          :key="word"
          type="button"
          class="word-suggestion-item"
          @click="selectSuggestion(word)"
        >
          <van-icon name="search" />
          <span>{{ word }}</span>
        </button>
      </div>
    </section>

    <van-loading v-if="loading" class="lookup-loading" type="spinner">{{ t('lookup.loading') }}</van-loading>

    <template v-else-if="result">
      <section class="lookup-word-card">
        <p class="eyebrow">Vocabulary</p>
        <div class="lookup-title-row">
          <div>
            <h1>{{ result.word }}</h1>
            <p class="phonetic">{{ result.phonetic || t('lookup.noPhonetic') }}</p>
          </div>
          <div class="lookup-actions">
            <van-button
              round
              size="small"
              :type="favoriteWord ? 'danger' : 'default'"
              :icon="favoriteWord ? 'like' : 'like-o'"
              :loading="favoriteLoading"
              @click="toggleFavorite"
            />
            <van-button round size="small" type="primary" icon="volume-o" @click="playWord">
              {{ t('lookup.pronounce') }}
            </van-button>
          </div>
        </div>

        <p class="favorite-hint">
          {{ favoriteWord ? t('lookup.savedHint') : t('lookup.unsavedHint') }}
        </p>

        <div class="lookup-button-grid single-action">
          <van-button round plain type="primary" icon="search" class="longman-button" @click="openLongman">
            {{ t('lookup.longman') }}
          </van-button>
        </div>
      </section>

      <!-- Imported MDX dictionaries: one panel per enabled dictionary -->
      <DictionaryPanels :word="result.word" @lookup="openDictionaryWord" />

      <!-- AI deep explanation: etymology, letter shapes, memory "movie" -->
      <WordExplanationCard :word="result.word" />

      <section class="learning-card word-learning-card longman-panel">
        <div class="section-heading">
          <h2>{{ t('lookup.meaning') }}</h2>
          <span>Meaning</span>
        </div>
        <div class="definition-list">
          <article v-for="item in result.meaningOptions" :key="item.value" class="definition-item longman-definition">
            <van-tag plain type="primary">{{ item.label }}</van-tag>
            <p>{{ item.value }}</p>
          </article>
        </div>

        <!-- Real recordings from an imported dictionary (LDOCE) take priority over the text-only examples -->
        <div v-if="recordedExamples.length > 0" class="longman-example-block">
          <div class="section-heading compact-heading">
            <h2>{{ t('lookup.longmanExamples') }}</h2>
            <span>{{ t('lookup.realVoice') }}</span>
          </div>
          <div class="scene-list">
            <article v-for="(item, index) in recordedExamples" :key="item.text" class="scene-item longman-example">
              <div class="scene-title-row">
                <strong>{{ recordedSource }} {{ index + 1 }}</strong>
                <van-button size="mini" round type="primary" plain icon="volume-o" @click="playRecordedExample(item)">
                  {{ t('add.listenSentence') }}
                </van-button>
              </div>
              <blockquote>{{ item.text }}</blockquote>
            </article>
          </div>
        </div>

        <div v-else-if="longmanExamples.length > 0" class="longman-example-block">
          <div class="section-heading compact-heading">
            <h2>{{ t('lookup.longmanExamples') }}</h2>
            <span>Examples</span>
          </div>
          <div class="scene-list">
            <article v-for="item in longmanExamples" :key="item.value" class="scene-item longman-example">
              <div class="scene-title-row">
                <strong>{{ item.label }}</strong>
                <van-button size="mini" round icon="volume-o" @click="speakWord(item.value)">
                  {{ t('add.listenSentence') }}
                </van-button>
              </div>
              <blockquote>{{ item.value }}</blockquote>
            </article>
          </div>
        </div>
      </section>

      <section class="learning-card word-learning-card">
        <div class="section-heading">
          <h2>{{ t('lookup.academic') }}</h2>
          <span>Academic usage</span>
        </div>
        <div class="scene-list">
          <article v-for="item in academicExamples" :key="item.value" class="scene-item">
            <div class="scene-title-row">
              <strong>{{ item.label }}</strong>
              <van-button size="mini" round icon="volume-o" @click="speakWord(item.value)">
                {{ t('add.listenSentence') }}
              </van-button>
            </div>
            <blockquote>{{ item.value }}</blockquote>
          </article>
        </div>
      </section>

      <section class="learning-card word-learning-card">
        <div class="section-heading">
          <h2>{{ t('lookup.root') }}</h2>
          <span>Root memory</span>
        </div>
        <div class="memory-list">
          <article v-for="item in rootMemories" :key="item.root" class="memory-item">
            <van-tag type="primary" plain>{{ item.root }}</van-tag>
            <strong>{{ item.meaning }}</strong>
            <p>{{ item.memory }}</p>
          </article>
        </div>
      </section>

      <section class="learning-card word-learning-card">
        <div class="section-heading">
          <h2>{{ t('lookup.rootBooks') }}</h2>
          <span>PDF References</span>
        </div>
        <van-loading v-if="pdfLoading" type="spinner" size="20" class="pdf-loading">{{ t('lookup.searchingBooks') }}</van-loading>
        <template v-else-if="pdfPages.length > 0">
          <article v-for="page in pdfPages" :key="page.pdf_id + '_' + page.page_num" class="pdf-page-item">
            <p class="pdf-source-label">
              {{ language === 'zh' ? page.title : t('lookup.pdfReference') }}
              {{ language === 'zh' ? `（第 ${page.page_num + 1} 页）` : `(${t('lookup.page')} ${page.page_num + 1})` }}
            </p>
            <p v-if="page.note" class="pdf-note">{{ page.note }}</p>
            <img :src="resolveApiAssetUrl(page.image_url)" :alt="page.title" class="pdf-page-image" loading="lazy" />
          </article>
        </template>
        <p v-else class="pdf-empty-hint">{{ t('lookup.noBookResult') }}</p>
      </section>

      <section class="learning-card word-learning-card">
        <div class="section-heading">
          <h2>{{ t('lookup.scenes') }}</h2>
          <span>Movie & TV</span>
        </div>
        <div class="scene-list">
          <article v-for="scene in mediaScenes" :key="scene.title" class="scene-item">
            <div class="scene-title-row">
              <strong>{{ scene.title }}</strong>
              <van-button size="mini" round icon="volume-o" @click="speakWord(scene.line)">
                {{ t('add.listenSentence') }}
              </van-button>
            </div>
            <p>{{ scene.context }}</p>
            <blockquote>{{ scene.line }}</blockquote>
          </article>
        </div>
      </section>

      <section class="learning-card word-learning-card">
        <div class="section-heading">
          <h2>{{ t('lookup.playphrase') }}</h2>
          <span>Real clips</span>
        </div>
        <div class="playphrase-card">
          <div>
            <p class="eyebrow">External video examples</p>
            <strong>{{ playphraseTitle }}</strong>
          </div>
          <van-button round type="primary" icon="play-circle-o" @click="openPlayPhrase">
            {{ t('lookup.openVideo') }}
          </van-button>
        </div>
      </section>
    </template>

    <van-empty v-else :description="t('lookup.empty')" />
  </main>
</template>

<script setup lang="ts">
import { hapticTap } from '@/shared/lib/haptics';
import DictionaryPanels from '@/features/dictionaries/ui/DictionaryPanels.vue';
import { openInAppBrowser } from '@/shared/lib/inAppBrowser';
import { getRecordedExamplesApi, type RecordedExample } from '@/features/dictionaries/api/dictionaryLibraryApi';
import { API_BASE_URL } from '@/shared/api/config';
import WordExplanationCard from '@/features/words/ui/WordExplanationCard.vue';
import { preloadLongmanAudio } from '@/features/words/model/pronunciation';
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { showFailToast, showSuccessToast, showToast } from 'vant';
import { addWordApi, deleteWordApi, getWordsApi } from '@/features/words/api/wordApi';
import { resolveApiAssetUrl } from '@/shared/api/config';
import {
  buildMediaScenes,
  buildRootMemory,
  lookupDictionary,
  speakWord,
  type DictionaryLookupResult
} from '@/features/words/model/wordLearning';
import { getWordSuggestions } from '@/features/words/model/wordSuggestions';
import { recordSearch } from '@/features/words/model/searchHistory';
import { searchPdfRoots, type PdfRootPage } from '@/features/words/api/pdfRootsApi';
import { useSettingsStore } from '@/shared/model/settingsStore';
import type { Word } from '@/shared/types';

const route = useRoute();
const router = useRouter();
const { language, t } = useSettingsStore();
const keyword = ref('');
const loading = ref(false);
const favoriteLoading = ref(false);
const result = ref<DictionaryLookupResult | null>(null);
const favoriteWord = ref<Word | null>(null);
const pdfPages = ref<PdfRootPage[]>([]);
const pdfLoading = ref(false);
let lookupRequest = 0;

const suggestions = computed(() => getWordSuggestions(keyword.value));
const rootMemories = computed(() => buildRootMemory(result.value?.word || keyword.value, language.value));
const mediaScenes = computed(() => buildMediaScenes(result.value?.word || keyword.value, language.value));
const longmanExamples = computed(() => result.value?.longmanExampleOptions || []);
const academicExamples = computed(() =>
  (result.value?.exampleOptions || []).filter(
    (item) => !longmanExamples.value.some((longmanItem) => longmanItem.value === item.value)
  )
);
const playphraseTitle = computed(() => {
  const word = result.value?.word || keyword.value;
  return language.value === 'zh'
    ? `${t('lookup.playphraseTitle')} "${word}"`
    : `${t('lookup.playphraseTitle')} "${word}" ${t('lookup.playphraseTail')}`;
});

function syncKeywordFromRoute() {
  const word = Array.isArray(route.query.word) ? route.query.word[0] : route.query.word;
  keyword.value = typeof word === 'string' ? word : '';
}

function goBack() {
  if (router.options.history.state.back) {
    router.back();
    return;
  }

  const { mode } = route.query;
  void router.replace({ path: '/home', query: { mode } });
}

function resetLookupResult() {
  lookupRequest += 1;
  loading.value = false;
  result.value = null;
  favoriteWord.value = null;
  pdfPages.value = [];
  pdfLoading.value = false;
}

function clearLookup() {
  keyword.value = '';
  resetLookupResult();
  void router.replace({ query: { ...route.query, word: undefined } });
}

async function findFavorite(word: string) {
  try {
    const words = await getWordsApi();
    return words.find((item) => item.word.trim().toLowerCase() === word.trim().toLowerCase()) || null;
  } catch {
    return null;
  }
}

async function loadWord(updateRoute = true) {
  const word = keyword.value.trim();
  if (!word) {
    showFailToast(t('lookup.emptySearch'));
    return;
  }

  const request = ++lookupRequest;
  loading.value = true;
  favoriteWord.value = null;
  pdfPages.value = [];
  pdfLoading.value = false;
  try {
    const match = await lookupDictionary(word);
    if (request !== lookupRequest) return;

    const favorite = await findFavorite(match.word);
    if (request !== lookupRequest) return;

    result.value = match;
    keyword.value = match.word;
    favoriteWord.value = favorite;
    recordSearch(match.word, match.meaning);

    if (updateRoute) {
      void router.replace({ query: { ...route.query, word: match.word } });
    }

    void loadPdfRoots(match.word, request);
  } catch (error) {
    if (request !== lookupRequest) return;
    result.value = null;
    showFailToast(error instanceof Error ? error.message : t('lookup.failed'));
  } finally {
    if (request === lookupRequest) loading.value = false;
  }
}

async function loadPdfRoots(word: string, request: number) {
  pdfLoading.value = true;
  try {
    const data = await searchPdfRoots(word);
    if (request === lookupRequest) pdfPages.value = data.pages ?? [];
  } catch {
    if (request === lookupRequest) pdfPages.value = [];
  } finally {
    if (request === lookupRequest) pdfLoading.value = false;
  }
}

async function selectSuggestion(word: string) {
  keyword.value = word;
  await loadWord();
}

async function toggleFavorite() {
  hapticTap();
  if (!result.value || favoriteLoading.value) return;

  favoriteLoading.value = true;
  try {
    if (favoriteWord.value) {
      await deleteWordApi(favoriteWord.value.id);
      favoriteWord.value = null;
      showSuccessToast(t('lookup.removed'));
      return;
    }

    const addedWord = await addWordApi({
      word: result.value.word,
      meaning: result.value.meaning,
      example: result.value.example,
      source: 'Lookup favorite'
    });
    favoriteWord.value = addedWord;
    showSuccessToast(t('lookup.added'));
  } catch {
    showFailToast(t('lookup.actionFailed'));
  } finally {
    favoriteLoading.value = false;
  }
}

function openLongman() {
  if (!result.value) return;
  const word = encodeURIComponent(result.value.word.trim().toLowerCase());
  const longmanUrl = `https://www.ldoceonline.com/dictionary/${word}`;

  navigator.clipboard?.writeText(longmanUrl).catch(() => undefined);

  if (/android/i.test(navigator.userAgent)) {
    const fallbackUrl = encodeURIComponent(longmanUrl);
    window.location.href = `intent://www.ldoceonline.com/dictionary/${word}#Intent;scheme=https;package=com.android.chrome;S.browser_fallback_url=${fallbackUrl};end`;
    showToast(t('lookup.openLongman'));
    return;
  }

  openInAppBrowser(longmanUrl);
  showToast(t('lookup.openLongman'));
}

function openPlayPhrase() {
  if (!result.value) return;
  const query = encodeURIComponent(result.value.word.trim().toLowerCase()).replace(/%20/g, '+');
  // In the Android app this opens as an in-app browser sheet; closing it returns to this word.
  openInAppBrowser(`https://www.playphrase.me/#/search?q=${query}&pos=1&language=en`);
}

function playWord() {
  if (!result.value) return;
  speakWord(result.value.word, result.value.longmanAudio || result.value.audio);
}

watch(
  () => route.query.word,
  async () => {
    syncKeywordFromRoute();
    if (!keyword.value.trim()) {
      resetLookupResult();
    } else if (keyword.value !== result.value?.word) {
      await loadWord(false);
    }
  }
);

// ---- example sentences recorded by real speakers (from an imported dictionary's .mdd)
const recordedExamples = ref<RecordedExample[]>([]);
const recordedSource = ref('');
let recordedBase = '';
let recordedRequest = 0;
let examplePlayer: HTMLAudioElement | null = null;

watch(
  () => result.value?.word,
  async (word) => {
    const current = ++recordedRequest;
    recordedExamples.value = [];
    if (!word) return;
    try {
      const data = await getRecordedExamplesApi(word);
      if (current !== recordedRequest) return;
      recordedExamples.value = data.examples;
      recordedSource.value = data.dictionary || 'Longman';
      recordedBase = data.resource_base || '';
    } catch {
      // No imported dictionary with recordings: the text-only examples stay.
    }
  },
  { immediate: true }
);

function playRecordedExample(item: RecordedExample) {
  examplePlayer?.pause();
  examplePlayer = new Audio(`${API_BASE_URL}${recordedBase}${encodeURIComponent(item.audio)}`);
  examplePlayer.play().catch(() => speakWord(item.text));
}

// entry:// links inside a dictionary entry open that word on this page.
function openDictionaryWord(word: string) {
  if (word) router.push({ path: '/lookup', query: { word } });
}

// Fetch the Longman pronunciation as soon as a word is shown, so the speaker button plays instantly.
watch(
  () => result.value?.word,
  (word) => {
    if (word) preloadLongmanAudio(word);
  },
  { immediate: true }
);

onMounted(async () => {
  syncKeywordFromRoute();
  if (keyword.value.trim()) {
    await loadWord(false);
  }
});
</script>

<style scoped>
.lookup-clear-button {
  display: inline-grid;
  inline-size: 32px;
  block-size: 32px;
  place-items: center;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--van-text-color-2);
  cursor: pointer;
}
</style>
