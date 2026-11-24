<template>
  <iframe
    ref="frameRef"
    class="dictionary-frame"
    :style="{ height: `${height}px` }"
    :srcdoc="srcdoc"
    sandbox="allow-scripts allow-popups"
    :title="title"
    loading="lazy"
  />
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { showFailToast } from 'vant';
import { API_BASE_URL } from '@/shared/api/config';
import { openInAppBrowser } from '@/shared/lib/inAppBrowser';

/**
 * Renders MDict entry HTML the way desktop dictionary apps do, inside a sandboxed iframe:
 * - the dictionary's own CSS/JS cannot touch the app (opaque origin, no same-origin access);
 * - relative css/img/js URLs resolve against the signed resource URL via <base>;
 * - sound:// and entry:// links are forwarded to this component with postMessage.
 */
const props = defineProps<{
  entries: string[];
  resourceBase: string;
  title: string;
}>();

const emit = defineEmits<{ (event: 'lookup', word: string): void }>();

const frameRef = ref<HTMLIFrameElement | null>(null);
const height = ref(160);
const frameId = Math.random().toString(36).slice(2);
const baseUrl = new URL(`${API_BASE_URL}${props.resourceBase}`, window.location.href).href;

// Runs inside the iframe. Kept as plain ES5 so old Android WebViews accept it.
const bridge = `
(function () {
  var id = ${JSON.stringify(frameId)};
  function post(message) { message.__dict = id; parent.postMessage(message, '*'); }
  document.addEventListener('click', function (event) {
    var node = event.target;
    while (node && node.tagName !== 'A') node = node.parentElement;
    if (!node) return;
    var href = node.getAttribute('href') || '';
    if (/^sound:\\/\\//i.test(href)) {
      event.preventDefault();
      post({ type: 'sound', path: href.replace(/^sound:\\/\\/+/i, '') });
    } else if (/^(entry|bword):\\/\\//i.test(href)) {
      event.preventDefault();
      var target = href.replace(/^(entry|bword):\\/\\/+/i, '');
      if (target.charAt(0) === '#') {
        var el = document.getElementById(target.slice(1)) || document.getElementsByName(target.slice(1))[0];
        if (el) el.scrollIntoView();
        return;
      }
      try { target = decodeURIComponent(target); } catch (e) {}
      post({ type: 'entry', word: target });
    } else if (/^https?:/i.test(href)) {
      event.preventDefault();
      post({ type: 'open', url: node.href });
    }
  }, true);
  function size() { post({ type: 'height', height: Math.max(document.documentElement.scrollHeight, document.body.scrollHeight) }); }
  if (window.ResizeObserver) new ResizeObserver(size).observe(document.body);
  window.addEventListener('load', size);
  setTimeout(size, 50); setTimeout(size, 600);
})();`;

const srcdoc = computed(
  () => `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<base href="${baseUrl}">
<style>
html, body { margin: 0; background: #ffffff; color: #111827; overflow: hidden;
  -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
body { padding: 10px 12px; font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", sans-serif;
  overflow-wrap: anywhere; overflow-x: hidden; }
img { max-width: 100%; height: auto; }
table { max-width: 100%; }
hr.dictionary-entry-split { margin: 14px 0; border: 0; border-top: 1px dashed #cbd5e1; }
</style></head><body>${props.entries.join('<hr class="dictionary-entry-split">')}<script>${bridge}<\/script></body></html>`
);

let player: HTMLAudioElement | null = null;

function onMessage(event: MessageEvent) {
  const data = event.data as { __dict?: string; type?: string; path?: string; word?: string; url?: string; height?: number };
  if (!data || data.__dict !== frameId || event.source !== frameRef.value?.contentWindow) return;
  if (data.type === 'height' && typeof data.height === 'number') {
    height.value = Math.min(Math.max(Math.ceil(data.height) + 2, 60), 20000);
  } else if (data.type === 'sound' && data.path) {
    player?.pause();
    player = new Audio(new URL(data.path.replace(/\\/g, '/'), baseUrl).href);
    player.play().catch(() => showFailToast('Audio unavailable'));
  } else if (data.type === 'entry' && data.word) {
    emit('lookup', data.word.trim());
  } else if (data.type === 'open' && data.url && /^https?:/i.test(data.url)) {
    openInAppBrowser(data.url);
  }
}

onMounted(() => window.addEventListener('message', onMessage));
onBeforeUnmount(() => {
  window.removeEventListener('message', onMessage);
  player?.pause();
});
</script>

<style scoped>
.dictionary-frame {
  display: block;
  width: 100%;
  border: 0;
  border-radius: 0 0 14px 14px;
  background: #ffffff;
}
</style>
