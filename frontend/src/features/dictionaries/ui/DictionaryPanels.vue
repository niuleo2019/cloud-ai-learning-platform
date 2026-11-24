<template>
  <section v-if="loading || panels.length > 0 || showSetupHint" class="dictionary-panels">
    <div class="dictionary-panels-head">
      <h2>{{ t('dictionaries.panelTitle') }}</h2>
      <button type="button" class="dictionary-manage" @click="router.push('/settings/dictionaries')">
        <van-icon name="setting-o" /> {{ t('dictionaries.manage') }}
      </button>
    </div>

    <van-loading v-if="loading" size="20px" class="dictionary-loading">{{ t('dictionaries.searching') }}</van-loading>

    <p v-else-if="showSetupHint" class="dictionary-hint">{{ t('dictionaries.setupHint') }}</p>

    <p v-else-if="panels.length === 0" class="dictionary-hint">{{ t('dictionaries.notFound') }}</p>

    <article v-for="panel in panels" :key="panel.id" class="dictionary-card">
      <button type="button" class="dictionary-card-head" @click="toggle(panel.id)">
        <strong>{{ panel.title }}</strong>
        <van-icon :name="collapsed.has(panel.id) ? 'arrow-down' : 'arrow-up'" />
      </button>
      <DictionaryEntryFrame
        v-if="!collapsed.has(panel.id)"
        :entries="panel.entries || []"
        :resource-base="panel.resource_base || ''"
        :title="panel.title"
        @lookup="emit('lookup', $event)"
      />
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { lookupDictionariesApi, type DictionaryLookup } from '@/features/dictionaries/api/dictionaryLibraryApi';
import DictionaryEntryFrame from '@/features/dictionaries/ui/DictionaryEntryFrame.vue';
import { useSettingsStore } from '@/shared/model/settingsStore';

const props = defineProps<{ word: string }>();
const emit = defineEmits<{ (event: 'lookup', word: string): void }>();

const COLLAPSED_KEY = 'vocab.dictionaries.collapsed';

const router = useRouter();
const { t } = useSettingsStore();
const loading = ref(false);
const lookup = ref<DictionaryLookup | null>(null);
const collapsed = ref<Set<number>>(new Set(readCollapsed()));
let requestId = 0;

const panels = computed(() => (lookup.value?.results || []).filter((item) => item.found));
const showSetupHint = computed(() => !loading.value && lookup.value?.enabled_count === 0);

function readCollapsed(): number[] {
  try {
    return JSON.parse(localStorage.getItem(COLLAPSED_KEY) || '[]') as number[];
  } catch {
    return [];
  }
}

function toggle(id: number) {
  const next = new Set(collapsed.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  collapsed.value = next;
  try {
    localStorage.setItem(COLLAPSED_KEY, JSON.stringify([...next]));
  } catch {
    // Storage unavailable: the choice only lasts for this page view.
  }
}

watch(
  () => props.word,
  async (word) => {
    const current = ++requestId;
    if (!word.trim()) {
      lookup.value = null;
      return;
    }
    loading.value = true;
    try {
      const result = await lookupDictionariesApi(word.trim());
      if (current === requestId) lookup.value = result;
    } catch {
      if (current === requestId) lookup.value = null;
    } finally {
      if (current === requestId) loading.value = false;
    }
  },
  { immediate: true }
);
</script>

<style scoped>
.dictionary-panels {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.dictionary-panels-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px;
}

.dictionary-panels-head h2 {
  margin: 0;
  font-size: 17px;
  color: #0f172a;
}

.dictionary-manage {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 0;
  background: transparent;
  color: #2563eb;
  font-size: 13px;
}

.dictionary-loading {
  padding: 12px;
}

.dictionary-hint {
  margin: 0;
  padding: 12px 14px;
  border-radius: 14px;
  background: #ffffff;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.dictionary-card {
  overflow: hidden;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
}

.dictionary-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 10px 14px;
  border: 0;
  border-bottom: 1px solid #eef2f7;
  background: #f8fafc;
  color: #1e3a8a;
  font-size: 14px;
  text-align: left;
}
</style>

<style>
.theme-dark .dictionary-panels-head h2 {
  color: #f8fafc;
}

.theme-dark .dictionary-manage {
  color: #93c5fd;
}

.theme-dark .dictionary-hint {
  background: rgba(15, 23, 42, 0.82);
  color: #94a3b8;
}

.theme-dark .dictionary-card-head {
  border-bottom-color: #e2e8f0;
  background: #e2e8f0;
}
</style>
