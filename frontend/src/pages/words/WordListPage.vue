<template>
  <main class="page mobile-page">
    <van-nav-bar :title="t('words.title')" :right-text="t('words.add')" @click-right="router.push('/add-word')" />

    <van-search v-model="searchQuery" :placeholder="t('words.search')" shape="round" background="transparent" />

    <van-pull-refresh v-model="refreshing" @refresh="loadWords">
      <van-empty
        v-if="loaded && filteredWords.length === 0"
        image="search"
        :description="searchQuery ? t('words.noMatch') : t('words.empty')"
      >
        <van-button v-if="!searchQuery" round type="primary" to="/add-word">{{ t('add.title') }}</van-button>
      </van-empty>

      <div v-else class="word-list">
        <van-swipe-cell v-for="item in filteredWords" :key="item.id">
          <article
            class="word-card"
            @pointerdown="handlePointerDown"
            @pointermove="handlePointerMove"
            @click="goToLookup(item)"
          >
            <div class="word-card-main">
              <div>
                <h2>{{ item.word }}</h2>
                <p>{{ item.meaning }}</p>
              </div>
              <div class="word-card-tools">
                <van-button round size="mini" icon="volume-o" @pointerdown.stop @click.stop="playWord(item.word)">
                  {{ t('words.pronounce') }}
                </van-button>
                <van-button round size="mini" plain type="primary" @pointerdown.stop @click.stop="openEdit(item)">
                  {{ t('words.edit') }}
                </van-button>
                <van-tag plain :type="stageTagType(item.review_stage ?? 0)">
                  {{ t('words.stage') }} {{ item.review_stage ?? 0 }}
                </van-tag>
              </div>
            </div>

            <p v-if="item.example" class="word-example">{{ item.example }}</p>

            <div class="word-meta">
              <span>{{ item.source || t('words.noSource') }}</span>
              <span>{{ t('words.cardHint') }}</span>
            </div>
          </article>

          <template #right>
            <button class="swipe-delete-action" type="button" @click.stop="handleDelete(item.id)">
              <span class="delete-mark">x</span>
              <span>{{ t('words.delete') }}</span>
            </button>
          </template>
        </van-swipe-cell>
      </div>
    </van-pull-refresh>

    <van-dialog v-model:show="showEdit" :title="t('words.editTitle')" show-cancel-button @confirm="handleUpdate">
      <van-cell-group>
        <van-field v-model="editForm.word" :label="t('words.word')" />
        <van-field v-model="editForm.meaning" :label="t('words.meaning')" />
        <van-field v-model="editForm.example" :label="t('words.example')" rows="2" autosize type="textarea" />
        <van-field v-model="editForm.source" :label="t('words.source')" />
      </van-cell-group>
    </van-dialog>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { showConfirmDialog, showToast } from 'vant';
import { deleteWordApi, getWordsApi, updateWordApi } from '@/features/words/api/wordApi';
import { speakWord } from '@/features/words/model/wordLearning';
import { useSettingsStore } from '@/shared/model/settingsStore';
import type { Word } from '@/shared/types';

const router = useRouter();
const { language, t } = useSettingsStore();
const words = ref<Word[]>([]);
const refreshing = ref(false);
// Don't flash "No words yet" while the list is still loading.
const loaded = ref(false);
const searchQuery = ref('');

const filteredWords = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  if (!q) return words.value;
  return words.value.filter(
    (w) =>
      w.word.toLowerCase().includes(q) ||
      w.meaning.toLowerCase().includes(q) ||
      (w.source ?? '').toLowerCase().includes(q)
  );
});

function stageTagType(stage: number): 'default' | 'warning' | 'primary' | 'success' {
  if (stage === 0) return 'default';
  if (stage <= 2) return 'warning';
  if (stage <= 4) return 'primary';
  return 'success';
}

const showEdit = ref(false);
const editingId = ref<number | null>(null);
const pointerStartX = ref(0);
const hasSwiped = ref(false);

const editForm = reactive({
  word: '',
  meaning: '',
  example: '',
  source: ''
});

async function loadWords() {
  try {
    words.value = await getWordsApi();
  } finally {
    loaded.value = true;
    refreshing.value = false;
  }
}

function handlePointerDown(event: PointerEvent) {
  pointerStartX.value = event.clientX;
  hasSwiped.value = false;
}

function handlePointerMove(event: PointerEvent) {
  if (Math.abs(event.clientX - pointerStartX.value) > 8) {
    hasSwiped.value = true;
  }
}

function goToLookup(item: Word) {
  if (hasSwiped.value) {
    hasSwiped.value = false;
    return;
  }

  router.push({ path: '/lookup', query: { word: item.word } });
}

function playWord(word: string) {
  speakWord(word);
}

function openEdit(item: Word) {
  editingId.value = item.id;
  editForm.word = item.word;
  editForm.meaning = item.meaning;
  editForm.example = item.example || '';
  editForm.source = item.source || '';
  showEdit.value = true;
}

async function handleUpdate() {
  if (!editingId.value) return;
  await updateWordApi(editingId.value, editForm);
  showToast(t('words.updateSuccess'));
  await loadWords();
}

async function handleDelete(id: number) {
  await showConfirmDialog({
    title: t('words.deleteTitle'),
    message: t('words.deleteMessage')
  });

  await deleteWordApi(id);
  showToast(t('words.deleteSuccess'));
  await loadWords();
}

onMounted(loadWords);
</script>
