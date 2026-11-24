<template>
  <div class="segmented" role="tablist" :style="{ '--segments': options.length, '--index': activeIndex }">
    <span class="segmented-thumb" aria-hidden="true" />
    <button
      v-for="option in options"
      :key="String(option.value)"
      type="button"
      role="tab"
      class="segmented-item"
      :class="{ on: option.value === modelValue }"
      :aria-selected="option.value === modelValue"
      @click="select(option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<script setup lang="ts" generic="T extends string | number">
// iOS segmented control: grey track, white sliding thumb.
import { computed } from 'vue';
import { hapticSelect } from '@/shared/lib/haptics';

const props = defineProps<{ modelValue: T; options: { label: string; value: T }[] }>();
const emit = defineEmits<{ 'update:modelValue': [value: T] }>();

const activeIndex = computed(() => Math.max(0, props.options.findIndex((option) => option.value === props.modelValue)));

function select(value: T) {
  if (value === props.modelValue) return;
  hapticSelect();
  emit('update:modelValue', value);
}
</script>

<style scoped>
.segmented {
  position: relative;
  display: grid;
  grid-template-columns: repeat(var(--segments), 1fr);
  padding: 2px;
  border-radius: 9px;
  background: var(--ios-fill-strong, rgba(118, 118, 128, 0.12));
}

.segmented-thumb {
  position: absolute;
  top: 2px;
  bottom: 2px;
  left: 2px;
  width: calc((100% - 4px) / var(--segments));
  border-radius: 7px;
  background: var(--ios-segment-thumb, #ffffff);
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12), 0 3px 1px rgba(0, 0, 0, 0.04);
  transform: translateX(calc(var(--index) * 100%));
  transition: transform 0.3s var(--ios-ease, cubic-bezier(0.32, 0.72, 0, 1));
}

.segmented-item {
  position: relative;
  z-index: 1;
  min-height: 30px;
  padding: 4px 8px;
  border: 0;
  background: transparent;
  color: var(--ios-label, #000);
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.segmented-item.on {
  font-weight: 600;
}
</style>
