<template>
  <main class="page mobile-page dictionaries-page">
    <van-nav-bar :title="t('dictionaries.title')" :left-text="t('common.back')" left-arrow @click-left="router.back()" />

    <section class="dict-card dict-hero">
      <p class="eyebrow">MDX / MDD</p>
      <h1>{{ t('dictionaries.heading') }}</h1>
      <p>{{ t('dictionaries.description') }}</p>
    </section>

    <!-- Import -->
    <section class="dict-card dict-import">
      <input ref="fileInput" type="file" multiple class="dict-file-input" @change="onFilesPicked" />
      <button type="button" class="dict-pick" :disabled="uploading" @click="fileInput?.click()">
        <van-icon name="add-o" />
        <strong>{{ t('dictionaries.pick') }}</strong>
        <span>{{ t('dictionaries.pickHint') }}</span>
      </button>

      <ul v-if="pickedFiles.length" class="dict-picked">
        <li v-for="file in pickedFiles" :key="file.name">
          <van-icon :name="file.name.toLowerCase().endsWith('.mdx') ? 'description' : 'photo-o'" />
          <span>{{ file.name }}</span>
          <small>{{ formatSize(file.size) }}</small>
        </li>
      </ul>

      <van-button
        block
        round
        type="primary"
        icon="upgrade"
        :disabled="!canImport"
        :loading="uploading"
        :loading-text="uploadProgress < 100 ? `${t('dictionaries.uploading')} ${uploadProgress}%` : t('dictionaries.indexing')"
        @click="importPicked"
      >
        {{ t('dictionaries.import') }}
      </van-button>

      <div class="dict-scan">
        <p>{{ t('dictionaries.scanHint') }}</p>
        <code>backend/data/dictionaries/</code>
        <van-button size="small" round plain type="primary" icon="replay" :loading="scanning" @click="scan">
          {{ t('dictionaries.scan') }}
        </van-button>
      </div>
    </section>

    <!-- Installed -->
    <section class="dict-card dict-list">
      <div class="dict-list-head">
        <h2>{{ t('dictionaries.installed') }}</h2>
        <span>{{ dictionaries.length }}</span>
      </div>
      <p v-if="!loading && dictionaries.length === 0" class="dict-empty">{{ t('dictionaries.none') }}</p>

      <article v-for="(item, index) in dictionaries" :key="item.id" class="dict-item" :class="{ off: !item.enabled }">
        <div class="dict-item-main" @click="rename(item)">
          <strong>{{ item.title }}</strong>
          <span>
            {{ item.entry_count.toLocaleString() }} {{ t('dictionaries.entries') }}
            · {{ item.mdd_files.length ? `${item.mdd_files.length} MDD` : t('dictionaries.noMdd') }}
          </span>
        </div>
        <div class="dict-item-actions">
          <van-button size="mini" round icon="arrow-up" :disabled="index === 0" @click="move(index, -1)" />
          <van-button size="mini" round icon="arrow-down" :disabled="index === dictionaries.length - 1" @click="move(index, 1)" />
          <van-switch :model-value="item.enabled" size="20px" @update:model-value="toggle(item, $event)" />
          <van-button size="mini" round icon="delete-o" type="danger" plain @click="remove(item)" />
        </div>
      </article>
      <p v-if="dictionaries.length > 1" class="dict-order-hint">{{ t('dictionaries.orderHint') }}</p>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { showConfirmDialog, showDialog, showFailToast, showSuccessToast } from 'vant';
import {
  deleteDictionaryApi,
  getDictionariesApi,
  importDictionaryApi,
  reorderDictionariesApi,
  scanDictionariesApi,
  updateDictionaryApi,
  type ImportedDictionary
} from '@/features/dictionaries/api/dictionaryLibraryApi';
import { useSettingsStore } from '@/shared/model/settingsStore';

const ALLOWED = /\.(mdx|mdd|css|js|png|jpe?g|gif|svg|webp|bmp|ttf|otf|woff2?|mp3|wav|ogg|spx|txt|ini)$/i;

const router = useRouter();
const { t } = useSettingsStore();
const fileInput = ref<HTMLInputElement | null>(null);
const pickedFiles = ref<File[]>([]);
const uploading = ref(false);
const uploadProgress = ref(0);
const scanning = ref(false);
const loading = ref(true);
const dictionaries = ref<ImportedDictionary[]>([]);

const canImport = computed(() => !uploading.value && pickedFiles.value.some((file) => /\.mdx$/i.test(file.name)));

async function load() {
  try {
    dictionaries.value = await getDictionariesApi();
  } finally {
    loading.value = false;
  }
}

function onFilesPicked(event: Event) {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  input.value = '';
  const rejected = files.filter((file) => !ALLOWED.test(file.name));
  if (rejected.length) showFailToast(`${t('dictionaries.unsupported')}: ${rejected.map((f) => f.name).join(', ')}`);
  const accepted = files.filter((file) => ALLOWED.test(file.name));
  // Picking again adds to the selection (Android pickers often allow one file at a time).
  const byName = new Map(pickedFiles.value.map((file) => [file.name, file]));
  accepted.forEach((file) => byName.set(file.name, file));
  pickedFiles.value = [...byName.values()];
  if (accepted.length && !pickedFiles.value.some((file) => /\.mdx$/i.test(file.name))) {
    showFailToast(t('dictionaries.needMdx'));
  }
}

async function importPicked() {
  if (!canImport.value) return;
  uploading.value = true;
  uploadProgress.value = 0;
  try {
    const created = await importDictionaryApi(pickedFiles.value, (percent) => {
      uploadProgress.value = percent;
    });
    showSuccessToast(`${t('dictionaries.imported')}: ${created.map((d) => d.title).join(', ')}`);
    pickedFiles.value = [];
    await load();
  } catch {
    // http.ts shows the server's reason.
  } finally {
    uploading.value = false;
  }
}

async function scan() {
  scanning.value = true;
  try {
    const result = await scanDictionariesApi();
    await load();
    const lines = [
      result.added.length ? `${t('dictionaries.scanAdded')}: ${result.added.map((d) => d.title).join(', ')}` : t('dictionaries.scanNothing'),
      ...result.errors.map((error) => `${error.folder}: ${error.message}`)
    ];
    showDialog({ title: t('dictionaries.scan'), message: lines.join('\n') });
  } finally {
    scanning.value = false;
  }
}

async function toggle(item: ImportedDictionary, enabled: boolean) {
  const updated = await updateDictionaryApi(item.id, { enabled });
  item.enabled = updated.enabled;
}

async function move(index: number, delta: number) {
  const list = [...dictionaries.value];
  const [item] = list.splice(index, 1);
  list.splice(index + delta, 0, item);
  dictionaries.value = list;
  dictionaries.value = await reorderDictionariesApi(list.map((d) => d.id));
}

async function rename(item: ImportedDictionary) {
  const title = window.prompt(t('dictionaries.renamePrompt'), item.title);
  if (title === null || !title.trim() || title.trim() === item.title) return;
  const updated = await updateDictionaryApi(item.id, { title: title.trim() });
  item.title = updated.title;
}

async function remove(item: ImportedDictionary) {
  try {
    await showConfirmDialog({ title: t('dictionaries.delete'), message: `${t('dictionaries.deleteConfirm')}\n${item.title}` });
  } catch {
    return;
  }
  await deleteDictionaryApi(item.id);
  dictionaries.value = dictionaries.value.filter((d) => d.id !== item.id);
}

function formatSize(bytes: number) {
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
  if (bytes >= 1024 ** 2) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

onMounted(() => {
  load().catch(() => undefined);
});
</script>

<style scoped>
.dict-card {
  margin-top: 14px;
  padding: 16px;
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
  color: #334155;
}

.dict-hero h1 {
  margin: 4px 0 6px;
  font-size: 20px;
  color: #0f172a;
}

.dict-hero p {
  margin: 0;
  line-height: 1.5;
}

.dict-import {
  display: grid;
  gap: 12px;
}

.dict-file-input {
  display: none;
}

.dict-pick {
  display: grid;
  justify-items: center;
  gap: 4px;
  padding: 18px 12px;
  border: 1.5px dashed rgba(37, 99, 235, 0.35);
  border-radius: 14px;
  background: #eff6ff;
  color: #1d4ed8;
}

.dict-pick .van-icon {
  font-size: 26px;
}

.dict-pick span,
.dict-scan p,
.dict-order-hint,
.dict-empty {
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.dict-picked {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 13px;
}

.dict-picked li {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dict-picked span {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dict-picked small {
  color: #64748b;
}

.dict-scan {
  display: grid;
  gap: 6px;
  justify-items: start;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
}

.dict-scan code {
  padding: 2px 6px;
  border-radius: 6px;
  background: #f1f5f9;
  font-size: 12px;
}

.dict-list-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dict-list-head h2 {
  margin: 0;
  font-size: 17px;
  color: #0f172a;
}

.dict-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 0;
  border-bottom: 1px solid #f1f5f9;
}

.dict-item.off .dict-item-main {
  opacity: 0.5;
}

.dict-item-main {
  display: grid;
  flex: 1;
  gap: 2px;
  min-width: 0;
}

.dict-item-main strong {
  overflow: hidden;
  color: #0f172a;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dict-item-main span {
  color: #64748b;
  font-size: 12px;
}

.dict-item-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dict-order-hint {
  padding-top: 10px;
}
</style>

<style>
.theme-dark .dictionaries-page .dict-card {
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.82);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
  color: #cbd5e1;
}

.theme-dark .dictionaries-page .dict-hero h1,
.theme-dark .dictionaries-page .dict-list-head h2,
.theme-dark .dictionaries-page .dict-item-main strong {
  color: #f8fafc;
}

.theme-dark .dictionaries-page .dict-pick {
  border-color: rgba(96, 165, 250, 0.4);
  background: rgba(37, 99, 235, 0.12);
  color: #93c5fd;
}

.theme-dark .dictionaries-page .dict-scan,
.theme-dark .dictionaries-page .dict-item {
  border-color: rgba(148, 163, 184, 0.14);
}

.theme-dark .dictionaries-page .dict-scan code {
  background: rgba(148, 163, 184, 0.16);
  color: #e2e8f0;
}
</style>
