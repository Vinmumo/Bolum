<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: String, required: true },
  sub: { type: String, default: null },
  accent: { type: String, default: "brand" }, // brand | win | draw | away
});
const ring = {
  brand: "text-brand-600 dark:text-brand-400",
  win: "text-win",
  draw: "text-draw",
  away: "text-away",
};
</script>

<template>
  <div class="card p-4">
    <p class="text-xs font-medium uppercase tracking-wide text-ink-400">{{ label }}</p>
    <p class="mt-1 text-2xl font-bold tabular-nums" :class="ring[accent]">{{ value }}</p>
    <p v-if="sub" class="mt-0.5 text-xs text-ink-500 dark:text-ink-400">{{ sub }}</p>
  </div>
</template>
