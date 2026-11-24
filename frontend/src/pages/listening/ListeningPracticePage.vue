<template>
  <main class="page mobile-page practice-page">
    <van-nav-bar
      :title="material?.title || t('listening.title')"
      :left-text="t('common.back')"
      left-arrow
      @click-left="router.back()"
    />

    <van-loading v-if="loading" class="practice-loading" vertical>{{ t('listening.loadingAudio') }}</van-loading>

    <template v-else-if="material && sentence">
      <audio ref="audioRef" :src="audioUrl" preload="auto" @pause="playing = false" @play="playing = true" />

      <!-- Sentence navigator: one dot per sentence, coloured by best score -->
      <section class="practice-progress">
        <div class="practice-progress-head">
          <strong>{{ t('listening.sentence') }} {{ currentIndex + 1 }} / {{ sentences.length }}</strong>
          <span>{{ formatTime(sentence.start) }} – {{ formatTime(sentence.end) }}</span>
        </div>
        <div ref="dotsRef" class="practice-dots">
          <button
            v-for="item in sentences"
            :key="item.index"
            type="button"
            class="practice-dot"
            :class="[dotClass(item.index), { active: item.index === currentIndex }]"
            :aria-label="`${t('listening.sentence')} ${item.index + 1}`"
            @click="goTo(item.index, true)"
          />
        </div>
      </section>

      <!-- Player -->
      <section class="practice-player">
        <div class="practice-controls">
          <van-button round icon="arrow-left" :disabled="currentIndex === 0" @click="goTo(currentIndex - 1, true)" />
          <van-button round type="primary" class="practice-play" :icon="playing ? 'pause' : 'play'" @click="togglePlay">
            {{ playing ? t('listening.pause') : t('listening.playSentence') }}
          </van-button>
          <van-button
            round
            icon="arrow"
            :disabled="currentIndex === sentences.length - 1"
            @click="goTo(currentIndex + 1, true)"
          />
        </div>
        <div class="practice-options">
          <button type="button" class="practice-chip" :class="{ on: loop }" @click="loop = !loop">
            <van-icon name="replay" /> {{ t('listening.loop') }}
          </button>
          <SegmentedControl
            class="practice-rate"
            :model-value="rate"
            :options="RATES.map((value) => ({ label: `${value}x`, value }))"
            @update:model-value="setRate"
          />
        </div>
      </section>

      <!-- Mode tabs -->
      <van-tabs v-model:active="mode" class="practice-tabs" shrink>
        <van-tab :title="t('listening.dictation')" name="dictation">
          <section class="practice-card">
            <van-field
              v-model="draft"
              type="textarea"
              rows="3"
              autosize
              :placeholder="t('listening.dictationPlaceholder')"
              autocomplete="off"
              autocapitalize="off"
              autocorrect="off"
              :spellcheck="false"
              class="practice-input"
            />
            <van-button block round type="primary" :disabled="!draft.trim()" @click="checkDictation">
              {{ t('listening.check') }}
            </van-button>
            <CompareView v-if="dictationResult" :result="dictationResult" :attempt-label="t('listening.youWrote')" @word="openWord" />
          </section>
        </van-tab>

        <van-tab :title="t('listening.retell')" name="retell">
          <section class="practice-card">
            <p class="practice-hint">{{ t('listening.retellHint') }}</p>
            <div v-if="!recorderSupported" class="practice-warning">
              <p>{{ t('listening.micUnavailable') }}</p>
              <a v-if="localhostUrl" :href="localhostUrl" class="practice-warning-link">{{ t('listening.openOnLocalhost') }}</a>
            </div>
            <van-button
              v-else
              block
              round
              :type="recordState === 'recording' ? 'danger' : 'primary'"
              :icon="recordState === 'recording' ? 'stop-circle-o' : 'audio'"
              :class="{ 'practice-recording': recordState === 'recording' }"
              :loading="recordState === 'recognising'"
              :loading-text="t('listening.recognising')"
              @click="toggleRecording"
            >
              {{ recordState === 'recording' ? t('listening.stopRecording') : t('listening.startRecording') }}
            </van-button>

            <template v-if="retellResult">
              <div class="practice-recognised">
                <span>{{ t('listening.recognised') }}</span>
                <p>{{ retellText || t('listening.nothingHeard') }}</p>
              </div>
              <div class="practice-compare-audio">
                <van-button size="small" round icon="volume-o" :disabled="!recording" @click="playMyRecording">
                  {{ t('listening.myRecording') }}
                </van-button>
                <van-button size="small" round icon="play-circle-o" @click="playSentence">
                  {{ t('listening.original') }}
                </van-button>
              </div>
              <CompareView :result="retellResult" :attempt-label="t('listening.youSaid')" @word="openWord" />
            </template>
          </section>
        </van-tab>
      </van-tabs>

      <!-- Original sentence: hidden until checked or revealed; every word can be tapped -->
      <section class="practice-card practice-original">
        <div class="practice-original-head">
          <strong>{{ t('listening.originalText') }}</strong>
          <div>
            <van-button size="mini" round plain icon="edit" @click="openEdit">{{ t('listening.edit') }}</van-button>
            <van-button size="mini" round plain :icon="textVisible ? 'eye-o' : 'closed-eye'" @click="revealed = !revealed">
              {{ textVisible ? t('listening.hide') : t('listening.show') }}
            </van-button>
          </div>
        </div>
        <p v-if="textVisible" class="practice-sentence">
          <template v-for="(piece, i) in sentenceWords" :key="i">
            <button v-if="lookupWord(piece)" type="button" class="practice-word" @click="openWord(piece)">{{ piece }}</button>
            <span v-else>{{ piece }}</span>
            {{ ' ' }}
          </template>
        </p>
        <p v-else class="practice-hidden">{{ t('listening.hiddenHint') }}</p>
        <p v-if="sentence.edited" class="practice-edited">{{ t('listening.editedNote') }}</p>
        <p v-else class="practice-edited">{{ t('listening.machineNote') }}</p>
      </section>
    </template>

    <van-action-sheet
      v-model:show="wordSheet"
      :title="selectedWord"
      :actions="wordActions"
      :cancel-text="t('listening.cancel')"
      close-on-click-action
      @select="onWordAction"
    />

    <van-dialog
      v-model:show="editing"
      :title="t('listening.editTitle')"
      show-cancel-button
      :confirm-button-text="t('listening.save')"
      :cancel-button-text="t('listening.cancel')"
      :before-close="saveEdit"
    >
      <van-field v-model="editText" type="textarea" rows="4" autosize maxlength="1000" class="practice-edit-field" />
    </van-dialog>
  </main>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, ref, watch, type PropType } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { showFailToast } from 'vant';
import {
  fetchListeningAudioUrl,
  getListeningMaterialApi,
  recogniseRetellApi,
  updateListeningSentenceApi,
  type ListeningMaterial,
  type ListeningSentence
} from '@/features/listening/api/listeningApi';
import { recordPracticeAttemptApi } from '@/features/planner/api/plannerApi';
import { compareText, lookupWord, type CompareResult } from '@/features/listening/model/textCompare';
import { MicrophoneUnavailableError, VoiceRecorder, canRecord, type Recording } from '@/features/listening/model/voiceRecorder';
import { playLongmanAudio, preloadLongmanAudio, type Accent } from '@/features/words/model/pronunciation';
import { speakWord } from '@/features/words/model/wordLearning';
import { useSettingsStore } from '@/shared/model/settingsStore';
import SegmentedControl from '@/shared/ui/SegmentedControl.vue';
import { hapticSuccess, hapticWarning } from '@/shared/lib/haptics';

type Mode = 'dictation' | 'retell';
type Scores = Record<number, { dictation?: number; retell?: number }>;

const RATES = [0.75, 1, 1.25] as const;
const LOOP_GAP_MS = 700;

const route = useRoute();
const router = useRouter();
const { t } = useSettingsStore();
const materialId = Number(route.params.id);
const POSITION_KEY = `vocab.listening.position.${materialId}`;
const SCORES_KEY = `vocab.listening.scores.${materialId}`;

const loading = ref(true);
const material = ref<ListeningMaterial | null>(null);
const audioUrl = ref('');
const audioRef = ref<HTMLAudioElement | null>(null);
const dotsRef = ref<HTMLElement | null>(null);
const currentIndex = ref(readNumber(POSITION_KEY));
const playing = ref(false);
const loop = ref(false);
const rate = ref<number>(1);
const mode = ref<Mode>('dictation');
const revealed = ref(false);
const scores = ref<Scores>(readJson<Scores>(SCORES_KEY, {}));

const draft = ref('');
const dictationResult = ref<CompareResult | null>(null);

const recorderSupported = canRecord();
// Browsers only expose the microphone on HTTPS or localhost; offer the localhost address on this computer.
const localhostUrl =
  !recorderSupported && window.location.protocol === 'http:' && !['localhost', '127.0.0.1'].includes(window.location.hostname)
    ? `http://localhost:${window.location.port || '80'}${window.location.pathname}${window.location.search}`
    : '';
const recorder = new VoiceRecorder();
const recordState = ref<'idle' | 'recording' | 'recognising'>('idle');
const recording = ref<Recording | null>(null);
const retellText = ref('');
const retellResult = ref<CompareResult | null>(null);

const wordSheet = ref(false);
const selectedWord = ref('');
const editing = ref(false);
const editText = ref('');

const sentences = computed<ListeningSentence[]>(() => material.value?.sentences || []);
const sentence = computed(() => sentences.value[currentIndex.value]);
const sentenceWords = computed(() => (sentence.value?.text || '').split(/\s+/).filter(Boolean));
const textVisible = computed(() => revealed.value || !!dictationResult.value || !!retellResult.value);
const wordActions = computed(() => [
  { name: t('listening.pronounceGb'), value: 'gb' },
  { name: t('listening.pronounceUs'), value: 'us' },
  { name: t('listening.lookupWord'), value: 'lookup' }
]);

// ---------------------------------------------------------------- storage

function readNumber(key: string) {
  try {
    return Number(localStorage.getItem(key)) || 0;
  } catch {
    return 0;
  }
}

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function save(key: string, value: unknown) {
  try {
    localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value));
  } catch {
    // Storage unavailable: progress lasts for this page view only.
  }
}

function recordScore(kind: Mode, score: number) {
  if (score >= 90) hapticSuccess();
  else hapticWarning();
  const index = currentIndex.value;
  const previous = scores.value[index]?.[kind] ?? 0;
  scores.value = { ...scores.value, [index]: { ...scores.value[index], [kind]: Math.max(previous, score) } };
  save(SCORES_KEY, scores.value);
}

function dotClass(index: number) {
  const entry = scores.value[index];
  if (!entry) return '';
  const best = Math.max(entry.dictation ?? 0, entry.retell ?? 0);
  return best >= 90 ? 'good' : best >= 60 ? 'fair' : 'poor';
}

// ---------------------------------------------------------------- playback

let frame = 0;
let loopTimer: number | undefined;
let endTimer: number | undefined;

function stopAudio() {
  cancelAnimationFrame(frame);
  window.clearTimeout(loopTimer);
  window.clearTimeout(endTimer);
  audioRef.value?.pause();
}

function playSentence() {
  const audio = audioRef.value;
  const current = sentence.value;
  if (!audio || !current) return;
  stopAudio();
  audio.playbackRate = rate.value;
  audio.currentTime = current.start;
  audio.play().catch(() => showFailToast(t('listening.playFailed')));
  // timeupdate fires only ~4 times a second; check every frame so the next sentence is not heard.
  // A timer at the expected end time backs this up when frames are throttled (background tab).
  const watchEnd = () => {
    cancelAnimationFrame(frame);
    window.clearTimeout(endTimer);
    if (audio.paused) return;
    const remaining = current.end - audio.currentTime;
    if (remaining <= 0.02) {
      audio.pause();
      if (loop.value) loopTimer = window.setTimeout(playSentence, LOOP_GAP_MS);
      return;
    }
    endTimer = window.setTimeout(watchEnd, (remaining / audio.playbackRate) * 1000);
    frame = requestAnimationFrame(watchEnd);
  };
  frame = requestAnimationFrame(watchEnd);
}

function togglePlay() {
  if (playing.value) stopAudio();
  else playSentence();
}

function setRate(value: number) {
  rate.value = value;
  if (audioRef.value) audioRef.value.playbackRate = value;
}

function goTo(index: number, autoplay = false) {
  if (index < 0 || index >= sentences.value.length) return;
  stopAudio();
  recorder.cancel();
  currentIndex.value = index;
  if (autoplay) nextTick(playSentence);
}

watch(currentIndex, (index) => {
  save(POSITION_KEY, String(index));
  draft.value = '';
  dictationResult.value = null;
  retellResult.value = null;
  retellText.value = '';
  recordState.value = 'idle';
  recording.value = null;
  revealed.value = false;
  nextTick(() => {
    const dot = dotsRef.value?.children[index] as HTMLElement | undefined;
    dot?.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' });
  });
});

function formatTime(seconds: number) {
  const total = Math.floor(seconds);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
}

// ---------------------------------------------------------------- dictation

function checkDictation() {
  if (!sentence.value || !draft.value.trim()) return;
  dictationResult.value = compareText(sentence.value.text, draft.value);
  recordScore('dictation', dictationResult.value.score);
  reportAttempt('dictation', draft.value, dictationResult.value);
}

/** Send the result to the server so the study-planning agent can see which words were missed or misheard. */
function reportAttempt(kind: Mode, attempt: string, result: CompareResult) {
  if (!sentence.value) return;
  recordPracticeAttemptApi({
    material_id: materialId,
    sentence_index: currentIndex.value,
    mode: kind,
    score: result.score,
    expected_text: sentence.value.text,
    attempt_text: attempt,
    missed: result.ops.flatMap((op) => (op.type === 'missing' && op.expected ? [op.expected] : [])).slice(0, 60),
    wrong: result.ops.flatMap((op) => (op.type === 'wrong' ? [{ expected: op.expected, actual: op.actual }] : [])).slice(0, 60)
  }).catch(() => undefined); // best effort: practice must never fail because of this
}

// ---------------------------------------------------------------- retell

async function toggleRecording() {
  if (recordState.value === 'recognising') return;
  if (recordState.value === 'recording') {
    await finishRecording();
    return;
  }
  stopAudio();
  try {
    await recorder.start(30, () => {
      finishRecording();
    });
    recordState.value = 'recording';
  } catch (error) {
    recordState.value = 'idle';
    showFailToast(error instanceof MicrophoneUnavailableError ? t('listening.micDenied') : t('listening.recordFailed'));
  }
}

async function finishRecording() {
  if (recordState.value !== 'recording') return;
  recordState.value = 'recognising';
  try {
    const result = await recorder.stop();
    if (recording.value) URL.revokeObjectURL(recording.value.url);
    recording.value = result;
    const { text } = await recogniseRetellApi(result.blob, result.filename);
    retellText.value = text;
    retellResult.value = compareText(sentence.value.text, text);
    recordScore('retell', retellResult.value.score);
    reportAttempt('retell', text, retellResult.value);
  } catch {
    // Network/server errors are shown by http.ts.
  } finally {
    recordState.value = 'idle';
  }
}

function playMyRecording() {
  if (!recording.value) return;
  stopAudio();
  new Audio(recording.value.url).play().catch(() => showFailToast(t('listening.playFailed')));
}

// ---------------------------------------------------------------- words

function openWord(display: string) {
  const word = lookupWord(display);
  if (!word) return;
  selectedWord.value = word;
  wordSheet.value = true;
  preloadLongmanAudio(word, 'gb');
  preloadLongmanAudio(word, 'us');
}

function onWordAction(action: { value: string }) {
  const word = selectedWord.value;
  if (action.value === 'lookup') {
    stopAudio();
    router.push({ path: '/lookup', query: { word } });
    return;
  }
  playLongmanAudio(word, action.value as Accent).then((played) => {
    if (!played) speakWord(word);
  });
}

// ---------------------------------------------------------------- edit transcript

function openEdit() {
  editText.value = sentence.value?.text || '';
  editing.value = true;
}

async function saveEdit(action: string) {
  if (action !== 'confirm') return true;
  const text = editText.value.trim();
  if (!text || !material.value?.sentences) return false;
  try {
    const updated = await updateListeningSentenceApi(materialId, currentIndex.value, text);
    material.value.sentences[currentIndex.value] = updated;
    if (dictationResult.value) dictationResult.value = compareText(updated.text, draft.value);
    if (retellResult.value) retellResult.value = compareText(updated.text, retellText.value);
    return true;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------- lifecycle

onMounted(async () => {
  try {
    material.value = await getListeningMaterialApi(materialId);
    if (material.value.status !== 'ready' || !material.value.sentences?.length) {
      showFailToast(t('listening.notReady'));
      router.replace('/listening');
      return;
    }
    // Opened from a study-plan task: jump to that sentence and mode.
    const target = Number(route.query.sentence);
    if (Number.isInteger(target) && target >= 0 && target < material.value.sentences.length) currentIndex.value = target;
    if (route.query.mode === 'retell' || route.query.mode === 'dictation') mode.value = route.query.mode;
    if (currentIndex.value >= material.value.sentences.length) currentIndex.value = 0;
    audioUrl.value = await fetchListeningAudioUrl(materialId);
  } catch {
    router.replace('/listening');
  } finally {
    loading.value = false;
  }
});

onBeforeUnmount(() => {
  stopAudio();
  recorder.cancel();
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value);
  if (recording.value) URL.revokeObjectURL(recording.value.url);
});

// ---------------------------------------------------------------- comparison view

const CompareView = defineComponent({
  name: 'CompareView',
  props: {
    result: { type: Object as PropType<CompareResult>, required: true },
    attemptLabel: { type: String, required: true }
  },
  emits: ['word'],
  setup(props, { emit }) {
    return () => {
      const { result } = props;
      const level = result.score >= 90 ? 'good' : result.score >= 60 ? 'fair' : 'poor';
      const pieces = result.ops.flatMap((op, i) => {
        if (op.type === 'match') {
          return op.expected ? [h('span', { key: i, class: 'cmp ok', onClick: () => emit('word', op.expected) }, op.expected), ' '] : [];
        }
        if (op.type === 'missing') {
          return [h('span', { key: i, class: 'cmp missing', onClick: () => emit('word', op.expected) }, op.expected), ' '];
        }
        if (op.type === 'wrong') {
          return [
            h('span', { key: i, class: 'cmp wrong', onClick: () => emit('word', op.expected) }, [
              op.expected,
              h('small', `${props.attemptLabel}: ${op.actual}`)
            ]),
            ' '
          ];
        }
        return [h('span', { key: i, class: 'cmp extra' }, op.actual), ' '];
      });
      return h('div', { class: 'compare' }, [
        h('div', { class: ['compare-score', level] }, [
          h('strong', `${result.score}`),
          h('span', `${result.correct} / ${result.total} ${t('listening.wordsCorrect')}`)
        ]),
        h('p', { class: 'compare-text' }, pieces),
        h('div', { class: 'compare-legend' }, [
          h('span', { class: 'cmp ok' }, t('listening.legendOk')),
          h('span', { class: 'cmp missing' }, t('listening.legendMissing')),
          h('span', { class: 'cmp wrong' }, t('listening.legendWrong')),
          h('span', { class: 'cmp extra' }, t('listening.legendExtra'))
        ])
      ]);
    };
  }
});
</script>

<style scoped>
.practice-loading {
  padding: 60px 0;
}

.practice-progress,
.practice-player,
.practice-card {
  margin-top: 12px;
  padding: 14px;
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
}

.practice-progress-head {
  display: flex;
  justify-content: space-between;
  color: #0f172a;
  font-size: 14px;
}

.practice-progress-head span {
  color: #64748b;
}

.practice-dots {
  display: flex;
  gap: 6px;
  margin-top: 10px;
  padding: 3px 2px 6px;
  overflow-x: auto;
  scrollbar-width: none;
}

.practice-dot {
  flex: 0 0 auto;
  width: 14px;
  height: 14px;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 50%;
  background: #e2e8f0;
}

.practice-dot.good {
  background: #22c55e;
}

.practice-dot.fair {
  background: #f59e0b;
}

.practice-dot.poor {
  background: #ef4444;
}

.practice-dot.active {
  border-color: #1d4ed8;
  transform: scale(1.25);
}

.practice-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
}

.practice-play {
  min-width: 150px;
}

.practice-options {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
}

.practice-chip {
  padding: 5px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: #ffffff;
  color: #334155;
  font-size: 13px;
}

.practice-chip.on {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 600;
}

.practice-tabs {
  margin-top: 12px;
}

.practice-tabs :deep(.van-tabs__wrap) {
  border-radius: 12px;
  overflow: hidden;
}

.practice-card {
  display: grid;
  gap: 12px;
}

.practice-input {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.practice-hint,
.practice-hidden,
.practice-edited {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.practice-edited {
  font-size: 12px;
}

.practice-warning {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fef3c7;
  color: #92400e;
  font-size: 13px;
}

.practice-warning p {
  margin: 0;
}

.practice-warning-link {
  display: inline-block;
  margin-top: 8px;
  color: #1d4ed8;
  font-weight: 600;
  text-decoration: underline;
}

.practice-recording {
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  50% {
    box-shadow: 0 0 0 8px rgba(239, 68, 68, 0.18);
  }
}

.practice-recognised span {
  color: #64748b;
  font-size: 12px;
}

.practice-recognised p {
  margin: 4px 0 0;
  color: #0f172a;
  line-height: 1.5;
}

.practice-compare-audio {
  display: flex;
  gap: 8px;
}

.practice-original-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.practice-original-head div {
  display: flex;
  gap: 6px;
}

.practice-sentence {
  margin: 0;
  text-align: left;
  font-size: 17px;
  line-height: 1.9;
  color: #0f172a;
}

.practice-word {
  padding: 0 1px;
  border: 0;
  border-bottom: 1px dashed #93c5fd;
  background: transparent;
  color: inherit;
  font: inherit;
}

.practice-edit-field {
  margin: 8px 0;
}

/* Comparison view (rendered by CompareView) */
.practice-page :deep(.compare) {
  display: grid;
  gap: 10px;
  padding-top: 4px;
}

.practice-page :deep(.compare-score) {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.practice-page :deep(.compare-score strong) {
  font-size: 28px;
}

.practice-page :deep(.compare-score span) {
  color: #64748b;
  font-size: 13px;
}

.practice-page :deep(.compare-score.good strong) {
  color: #16a34a;
}

.practice-page :deep(.compare-score.fair strong) {
  color: #d97706;
}

.practice-page :deep(.compare-score.poor strong) {
  color: #dc2626;
}

.practice-page :deep(.compare-text) {
  margin: 0;
  text-align: left;
  font-size: 16px;
  line-height: 2.1;
}

.practice-page :deep(.cmp) {
  padding: 1px 3px;
  border-radius: 5px;
}

.practice-page :deep(.cmp.ok) {
  color: #166534;
}

.practice-page :deep(.cmp.missing) {
  background: #fef3c7;
  color: #92400e;
  text-decoration: underline wavy #f59e0b;
}

.practice-page :deep(.cmp.wrong) {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.2;
  background: #fee2e2;
  color: #b91c1c;
  font-weight: 600;
  vertical-align: middle;
}

.practice-page :deep(.cmp.wrong small) {
  color: #64748b;
  font-size: 11px;
  font-weight: 400;
}

.practice-page :deep(.cmp.extra) {
  color: #94a3b8;
  text-decoration: line-through;
}

.practice-page :deep(.compare-legend) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
}
</style>

<style>
/* Dark theme lives in an unscoped block: Vue drops the rest of a selector after the global pseudo-class. */
.theme-dark .practice-progress,
.theme-dark .practice-player,
.theme-dark .practice-card {
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.82);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
}

.theme-dark .practice-progress-head,
.theme-dark .practice-sentence,
.theme-dark .practice-recognised p,
.theme-dark .practice-original-head {
  color: #f8fafc;
}

.theme-dark .practice-dot {
  background: #334155;
}

.theme-dark .practice-dot.good {
  background: #22c55e;
}

.theme-dark .practice-dot.fair {
  background: #f59e0b;
}

.theme-dark .practice-dot.poor {
  background: #ef4444;
}

.theme-dark .practice-dot.active {
  border-color: #93c5fd;
}

.theme-dark .practice-chip {
  border-color: rgba(148, 163, 184, 0.35);
  background: transparent;
  color: #cbd5e1;
}

.theme-dark .practice-chip.on {
  border-color: #60a5fa;
  background: rgba(37, 99, 235, 0.2);
  color: #bfdbfe;
}

.theme-dark .practice-input {
  border-color: rgba(148, 163, 184, 0.3);
}

.theme-dark .practice-original-head .van-button--plain {
  border-color: rgba(148, 163, 184, 0.4);
  background: transparent;
  color: #cbd5e1;
}

.theme-dark .practice-warning-link {
  color: #93c5fd;
}

.theme-dark .practice-warning {
  background: rgba(245, 158, 11, 0.16);
  color: #fcd34d;
}

/* CompareView is rendered by a render function, so its dark colours live in an unscoped block. */
.theme-dark .practice-page .cmp.ok {
  color: #86efac;
}

.theme-dark .practice-page .cmp.missing {
  background: rgba(245, 158, 11, 0.18);
  color: #fcd34d;
}

.theme-dark .practice-page .cmp.wrong {
  background: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
}

.theme-dark .practice-page .cmp.wrong small {
  color: #cbd5e1;
}
</style>
