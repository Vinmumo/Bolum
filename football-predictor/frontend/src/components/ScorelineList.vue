<script setup>
import { computed } from "vue";

const props = defineProps({
  scorelines: { type: Array, required: true }, // [{home, away, probability}]
});
const max = computed(() =>
  Math.max(...props.scorelines.map((s) => s.probability), 0.0001),
);
const pct = (v) => `${Math.round(v * 100)}%`;
</script>

<template>
  <ul class="space-y-2.5">
    <li v-for="(s, i) in scorelines" :key="i" class="flex items-center gap-3">
      <span class="w-12 text-sm font-bold tabular-nums">{{ s.home }}&ndash;{{ s.away }}</span>
      <div class="h-2.5 flex-1 overflow-hidden rounded-full bg-ink-100 dark:bg-ink-800">
        <div
          class="h-full rounded-full bg-brand-500 transition-all"
          :style="{ width: pct(s.probability / max) }"
        />
      </div>
      <span class="w-10 text-right text-sm text-ink-500 tabular-nums dark:text-ink-400">
        {{ pct(s.probability) }}
      </span>
    </li>
  </ul>
</template>
