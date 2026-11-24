<template>
  <main class="page mobile-page vision-page">
    <van-nav-bar :title="t('vision.title')" :left-text="t('common.back')" left-arrow @click-left="router.back()" />

    <section class="vision-hero-card">
      <p class="eyebrow">{{ t('vision.eyebrow') }}</p>
      <h1>{{ t('vision.heading') }}</h1>
      <p>{{ t('vision.description') }}</p>
    </section>

    <section class="vision-upload-card">
      <van-button
        v-if="canUseNativeCamera"
        block
        round
        type="primary"
        icon="photograph"
        class="vision-camera-button"
        :loading="loading && fileSource === 'camera'"
        :loading-text="t('vision.recognising')"
        :disabled="loading"
        @click="captureWithCamera"
      >
        {{ t('vision.takePhoto') }}
      </van-button>

      <van-uploader :after-read="handleAfterRead" :before-read="beforeRead" :max-count="1" accept="image/*">
        <div class="vision-upload-box">
          <van-icon name="photograph" />
          <strong>{{ t('vision.upload') }}</strong>
          <span>{{ t('vision.uploadHint') }}</span>
        </div>
      </van-uploader>

      <van-button
        v-if="selectedFile && fileSource === 'upload'"
        block
        round
        type="primary"
        icon="scan"
        :loading="loading"
        :loading-text="t('vision.recognising')"
        class="vision-action"
        @click="extractWords"
      >
        {{ t('vision.extract') }}
      </van-button>

      <p v-if="selectedFile" class="vision-file-name">{{ selectedFile.name }}</p>
    </section>

    <section v-if="result" class="vision-result-card">
      <div class="section-heading">
        <h2>{{ t('vision.result') }}</h2>
        <span>{{ result.engine }}</span>
      </div>

      <div v-if="result.words.length > 0" class="vision-word-grid">
        <button v-for="item in result.words" :key="item.word" type="button" @click="openLookup(item.word)">
          <strong>{{ item.word }}</strong>
          <span>x{{ item.count }}</span>
        </button>
      </div>
      <p v-else class="vision-empty">{{ t('vision.noWords') }}</p>

      <div class="vision-meta">
        <van-tag v-for="step in result.preprocessing" :key="step" plain type="primary">{{ step }}</van-tag>
      </div>
    </section>

    <section v-if="result?.text" class="vision-text-card">
      <div class="section-heading">
        <h2>{{ t('vision.ocrText') }}</h2>
        <span>OCR</span>
      </div>
      <p>{{ result.text }}</p>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { showFailToast, showSuccessToast } from 'vant';
import { extractWordsFromImageApi, type VisionExtractionResult } from '@/features/vision/api/visionApi';
import { CameraCancelledError, canUseNativeCamera, shrinkImageForOcr, takePhotoForOcr } from '@/features/vision/model/cameraCapture';
import { useSettingsStore } from '@/shared/model/settingsStore';

type UploaderFile = {
  file?: File;
};

const RESULT_STORAGE_KEY = 'vocab.vision.lastResult';

const router = useRouter();
const { t } = useSettingsStore();
const selectedFile = ref<File | null>(null);
const loading = ref(false);
const fileSource = ref<'camera' | 'upload'>('upload');
const result = ref<VisionExtractionResult | null>(loadSavedResult());

// Keep the last OCR result for this tab, so returning from the lookup page
// does not force the user to upload and extract the same image again.
function loadSavedResult(): VisionExtractionResult | null {
  try {
    const saved = sessionStorage.getItem(RESULT_STORAGE_KEY);
    return saved ? (JSON.parse(saved) as VisionExtractionResult) : null;
  } catch {
    return null;
  }
}

function saveResult(value: VisionExtractionResult | null) {
  try {
    if (value) {
      sessionStorage.setItem(RESULT_STORAGE_KEY, JSON.stringify(value));
    } else {
      sessionStorage.removeItem(RESULT_STORAGE_KEY);
    }
  } catch {
    // Storage can be unavailable (e.g. private mode); the page still works without it.
  }
}

function beforeRead(file: File | File[]) {
  const targetFile = Array.isArray(file) ? file[0] : file;

  if (!targetFile.type.startsWith('image/')) {
    showFailToast(t('vision.imageOnly'));
    return false;
  }

  if (targetFile.size > 8 * 1024 * 1024) {
    showFailToast(t('vision.tooLarge'));
    return false;
  }

  return true;
}

function handleAfterRead(item: UploaderFile | UploaderFile[]) {
  const uploadItem = Array.isArray(item) ? item[0] : item;
  if (!uploadItem.file) return;

  fileSource.value = 'upload';
  selectedFile.value = uploadItem.file;
  result.value = null;
  saveResult(null);
}

async function extractWords() {
  if (!selectedFile.value) {
    showFailToast(t('vision.selectFirst'));
    return;
  }

  loading.value = true;
  try {
    const upload = await shrinkImageForOcr(selectedFile.value);
    result.value = await extractWordsFromImageApi(upload);
    saveResult(result.value);
    if (result.value.words.length > 0) {
      showSuccessToast(t('vision.done'));
    } else {
      showFailToast(t('vision.noWords'));
    }
  } catch {
    // The HTTP interceptor already shows the error toast (invalid image, too large, network).
  } finally {
    loading.value = false;
  }
}

// Android app: open the rear camera directly, then run the same OCR flow as an uploaded image.
async function captureWithCamera() {
  try {
    const file = await takePhotoForOcr();
    fileSource.value = 'camera';
    if (file.size > 8 * 1024 * 1024) {
      showFailToast(t('vision.tooLarge'));
      return;
    }
    selectedFile.value = file;
    result.value = null;
    saveResult(null);
    await extractWords();
  } catch (error) {
    if (!(error instanceof CameraCancelledError)) {
      showFailToast(t('vision.cameraFailed'));
    }
  }
}

function openLookup(word: string) {
  router.push({ path: '/lookup', query: { word } });
}
</script>

<style scoped>
.vision-camera-button {
  margin-bottom: 12px;
}

.vision-page {
  display: grid;
  align-content: start;
  gap: 14px;
}

.vision-hero-card,
.vision-upload-card,
.vision-result-card,
.vision-text-card {
  padding: 18px;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
}

.theme-dark .vision-hero-card,
.theme-dark .vision-upload-card,
.theme-dark .vision-result-card,
.theme-dark .vision-text-card {
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(15, 23, 42, 0.86);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.28);
}

.vision-hero-card h1 {
  margin: 4px 0 10px;
  color: #0f172a;
  font-size: 28px;
  line-height: 1.15;
}

.theme-dark .vision-hero-card h1 {
  color: #f8fafc;
}

.vision-hero-card p:last-child {
  margin: 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.6;
}

.vision-upload-card {
  display: grid;
  gap: 14px;
}

.vision-upload-box {
  width: 100%;
  min-height: 156px;
  display: grid;
  place-items: center;
  gap: 8px;
  padding: 22px;
  border: 1px dashed rgba(37, 99, 235, 0.45);
  border-radius: 14px;
  color: #2563eb;
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.08), rgba(6, 182, 212, 0.05));
  text-align: center;
}

.vision-upload-box .van-icon {
  font-size: 34px;
}

.vision-upload-box strong {
  color: #0f172a;
  font-size: 18px;
}

.theme-dark .vision-upload-box strong {
  color: #f8fafc;
}

.vision-upload-box span,
.vision-file-name,
.vision-empty {
  color: #64748b;
  font-size: 13px;
}

.vision-action {
  margin-top: 2px;
}

.vision-word-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.vision-word-grid button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px;
  border: 1px solid rgba(37, 99, 235, 0.18);
  border-radius: 12px;
  color: #0f172a;
  background: #f8fbff;
  font: inherit;
  text-align: left;
}

.theme-dark .vision-word-grid button {
  color: #f8fafc;
  background: rgba(30, 41, 59, 0.86);
}

.vision-word-grid span {
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.vision-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.vision-text-card p {
  margin: 0;
  color: #475569;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
}

.theme-dark .vision-text-card p {
  color: #cbd5e1;
}
</style>
