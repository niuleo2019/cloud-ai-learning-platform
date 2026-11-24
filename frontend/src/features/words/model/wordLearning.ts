import { lookupOfflineDictionaryApi } from '@/features/words/api/dictionaryApi';
import type { AppLanguage } from '@/shared/model/settingsStore';
import type { MediaScene, RootMemory } from '@/shared/types';
import { isSingleHeadword, playLongmanAudio } from '@/features/words/model/pronunciation';
import { API_BASE_URL } from '@/shared/api/config';

interface DictionaryMeaning {
  partOfSpeech: string;
  definitions: Array<{
    definition: string;
    example?: string;
  }>;
}

interface DictionaryEntry {
  phonetic?: string;
  phonetics?: Array<{
    text?: string;
    audio?: string;
  }>;
  meanings?: DictionaryMeaning[];
}

interface PronunciationLookupResult {
  phonetic: string;
  audio: string;
}

export interface DictionaryOption {
  label: string;
  value: string;
}

export interface DictionaryLookupResult {
  word: string;
  phonetic: string;
  audio: string;
  meaning: string;
  example: string;
  meaningOptions: DictionaryOption[];
  exampleOptions: DictionaryOption[];
  longmanText?: string;
  longmanHtml?: string;
  longmanAudio?: string;
  longmanMeaningOptions?: DictionaryOption[];
  longmanExampleOptions?: DictionaryOption[];
  source?: string;
}

const rootRules: Array<{
  pattern: RegExp;
  root: string;
  meaning: Record<AppLanguage, string>;
  memory: Record<AppLanguage, string>;
}> = [
  {
    pattern: /spect|spec/i,
    root: 'spect / spec',
    meaning: { en: 'to look, observe', zh: '看、观察' },
    memory: {
      en: 'It shares the idea of seeing with inspect, respect and spectator.',
      zh: '和 inspect、respect、spectator 同源，可以联想到“看见、观察、审视”。'
    }
  },
  {
    pattern: /vid|vis/i,
    root: 'vid / vis',
    meaning: { en: 'to see, vision', zh: '看、视觉' },
    memory: {
      en: 'Video and vision both point to sight, so connect the word with a visual scene.',
      zh: 'video、vision 都和“看见”有关，遇到这个词根先往视觉场景想。'
    }
  },
  {
    pattern: /port/i,
    root: 'port',
    meaning: { en: 'to carry, transport', zh: '携带、运输' },
    memory: {
      en: 'Airport, transport and portable all carry the idea of moving something.',
      zh: 'airport、transport、portable 都和“带走、运送”有关。'
    }
  },
  {
    pattern: /dict/i,
    root: 'dict',
    meaning: { en: 'to say, speak', zh: '说、表达' },
    memory: {
      en: 'Dictionary, predict and dictation are all connected with saying or speaking.',
      zh: 'dictionary、predict、dictation 都和“说出来、表达”有关。'
    }
  },
  {
    pattern: /cred/i,
    root: 'cred',
    meaning: { en: 'to believe', zh: '相信' },
    memory: {
      en: 'Credit and credible both connect to trust and belief.',
      zh: 'credit、credible 都和“相信、信任”有关。'
    }
  },
  {
    pattern: /form/i,
    root: 'form',
    meaning: { en: 'shape, form', zh: '形状、形成' },
    memory: {
      en: 'Information, transform and reform all carry a sense of forming or changing shape.',
      zh: 'information、transform、reform 都有“形成、改变形态”的感觉。'
    }
  },
  {
    pattern: /struct/i,
    root: 'struct',
    meaning: { en: 'to build', zh: '建造' },
    memory: {
      en: 'Structure, construct and infrastructure are about building or arranging parts.',
      zh: 'structure、construct、infrastructure 都和“搭建结构”有关。'
    }
  },
  {
    pattern: /ject/i,
    root: 'ject',
    meaning: { en: 'to throw', zh: '投掷、抛出' },
    memory: {
      en: 'Project, reject and object can be remembered as pushing or throwing something out.',
      zh: 'project、reject、object 可以理解成“把东西抛出去”。'
    }
  },
  {
    pattern: /act/i,
    root: 'act',
    meaning: { en: 'to do, act', zh: '做、行动' },
    memory: {
      en: 'Action, active and react all connect to doing something.',
      zh: 'action、active、react 都和“行动”有关。'
    }
  },
  {
    pattern: /mem|mnem/i,
    root: 'mem / mnem',
    meaning: { en: 'memory', zh: '记忆' },
    memory: {
      en: 'Memory, memo and mnemonic all help you connect this root with remembering.',
      zh: 'memory、memo、mnemonic 都和“记住”有关。'
    }
  }
];

function uniqueOptions(options: DictionaryOption[]) {
  const seen = new Set<string>();
  return options.filter((item) => {
    const key = item.value.trim().toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function buildAcademicExamples(word: string): DictionaryOption[] {
  return [
    {
      label: 'IELTS Reading - Research',
      value: `Researchers use ${word} to support claims about changes in human behaviour.`
    },
    {
      label: 'IELTS Reading - Environment',
      value: `The passage presents ${word} that climate patterns have shifted over recent decades.`
    },
    {
      label: 'TOEFL Lecture - Campus',
      value: `The professor explains how this ${word} helps students understand the main argument.`
    },
    {
      label: 'TOEFL Reading - History',
      value: `This ${word} suggests that the settlement was used for trade and storage.`
    }
  ];
}

function splitLongmanText(text: string): DictionaryOption[] {
  return text
    .split(/(?<=[.!?])\s+/)
    .map((item) => item.trim())
    .filter((item) => item.length > 20)
    .slice(0, 6)
    .map((item, index) => ({
      label: index === 0 ? 'Longman definition' : 'Longman note',
      value: item
    }));
}

function splitLongmanExamples(text: string): DictionaryOption[] {
  const exampleMatches = [...text.matchAll(/Example:\s*([^.!?]+[.!?]?)/gi)]
    .map((match) => match[1]?.trim())
    .filter(Boolean) as string[];

  if (exampleMatches.length > 0) {
    return uniqueOptions(
      exampleMatches.slice(0, 4).map((value, index) => ({
        label: `Longman example ${index + 1}`,
        value
      }))
    );
  }

  return text
    .split(/(?<=[.!?])\s+/)
    .map((item) => item.trim())
    .filter((item) => item.length > 28 && /\b(the|a|an|that|this|is|are|was|were)\b/i.test(item))
    .slice(0, 3)
    .map((item, index) => ({
      label: `Longman example ${index + 1}`,
      value: item
    }));
}

async function lookupOfflineLongman(cleanWord: string): Promise<DictionaryLookupResult | null> {
  try {
    const result = await lookupOfflineDictionaryApi(cleanWord);
    if (!result.found || !result.text) {
      return null;
    }

    const meaningOptions = splitLongmanText(result.text);
    const longmanExampleOptions = splitLongmanExamples(result.text);
    const exampleOptions = uniqueOptions([...longmanExampleOptions, ...buildAcademicExamples(cleanWord)]);

    return {
      word: result.word,
      phonetic: '',
      audio: result.audio || '',
      meaning: meaningOptions[0]?.value || result.text,
      example: exampleOptions[0]?.value || '',
      meaningOptions,
      exampleOptions,
      longmanText: result.text,
      longmanHtml: result.html || '',
      longmanAudio: result.audio || '',
      longmanMeaningOptions: meaningOptions,
      longmanExampleOptions,
      source: result.source || 'Longman offline'
    };
  } catch {
    return null;
  }
}

async function lookupOnlineDictionary(cleanWord: string): Promise<DictionaryLookupResult> {
  const response = await fetch(`https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(cleanWord)}`);

  if (!response.ok) {
    throw new Error('Word not found. Please check the spelling.');
  }

  const entries = (await response.json()) as DictionaryEntry[];
  const firstEntry = entries[0];
  const allMeanings = entries.flatMap((entry) => entry.meanings || []);
  const allDefinitions = allMeanings.flatMap((meaning) =>
    meaning.definitions.map((definition) => ({
      partOfSpeech: meaning.partOfSpeech,
      definition: definition.definition,
      example: definition.example
    }))
  );

  const meaningOptions = uniqueOptions(
    allDefinitions.slice(0, 8).map((item) => ({
      label: `${item.partOfSpeech} - ${item.definition}`,
      value: item.definition
    }))
  );

  const dictionaryExamples = uniqueOptions(
    allDefinitions
      .filter((item) => item.example)
      .slice(0, 4)
      .map((item) => ({
        label: `Dictionary example - ${item.partOfSpeech}`,
        value: item.example || ''
      }))
  );

  const exampleOptions = uniqueOptions([...buildAcademicExamples(cleanWord), ...dictionaryExamples]);
  const audio = firstEntry?.phonetics?.find((item) => item.audio)?.audio || '';
  const phonetic = firstEntry?.phonetic || firstEntry?.phonetics?.find((item) => item.text)?.text || '';

  return {
    word: cleanWord,
    phonetic,
    audio,
    meaning: meaningOptions[0]?.value || '',
    example: exampleOptions[0]?.value || '',
    meaningOptions,
    exampleOptions,
    longmanMeaningOptions: [],
    longmanExampleOptions: [],
    source: 'Dictionary API'
  };
}

async function lookupOnlinePronunciation(cleanWord: string): Promise<PronunciationLookupResult | null> {
  try {
    const response = await fetch(`https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(cleanWord)}`);
    if (!response.ok) {
      return null;
    }

    const entries = (await response.json()) as DictionaryEntry[];
    const firstEntry = entries[0];
    const phonetic = firstEntry?.phonetic || firstEntry?.phonetics?.find((item) => item.text)?.text || '';
    const audio = firstEntry?.phonetics?.find((item) => item.audio)?.audio || '';

    if (!phonetic && !audio) {
      return null;
    }

    return { phonetic, audio };
  } catch {
    return null;
  }
}

export async function lookupDictionary(word: string): Promise<DictionaryLookupResult> {
  const cleanWord = word.trim().toLowerCase();
  const offlineResult = await lookupOfflineLongman(cleanWord);
  if (offlineResult) {
    const pronunciation = await lookupOnlinePronunciation(cleanWord);
    if (pronunciation) {
      return {
        ...offlineResult,
        phonetic: offlineResult.phonetic || pronunciation.phonetic,
        audio: offlineResult.audio || pronunciation.audio
      };
    }

    return offlineResult;
  }

  return lookupOnlineDictionary(cleanWord);
}

// ---------------------------------------------------------------- speaking words and sentences
// Order: real Longman recording (words) -> server neural voice (Piper, sentences) -> browser voice.

const NATURAL_VOICE = /natural|neural|online|google|enhanced|premium|siri/i;
const ACCENT_ORDER = ['en-GB', 'en-AU', 'en-US'];

function englishVoices() {
  return window.speechSynthesis.getVoices().filter((voice) => voice.lang.replace('_', '-').startsWith('en'));
}

function rankVoice(voice: SpeechSynthesisVoice, preferNatural: boolean) {
  const accent = ACCENT_ORDER.indexOf(voice.lang.replace('_', '-'));
  const natural = NATURAL_VOICE.test(voice.name);
  return (preferNatural === natural ? 0 : 10) + (accent === -1 ? 3 : accent);
}

function pickVoice(preferNatural: boolean) {
  return [...englishVoices()].sort((a, b) => rankVoice(a, preferNatural) - rankVoice(b, preferNatural))[0] || null;
}

// Voices load asynchronously in Chrome: warm the list so the first tap already has them.
if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
  window.speechSynthesis.getVoices();
  window.speechSynthesis.addEventListener?.('voiceschanged', () => window.speechSynthesis.getVoices());
}

// Keep a reference: Chrome can garbage-collect an utterance before it plays (no sound, no error).
let currentUtterance: SpeechSynthesisUtterance | null = null;

function speakWithBrowserVoice(text: string, preferNatural = true): boolean {
  if (!('speechSynthesis' in window) || typeof SpeechSynthesisUtterance === 'undefined') {
    return false;
  }
  const synth = window.speechSynthesis;
  const utterance = new SpeechSynthesisUtterance(text);
  const voice = pickVoice(preferNatural);
  if (voice) {
    utterance.voice = voice;
    utterance.lang = voice.lang;
  } else {
    utterance.lang = 'en-GB';
  }
  utterance.rate = 0.95;
  currentUtterance = utterance;

  // Online voices sometimes never start (offline, blocked, or a browser bug): retry with a local voice.
  let started = false;
  utterance.onstart = () => {
    started = true;
  };
  const retryLocal = () => {
    if (started || currentUtterance !== utterance) return;
    synth.cancel();
    if (preferNatural) speakWithBrowserVoice(text, false);
  };
  utterance.onerror = (event) => {
    if (event.error !== 'interrupted' && event.error !== 'canceled') retryLocal();
  };
  if (voice && !voice.localService) window.setTimeout(retryLocal, 1500);

  const speakNow = () => {
    synth.resume();
    synth.speak(utterance);
  };
  if (synth.speaking || synth.pending) {
    // speak() straight after cancel() is dropped by Chrome; give the engine a moment.
    synth.cancel();
    window.setTimeout(speakNow, 80);
  } else {
    speakNow();
  }
  return true;
}

let sentencePlayer: HTMLAudioElement | null = null;

/** A sentence read by the server's neural voice (Piper). Falls back to the browser voice. */
function speakSentence(text: string) {
  sentencePlayer?.pause();
  window.speechSynthesis?.cancel();
  const params = new URLSearchParams({ text });
  sentencePlayer = new Audio(`${API_BASE_URL}/dictionary/speak?${params.toString()}`);
  sentencePlayer.play().catch(() => speakWithBrowserVoice(text));
}

export function speakWord(text: string, audioUrl?: string) {
  const cleanText = text.trim();
  if (!cleanText) return;

  const playFallback = () => {
    if (audioUrl) {
      const audio = new Audio(audioUrl);
      audio.play().catch(() => speakSentence(cleanText));
      return;
    }
    speakSentence(cleanText);
  };

  // Real Longman recordings first (single words); sentences and missing words use the neural voice.
  if (isSingleHeadword(cleanText)) {
    playLongmanAudio(cleanText).then((played) => {
      if (!played) playFallback();
    });
    return;
  }

  playFallback();
}

export function buildRootMemory(word: string, language: AppLanguage = 'en'): RootMemory[] {
  const cleanWord = word.trim();
  if (!cleanWord) return [];

  const matched = rootRules.filter((rule) => rule.pattern.test(cleanWord));
  if (matched.length > 0) {
    return matched.map((rule) => ({
      root: rule.root,
      meaning: rule.meaning[language],
      memory: rule.memory[language]
    }));
  }

  return [
    {
      root: cleanWord.slice(0, Math.min(cleanWord.length, 4)),
      meaning: language === 'zh' ? '先拆前缀或音节，再看语境' : 'Break it into sounds, then use context',
      memory:
        language === 'zh'
          ? `暂时没有命中常见词根。可以先把 ${cleanWord} 拆成音节读三遍，再结合下面的影视语境记忆。`
          : `No common root matched yet. Read ${cleanWord} by syllables three times, then connect it with the examples below.`
    }
  ];
}

export function buildMediaScenes(word: string, language: AppLanguage = 'en'): MediaScene[] {
  const cleanWord = word.trim();
  if (!cleanWord) return [];

  return [
    {
      title: 'Crime / Detective scene',
      context:
        language === 'zh'
          ? '警探在现场讨论线索，语气通常短促、清晰，适合记住重音。'
          : 'Detectives discuss a clue at the scene. The short, clear tone helps you hear the stress.',
      line: `The ${cleanWord} changes everything in this case.`
    },
    {
      title: 'Workplace drama scene',
      context:
        language === 'zh'
          ? '经理或同事在会议里解释问题，适合记住正式语境。'
          : 'A manager explains a problem in a meeting, which fits a more formal context.',
      line: `We need to look at the ${cleanWord} before making a decision.`
    },
    {
      title: 'Family / Friends scene',
      context:
        language === 'zh'
          ? '朋友之间解释误会，语速更自然，适合练习日常发音。'
          : 'Friends explain a misunderstanding with a more natural pace for everyday pronunciation.',
      line: `I did not understand it until I saw the ${cleanWord}.`
    }
  ];
}
