<template>
  <div class="buddy-wrap" :class="{ mini, still }">
  <button
    ref="root"
    type="button"
    class="buddy"
    :class="{ bounce: bouncing }"
    :aria-label="mini ? 'AI' : 'Vocabulary buddy'"
    @click="poke"
    @animationend="bouncing = false"
  >
    <span class="buddy-glow" aria-hidden="true" />
    <span class="buddy-body" :style="{ '--tilt': `${look.x * 0.6}deg` }">
      <span class="buddy-shine" aria-hidden="true" />
      <span class="buddy-eyes" :style="{ transform: `translate(${look.x}px, ${look.y}px)` }">
        <span class="buddy-eye" :class="{ shut: blinking, happy }" />
        <span class="buddy-eye" :class="{ shut: blinking, happy }" />
      </span>
    </span>
  </button>

  <!-- Thought bubble: two little puffs, then the cloud with the message -->
  <Transition name="bubble">
    <button v-if="message" :key="message.en" type="button" class="buddy-bubble" @click="act(message)">
      <span class="puff puff-1" aria-hidden="true" />
      <span class="puff puff-2" aria-hidden="true" />
      <span class="cloud">{{ language === 'zh' ? message.zh : message.en }}</span>
    </button>
  </Transition>
  </div>
</template>

<script setup lang="ts">
// A small breathing blob whose eyes wander around, blink, and glance at the pointer.
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { hapticTap } from '@/shared/lib/haptics';
import { useSettingsStore } from '@/shared/model/settingsStore';

interface BuddyLine {
  zh: string;
  en: string;
  /** What tapping the bubble does: open the search, or the AI assistant. */
  action?: 'search' | 'agent';
}

const GREETING: BuddyLine = { zh: '嗨～', en: 'Hi!' };
const LINES: BuddyLine[] = [
  GREETING,
  { zh: '想查哪个单词？', en: 'Look up a word?', action: 'search' },
  { zh: '需要什么帮助吗？', en: 'Need help?', action: 'agent' },
  { zh: '今天也来记几个词吧', en: 'Learn a few words?', action: 'search' },
  { zh: '有不懂的可以问我哦', en: 'Ask me anything!', action: 'agent' },
  { zh: '拍张照也能找生词', en: 'Try a photo search' }
];

// mini: a tiny, silent version that opens the AI chat when tapped.
// still: a motionless picture of the character (e.g. as a title); not interactive.
const props = defineProps<{ mini?: boolean; still?: boolean }>();
const emit = defineEmits<{ search: [] }>();
const router = useRouter();
const { language } = useSettingsStore();
const message = ref<BuddyLine | null>(null);
let lastLine: BuddyLine | null = null;

const look = reactive({ x: 0, y: 0 });
const blinking = ref(false);
const happy = ref(false);
const bouncing = ref(false);
const root = ref<HTMLElement>();

const timers = new Set<number>();
let followUntil = 0;

function later(fn: () => void, ms: number) {
  const id = window.setTimeout(() => {
    timers.delete(id);
    fn();
  }, ms);
  timers.add(id);
}

const rand = (min: number, max: number) => min + Math.random() * (max - min);

// Glance somewhere new every second or two; sometimes come back to the middle.
function wander() {
  if (Date.now() > followUntil) {
    const centre = Math.random() < 0.25;
    look.x = centre ? 0 : Math.round(rand(-9, 9));
    look.y = centre ? 0 : Math.round(rand(-6, 4));
  }
  later(wander, rand(900, 2400));
}

function blink() {
  blinking.value = true;
  later(() => (blinking.value = false), 140);
  // Now and then a quick double blink.
  if (Math.random() < 0.2) {
    later(() => (blinking.value = true), 260);
    later(() => (blinking.value = false), 400);
  }
  later(blink, rand(2500, 5500));
}

function onPointerMove(event: PointerEvent) {
  if (!root.value) return;
  const box = root.value.getBoundingClientRect();
  const dx = event.clientX - (box.left + box.width / 2);
  const dy = event.clientY - (box.top + box.height / 2);
  const distance = Math.hypot(dx, dy) || 1;
  look.x = Math.round((dx / distance) * 9);
  look.y = Math.round((dy / distance) * 6);
  followUntil = Date.now() + 1500;
}

function say(line: BuddyLine, ms = 3800) {
  message.value = line;
  lastLine = line;
  later(() => {
    // Compare by text: the ref hands back a reactive proxy, never the original object.
    if (message.value?.en === line.en) message.value = null;
  }, ms);
}

// Every so often, pipe up with something (never the same line twice in a row).
function chatter() {
  if (!message.value) {
    const choices = LINES.filter((line) => line !== lastLine);
    say(choices[Math.floor(Math.random() * choices.length)]);
  }
  later(chatter, rand(9000, 15000));
}

function act(line: BuddyLine) {
  hapticTap();
  message.value = null;
  if (line.action === 'search') emit('search');
  if (line.action === 'agent') router.push('/agent');
}

function poke() {
  hapticTap();
  if (props.mini) {
    bouncing.value = true;
    happy.value = true;
    later(() => (happy.value = false), 1200);
    if (router.currentRoute.value.path !== '/agent') later(() => router.push('/agent'), 220);
    return;
  }
  say(LINES[1 + Math.floor(Math.random() * 2)], 3200);
  bouncing.value = true;
  happy.value = true;
  look.x = 0;
  look.y = 0;
  later(() => (happy.value = false), 1200);
}

const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

onMounted(() => {
  if (props.still) return;
  if (!props.mini) {
    later(() => !message.value && say(GREETING, 2600), 900);
    later(chatter, rand(7000, 10000));
  }
  if (reduceMotion) return;
  later(wander, 600);
  later(blink, 1800);
  window.addEventListener('pointermove', onPointerMove, { passive: true });
});

onBeforeUnmount(() => {
  timers.forEach((id) => window.clearTimeout(id));
  timers.clear();
  window.removeEventListener('pointermove', onPointerMove);
});
</script>

<style scoped>
.buddy-wrap {
  position: relative;
  width: 112px;
  margin: 0 auto 10px;
}

/* Mini: the same character drawn at about a third of the size */
.buddy-wrap.mini {
  width: 40px;
  height: 33px;
  margin: 0;
}

.buddy-wrap.mini .buddy {
  position: absolute;
  bottom: 0;
  left: 50%;
  margin-left: -56px;
  transform-origin: 50% 100%;
  scale: 0.36;
}

.buddy-wrap.still {
  pointer-events: none;
}

.buddy-wrap.still .buddy,
.buddy-wrap.still .buddy-glow,
.buddy-wrap.still .buddy-body {
  animation: none;
}

/* Cloud-shaped bubble to the upper right; the puffs and the cloud pop in one after another */
.buddy-bubble {
  position: absolute;
  z-index: 1;
  bottom: 62px;
  left: calc(100% - 40px);
  padding: 0;
  border: 0;
  background: transparent;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.cloud {
  display: block;
  width: max-content;
  white-space: nowrap;
  padding: 8px 12px;
  border-radius: 18px;
  /* Always a white cloud with dark text, in light and dark mode */
  background: #fff;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1);
  color: #000;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.3;
}

.puff {
  position: absolute;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.puff-1 {
  bottom: -16px;
  left: -2px;
  width: 7px;
  height: 7px;
}

.puff-2 {
  bottom: -8px;
  left: 6px;
  width: 11px;
  height: 11px;
}

.bubble-enter-active .puff-1 {
  animation: pop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}

.bubble-enter-active .puff-2 {
  animation: pop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) 0.12s both;
}

.bubble-enter-active .cloud {
  transform-origin: 0 100%;
  animation: pop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) 0.24s both;
}

.bubble-enter-active {
  transition: opacity 0.01s linear 0.7s;
}

.bubble-leave-active {
  transition:
    opacity 0.25s ease,
    transform 0.25s ease;
}

.bubble-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.92);
}

@keyframes pop {
  from {
    opacity: 0;
    transform: scale(0.3);
  }
}

.buddy {
  position: relative;
  display: grid;
  place-items: center;
  width: 112px;
  height: 92px;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  animation: buddy-float 4.2s ease-in-out infinite;
}

.buddy.bounce {
  animation: buddy-bounce 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* Soft halo that breathes with the body */
.buddy-glow {
  position: absolute;
  inset: 8px 4px;
  border-radius: 50%;
  background: radial-gradient(closest-side, rgba(10, 132, 255, 0.45), rgba(94, 92, 230, 0.2) 60%, transparent);
  filter: blur(14px);
  animation: buddy-breathe 3.6s ease-in-out infinite;
}

/* The ellipse itself: slowly morphing outline, gradient that drifts */
.buddy-body {
  position: relative;
  display: grid;
  place-items: center;
  width: 92px;
  height: 72px;
  overflow: hidden;
  border-radius: 50% 50% 48% 52% / 55% 52% 48% 45%;
  background: linear-gradient(135deg, #5ac8fa, #0a84ff 45%, #5e5ce6 80%, #bf5af2);
  background-size: 220% 220%;
  box-shadow:
    inset 0 -8px 16px rgba(30, 20, 120, 0.28),
    inset 0 6px 12px rgba(255, 255, 255, 0.35),
    0 10px 24px rgba(10, 132, 255, 0.3);
  transform: rotate(var(--tilt, 0deg));
  transition: transform 0.6s var(--ios-ease, ease);
  animation:
    buddy-morph 7s ease-in-out infinite,
    buddy-hue 9s ease-in-out infinite;
}

.buddy-shine {
  position: absolute;
  top: 9px;
  left: 18px;
  width: 26px;
  height: 12px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.45);
  filter: blur(3px);
  transform: rotate(-18deg);
}

.buddy-eyes {
  display: flex;
  gap: 16px;
  transition: transform 0.45s cubic-bezier(0.34, 1.3, 0.64, 1);
}

.buddy-eye {
  width: 11px;
  height: 20px;
  border-radius: 999px;
  background: #fff;
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.7);
  transform-origin: center;
  transition:
    transform 0.09s ease,
    height 0.2s ease,
    border-radius 0.2s ease;
}

.buddy-eye.shut {
  transform: scaleY(0.12);
}

/* Smiling eyes: little upside-down arcs */
.buddy-eye.happy {
  height: 9px;
  border-radius: 999px 999px 2px 2px;
}

@keyframes buddy-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-6px);
  }
}

@keyframes buddy-breathe {
  0%,
  100% {
    opacity: 0.75;
    transform: scale(0.95);
  }
  50% {
    opacity: 1;
    transform: scale(1.08);
  }
}

@keyframes buddy-morph {
  0%,
  100% {
    border-radius: 50% 50% 48% 52% / 55% 52% 48% 45%;
  }
  33% {
    border-radius: 54% 46% 52% 48% / 50% 56% 44% 50%;
  }
  66% {
    border-radius: 47% 53% 46% 54% / 56% 48% 52% 44%;
  }
}

@keyframes buddy-hue {
  0%,
  100% {
    background-position: 0% 30%;
  }
  50% {
    background-position: 100% 70%;
  }
}

@keyframes buddy-bounce {
  0% {
    transform: scale(1);
  }
  30% {
    transform: scale(1.12, 0.88);
  }
  60% {
    transform: scale(0.94, 1.08) translateY(-6px);
  }
  100% {
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .buddy,
  .buddy-glow,
  .buddy-body {
    animation: none;
  }
}
</style>
