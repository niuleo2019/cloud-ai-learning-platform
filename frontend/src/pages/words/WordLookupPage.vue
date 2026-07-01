<template>
  <main class="page mobile-page lookup-detail-page">
    <van-nav-bar :title="t('lookup.title')" :left-text="t('common.back')" left-arrow @click-left="router.back()" />

    <section class="lookup-search-card autocomplete-host">
      <van-field v-model="keyword" clearable :placeholder="t('lookup.input')" @keyup.enter="loadWord()">
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

        <div v-if="longmanExamples.length > 0" class="longman-example-block">
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
            <img :src="page.image_url" :alt="page.title" class="pdf-page-image" loading="lazy" />
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
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { showFailToast, showSuccessToast, showToast } from 'vant';
import { addWordApi, deleteWordApi, getWordsApi } from '@/features/words/api/wordApi';
import {
  buildMediaScenes,
  buildRootMemory,
  lookupDictionary,
  speakWord,
  type DictionaryLookupResult
} from '@/features/words/model/wordLearning';
import { getWordSuggestions } from '@/features/words/model/wordSuggestions';
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

async function refreshFavoriteStatus(word: string) {
  try {
    const words = await getWordsApi();
    favoriteWord.value =
      words.find((item) => item.word.trim().toLowerCase() === word.trim().toLowerCase()) || null;
  } catch {
    favoriteWord.value = null;
  }
}

async function loadWord(updateRoute = true) {
  const word = keyword.value.trim();
  if (!word) {
    showFailToast(t('lookup.emptySearch'));
    return;
  }

  loading.value = true;
  favoriteWord.value = null;
  pdfPages.value = [];
  try {
    result.value = await lookupDictionary(word);
    keyword.value = result.value.word;
    await refreshFavoriteStatus(result.value.word);

    if (updateRoute) {
      router.replace({ path: '/lookup', query: { word: result.value.word } });
    }

    loadPdfRoots(result.value.word);
  } catch (error) {
    result.value = null;
    showFailToast(error instanceof Error ? error.message : t('lookup.failed'));
  } finally {
    loading.value = false;
  }
}

async function loadPdfRoots(word: string) {
  pdfLoading.value = true;
  try {
    const data = await searchPdfRoots(word);
    pdfPages.value = data.pages ?? [];
  } catch {
    pdfPages.value = [];
  } finally {
    pdfLoading.value = false;
  }
}

async function selectSuggestion(word: string) {
  keyword.value = word;
  await loadWord();
}

async function toggleFavorite() {
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

  window.open(longmanUrl, '_blank', 'noopener,noreferrer');
  showToast(t('lookup.openLongman'));
}

function openPlayPhrase() {
  if (!result.value) return;
  const query = encodeURIComponent(result.value.word.trim().toLowerCase()).replace(/%20/g, '+');
  window.open(`https://www.playphrase.me/#/search?q=${query}&pos=1&language=en`, '_blank', 'noopener,noreferrer');
}

function playWord() {
  if (!result.value) return;
  speakWord(result.value.word, result.value.longmanAudio || result.value.audio);
}

watch(
  () => route.query.word,
  async () => {
    syncKeywordFromRoute();
    if (keyword.value.trim()) {
      await loadWord(false);
    }
  }
);

onMounted(async () => {
  syncKeywordFromRoute();
  if (keyword.value.trim()) {
    await loadWord(false);
  }
});
</script>
