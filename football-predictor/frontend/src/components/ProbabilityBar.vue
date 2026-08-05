<script setup>
import { computed } from "vue";

// Segmented W/D/L meter. Colors are the dataviz-validated trio (blue/amber/
// magenta). Each segment carries a direct % label (the required secondary
// encoding), so identity never rests on color alone.
const props = defineProps({
  home: { type: Number, required: true },
  draw: { type: Number, required: true },
  away: { type: Number, required: true },
  homeName: { type: String, default: "Home" },
  awayName: { type: String, default: "Away" },
});

const pct = (v) => `${Math.round(v * 100)}%`;
const segments = computed(() => [
  { key: "home", value: props.home, cls: "bg-win", label: props.homeName },
  { key: "draw", value: props.draw, cls: "bg-draw", label: "Draw" },
  { key: "away", value: props.away, cls: "bg-away", label: props.awayName },
]);
</script>

<template>
  <div>
    <!-- meter: 2px surface gaps between fills, rounded outer ends -->
    <div class="flex h-9 w-full gap-0.5 overflow-hidden rounded-lg" role="img"
         :aria-label="`Home win ${pct(home)}, draw ${pct(draw)}, away win ${pct(away)}`">
      <div
        v-for="s in segments"
        :key="s.key"
        class="flex items-center justify-center transition-all"
        :class="s.cls"
        :style="{ width: pct(s.value) }"
      >
        <span
          v-if="s.value > 0.08"
          class="px-1 text-xs font-bold text-white tabular-nums"
        >{{ pct(s.value) }}</span>
      </div>
    </div>

    <!-- legend: dot + label + value, in ink text (never series color) -->
    <div class="mt-3 grid grid-cols-3 gap-2 text-center">
      <div v-for="s in segments" :key="s.key" class="flex flex-col items-center">
        <div class="flex items-center gap-1.5">
          <span class="h-2.5 w-2.5 rounded-full" :class="s.cls" />
          <span class="text-xs font-medium text-ink-500 dark:text-ink-400 truncate max-w-[9rem]">
            {{ s.label }}
          </span>
        </div>
        <span class="mt-0.5 text-sm font-bold tabular-nums">{{ pct(s.value) }}</span>
      </div>
    </div>
  </div>
</template>
