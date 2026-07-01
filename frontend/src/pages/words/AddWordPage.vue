<template>
  <main class="page mobile-page">
    <van-nav-bar :title="t('add.title')" :left-text="t('common.back')" left-arrow @click-left="router.back()" />

    <section class="page-intro">
      <p class="eyebrow">New Word</p>
      <h1>{{ t('add.heading') }}</h1>
      <p>{{ t('add.description') }}</p>
    </section>

    <section class="lookup-panel">
      <van-field
        v-model="form.word"
        clearable
        :label="t('add.lookupLabel')"
        :placeholder="t('home.placeholder')"
        @keyup.enter="handleLookup"
      >
        <template #button>
          <van-button size="small" type="primary" :loading="lookupLoading" @click="handleLookup">
            {{ t('add.lookupButton') }}
          </van-button>
        </template>
      </van-field>

      <div v-if="lookupResult" class="lookup-result">
        <div>
          <p class="eyebrow">Pronunciation</p>
          <h2>{{ lookupResult.word }}</h2>
          <span>{{ lookupResult.phonetic || t('add.noPhonetic') }}</span>
        </div>
        <van-button round type="primary" icon="volume-o" @click="playCurrentWord">
          {{ t('add.pronounce') }}
        </van-button>
      </div>
    </section>

    <section class="form-panel">
      <van-form @submit="handleSubmit">
        <van-cell-group inset>
          <van-field
            v-model="form.word"
            name="word"
            :label="t('words.word')"
            :placeholder="t('home.placeholder')"
            :rules="[{ required: true, message: t('common.requiredWord') }]"
          />
          <van-field
            v-model="form.meaning"
            name="meaning"
            :label="t('words.meaning')"
            :placeholder="meaningPlaceholder"
            :rules="[{ required: true, message: t('common.requiredMeaning') }]"
            @keydown.enter="handleMeaningEnter"
          >
            <template #button>
              <van-button size="small" plain type="primary" :disabled="meaningActions.length === 0" @click="showMeaningSheet = true">
                {{ t('add.select') }}
              </van-button>
            </template>
          </van-field>
          <button
            v-if="pendingMeaningSuggestion"
            type="button"
            class="ghost-suggestion"
            @click="acceptMeaningSuggestion"
          >
            <span>{{ t('words.meaning') }}</span>
            <strong>{{ pendingMeaningSuggestion }}</strong>
          </button>
          <van-field
            v-model="form.example"
            rows="3"
            autosize
            type="textarea"
            :label="t('words.example')"
            :placeholder="examplePlaceholder"
            @keydown.enter="handleExampleEnter"
          >
            <template #button>
              <van-button size="small" plain type="primary" :disabled="exampleActions.length === 0" @click="showExampleSheet = true">
                {{ t('add.select') }}
              </van-button>
            </template>
          </van-field>
          <button
            v-if="pendingExampleSuggestion"
            type="button"
            class="ghost-suggestion"
            @click="acceptExampleSuggestion"
          >
            <span>{{ t('words.example') }}</span>
            <strong>{{ pendingExampleSuggestion }}</strong>
          </button>
          <van-field v-model="form.source" :label="t('words.source')" :placeholder="t('add.sourcePlaceholder')" />
        </van-cell-group>

        <div class="form-actions">
          <van-button round block type="primary" native-type="submit" :loading="loading">
            {{ t('add.save') }}
          </van-button>
        </div>
      </van-form>
    </section>

    <section v-if="rootMemories.length > 0" class="learning-card word-learning-card">
      <div class="section-heading">
        <h2>{{ t('add.rootMemory') }}</h2>
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

    <section v-if="mediaScenes.length > 0" class="learning-card word-learning-card">
      <div class="section-heading">
        <h2>{{ t('add.movieContext') }}</h2>
        <span>Movie & TV</span>
      </div>
      <div class="scene-list">
        <article v-for="scene in mediaScenes" :key="scene.title" class="scene-item">
          <div class="scene-title-row">
            <strong>{{ scene.title }}</strong>
            <van-button size="mini" round icon="volume-o" @click="speakLine(scene.line)">
              {{ t('add.listenSentence') }}
            </van-button>
          </div>
          <p>{{ scene.context }}</p>
          <blockquote>{{ scene.line }}</blockquote>
        </article>
      </div>
    </section>

    <van-action-sheet
      v-model:show="showMeaningSheet"
      :actions="meaningActions"
      :title="t('add.meaningPopup')"
      close-on-click-action
      @select="selectMeaning"
    />

    <van-action-sheet
      v-model:show="showExampleSheet"
      :actions="exampleActions"
      :title="t('add.examplePopup')"
      close-on-click-action
      @select="selectExample"
    />
  </main>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { showFailToast, showSuccessToast } from 'vant';
import { addWordApi } from '@/features/words/api/wordApi';
import {
  buildMediaScenes,
  buildRootMemory,
  lookupDictionary,
  speakWord,
  type DictionaryLookupResult,
  type DictionaryOption
} from '@/features/words/model/wordLearning';
import { useSettingsStore } from '@/shared/model/settingsStore';

interface SheetAction {
  name: string;
  subname?: string;
  value: string;
}

const router = useRouter();
const { language, t } = useSettingsStore();
const loading = ref(false);
const lookupLoading = ref(false);
const lookupResult = ref<DictionaryLookupResult | null>(null);
const showMeaningSheet = ref(false);
const showExampleSheet = ref(false);

const form = reactive({
  word: '',
  meaning: '',
  example: '',
  source: ''
});

const rootMemories = computed(() => buildRootMemory(form.word, language.value));
const mediaScenes = computed(() => buildMediaScenes(form.word, language.value));

const meaningActions = computed<SheetAction[]>(() => toSheetActions(lookupResult.value?.meaningOptions || []));
const exampleActions = computed<SheetAction[]>(() => toSheetActions(lookupResult.value?.exampleOptions || []));
const pendingMeaningSuggestion = computed(() => {
  if (form.meaning.trim()) return '';
  return lookupResult.value?.meaning || meaningActions.value[0]?.value || '';
});
const pendingExampleSuggestion = computed(() => {
  if (form.example.trim()) return '';
  return lookupResult.value?.example || exampleActions.value[0]?.value || '';
});
const meaningPlaceholder = computed(() => pendingMeaningSuggestion.value || t('add.meaningPlaceholder'));
const examplePlaceholder = computed(() => pendingExampleSuggestion.value || t('add.examplePlaceholder'));

function toSheetActions(options: DictionaryOption[]): SheetAction[] {
  return options.map((item) => ({
    name: item.value,
    subname: item.label,
    value: item.value
  }));
}

async function handleLookup() {
  if (!form.word.trim()) {
    showFailToast(t('add.emptySearch'));
    return;
  }

  lookupLoading.value = true;
  try {
    const result = await lookupDictionary(form.word);
    lookupResult.value = result;
    form.word = result.word;
    form.source = 'Dictionary + IELTS Reading';

    showSuccessToast(t('add.lookupDone'));
  } catch (error) {
    showFailToast(error instanceof Error ? error.message : t('add.lookupFailed'));
  } finally {
    lookupLoading.value = false;
  }
}

function selectMeaning(action: SheetAction) {
  form.meaning = action.value;
}

function selectExample(action: SheetAction) {
  form.example = action.value;
  form.source = 'IELTS Reading';
}

function acceptMeaningSuggestion() {
  if (!pendingMeaningSuggestion.value) return;
  form.meaning = pendingMeaningSuggestion.value;
}

function acceptExampleSuggestion() {
  if (!pendingExampleSuggestion.value) return;
  form.example = pendingExampleSuggestion.value;
  form.source = 'IELTS Reading';
}

function handleMeaningEnter(event: KeyboardEvent) {
  if (!pendingMeaningSuggestion.value) return;
  event.preventDefault();
  acceptMeaningSuggestion();
}

function handleExampleEnter(event: KeyboardEvent) {
  if (!pendingExampleSuggestion.value) return;
  event.preventDefault();
  acceptExampleSuggestion();
}

function playCurrentWord() {
  if (!form.word.trim()) return;
  speakWord(form.word, lookupResult.value?.audio);
}

function speakLine(line: string) {
  speakWord(line);
}

async function handleSubmit() {
  loading.value = true;
  try {
    await addWordApi(form);
    showSuccessToast(t('add.success'));
    router.push('/words');
  } finally {
    loading.value = false;
  }
}
</script>
