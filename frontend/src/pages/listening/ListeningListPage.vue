<template>
  <main class="page mobile-page listening-page">
    <van-nav-bar :title="t('listening.title')">
      <template #right>
        <button type="button" class="listening-add" :aria-label="t('listening.upload')" @click="showUpload = true">
          <van-icon name="plus" />
        </button>
      </template>
    </van-nav-bar>

    <section class="listening-hero">
      <p class="eyebrow">{{ t('listening.eyebrow') }}</p>
      <h1>{{ t('listening.heading') }}</h1>
      <p>{{ t('listening.description') }}</p>
    </section>

    <!-- Upload form lives in a bottom sheet opened by the + button -->
    <van-popup
      v-model:show="showUpload"
      position="bottom"
      round
      closeable
      safe-area-inset-bottom
      class="listening-upload-sheet"
    >
    <section class="listening-upload">
      <van-field v-model="title" :label="t('listening.titleLabel')" :placeholder="t('listening.titlePlaceholder')" maxlength="200" />
      <van-uploader :after-read="handleAfterRead" :before-read="beforeRead" :max-count="1" accept="audio/*,.mp3,.m4a,.wav,.ogg,.webm,.flac">
        <div class="listening-upload-box">
          <van-icon name="music-o" />
          <strong>{{ selectedFile ? selectedFile.name : t('listening.pickAudio') }}</strong>
          <span>{{ t('listening.pickHint') }}</span>
        </div>
      </van-uploader>
      <van-button
        block
        round
        type="primary"
        icon="upgrade"
        :disabled="!selectedFile"
        :loading="uploading"
        :loading-text="uploadProgress < 100 ? `${t('listening.uploading')} ${uploadProgress}%` : t('listening.uploading')"
        @click="upload"
      >
        {{ t('listening.upload') }}
      </van-button>
      <p class="listening-note">{{ t('listening.copyrightNote') }}</p>
    </section>
    </van-popup>

    <section class="listening-list">
      <div class="section-heading">
        <h2>{{ t('listening.myMaterials') }}</h2>
        <span>{{ materials.length }}</span>
      </div>

      <p v-if="!loading && materials.length === 0" class="listening-empty">{{ t('listening.empty') }}</p>

      <van-swipe-cell v-for="item in materials" :key="item.id">
        <button type="button" class="listening-item" :disabled="item.status !== 'ready'" @click="openMaterial(item)">
          <div class="listening-item-main">
            <strong>{{ item.title }}</strong>
            <span v-if="item.status === 'ready'">
              {{ formatDuration(item.duration_seconds) }} · {{ item.sentence_count }} {{ t('listening.sentences') }}
            </span>
            <span v-else-if="item.status === 'processing'">{{ t('listening.processingHint') }}</span>
            <span v-else class="listening-error">{{ item.error_message || t('listening.failed') }}</span>
          </div>
          <van-loading v-if="item.status === 'processing'" size="18px" />
          <van-tag v-else-if="item.status === 'failed'" type="danger" plain round>{{ t('listening.failed') }}</van-tag>
          <van-icon v-else name="arrow" />
        </button>
        <template #right>
          <van-button square type="danger" class="listening-delete" :text="t('listening.delete')" @click="remove(item)" />
        </template>
      </van-swipe-cell>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { showConfirmDialog, showFailToast, showSuccessToast } from 'vant';
import {
  deleteListeningMaterialApi,
  getListeningMaterialsApi,
  uploadListeningMaterialApi,
  type ListeningMaterialSummary
} from '@/features/listening/api/listeningApi';
import { useSettingsStore } from '@/shared/model/settingsStore';

type UploaderFile = { file?: File };

const MAX_UPLOAD_MB = 80;

const router = useRouter();
const { t } = useSettingsStore();
const title = ref('');
const selectedFile = ref<File | null>(null);
const uploading = ref(false);
const showUpload = ref(false);
const uploadProgress = ref(0);
const loading = ref(true);
const materials = ref<ListeningMaterialSummary[]>([]);
let pollTimer: number | undefined;

function beforeRead(file: File | File[]) {
  const target = Array.isArray(file) ? file[0] : file;
  const looksLikeAudio = target.type.startsWith('audio/') || /\.(mp3|m4a|aac|wav|ogg|oga|opus|webm|flac|mp4)$/i.test(target.name);
  if (!looksLikeAudio) {
    showFailToast(t('listening.audioOnly'));
    return false;
  }
  if (target.size > MAX_UPLOAD_MB * 1024 * 1024) {
    showFailToast(t('listening.tooLarge'));
    return false;
  }
  return true;
}

function handleAfterRead(item: UploaderFile | UploaderFile[]) {
  const file = Array.isArray(item) ? item[0]?.file : item.file;
  if (!file) return;
  selectedFile.value = file;
  if (!title.value.trim()) title.value = file.name.replace(/\.[^.]+$/, '');
}

async function upload() {
  if (!selectedFile.value || uploading.value) return;
  uploading.value = true;
  uploadProgress.value = 0;
  try {
    await uploadListeningMaterialApi(selectedFile.value, title.value.trim(), (percent) => {
      uploadProgress.value = percent;
    });
    showSuccessToast(t('listening.uploaded'));
    showUpload.value = false;
    selectedFile.value = null;
    title.value = '';
    await loadMaterials();
  } catch {
    // http.ts already shows the error toast.
  } finally {
    uploading.value = false;
  }
}

async function loadMaterials() {
  try {
    materials.value = await getListeningMaterialsApi();
  } finally {
    loading.value = false;
  }
  schedulePoll();
}

// Transcription runs on the server; refresh while anything is still processing.
function schedulePoll() {
  window.clearTimeout(pollTimer);
  if (materials.value.some((item) => item.status === 'processing')) {
    pollTimer = window.setTimeout(() => {
      loadMaterials().catch(() => undefined);
    }, 4000);
  }
}

function openMaterial(item: ListeningMaterialSummary) {
  if (item.status === 'ready') router.push(`/listening/${item.id}`);
}

async function remove(item: ListeningMaterialSummary) {
  try {
    await showConfirmDialog({ title: t('listening.delete'), message: `${t('listening.deleteConfirm')} "${item.title}"` });
  } catch {
    return;
  }
  await deleteListeningMaterialApi(item.id);
  materials.value = materials.value.filter((material) => material.id !== item.id);
}

function formatDuration(seconds?: number | null) {
  if (!seconds) return '0:00';
  const total = Math.round(seconds);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
}

onMounted(() => {
  loadMaterials().catch(() => undefined);
});

onBeforeUnmount(() => window.clearTimeout(pollTimer));
</script>

<style scoped>
.listening-hero,
.listening-upload,
.listening-list {
  margin-top: 14px;
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
}

.listening-hero {
  padding: 18px;
  color: #334155;
}

.listening-hero h1 {
  margin: 4px 0 6px;
  font-size: 20px;
  color: #0f172a;
}

.listening-hero p {
  margin: 0;
  line-height: 1.5;
}

.listening-upload {
  display: grid;
  gap: 12px;
  padding: 12px 14px 16px;
}

.listening-upload :deep(.van-uploader),
.listening-upload :deep(.van-uploader__wrapper),
.listening-upload :deep(.van-uploader__input-wrapper) {
  width: 100%;
}

.listening-upload-box {
  display: grid;
  justify-items: center;
  gap: 4px;
  padding: 18px 12px;
  border: 1.5px dashed rgba(37, 99, 235, 0.35);
  border-radius: 14px;
  background: #eff6ff;
  color: #1d4ed8;
  text-align: center;
  word-break: break-all;
}

.listening-upload-box .van-icon {
  font-size: 28px;
}

.listening-upload-box span,
.listening-note {
  color: #64748b;
  font-size: 12px;
}

.listening-note {
  margin: 0;
  line-height: 1.5;
}

.listening-list {
  padding-bottom: 6px;
  overflow: hidden;
}

.listening-empty {
  padding: 8px 16px 14px;
  color: #64748b;
}

.listening-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 16px;
  border: 0;
  border-top: 1px solid #f1f5f9;
  background: transparent;
  text-align: left;
  color: #0f172a;
}

.listening-item:disabled {
  opacity: 0.85;
}

.listening-item-main {
  display: grid;
  flex: 1;
  gap: 3px;
  min-width: 0;
}

.listening-item-main strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.listening-item-main span {
  color: #64748b;
  font-size: 13px;
}

.listening-error {
  color: #dc2626 !important;
}

.listening-delete {
  height: 100%;
}
</style>

<style>
/* Dark theme lives in an unscoped block: Vue drops the rest of a selector after the global pseudo-class. */
.theme-dark .listening-hero,
.theme-dark .listening-upload,
.theme-dark .listening-list {
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.82);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
  color: #cbd5e1;
}

.theme-dark .listening-hero h1,
.theme-dark .listening-item {
  color: #f8fafc;
}

.theme-dark .listening-upload-box {
  border-color: rgba(96, 165, 250, 0.4);
  background: rgba(37, 99, 235, 0.12);
  color: #93c5fd;
}

.theme-dark .listening-item {
  border-top-color: rgba(148, 163, 184, 0.14);
}

.theme-dark .listening-upload-box span,
.theme-dark .listening-note,
.theme-dark .listening-item-main span,
.theme-dark .listening-empty {
  color: #94a3b8;
}

.listening-add {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: var(--ios-blue-tint);
  color: var(--ios-blue);
  font-size: 20px;
  cursor: pointer;
}

.listening-add:active {
  opacity: 0.6;
}

.listening-upload-sheet .listening-upload {
  margin: 0;
  padding: 52px 16px 16px;
  box-shadow: none;
}
</style>
