<script setup>
// Per-API comparison: each source's expected goals + a compact W/D/L bar, so
// you can see where the APIs agree/disagree and judge which looks most accurate.
defineProps({
  sources: { type: Array, required: true }, // [{ provider, prediction, ... }]
  failed: { type: Array, default: () => [] }, // [{ provider, reason }]
});
const pct = (v) => `${Math.round(v * 100)}%`;
</script>

<template>
  <div class="card p-6">
    <h2 class="mb-1 text-sm font-semibold uppercase tracking-wide text-ink-400">By data source</h2>
    <p class="mb-4 text-xs text-ink-400">
      The headline is the average of these. Compare them to spot disagreement.
    </p>

    <ul class="space-y-4">
      <li v-for="s in sources" :key="s.provider">
        <div class="mb-1.5 flex items-center justify-between gap-3">
          <span class="truncate text-sm font-semibold">{{ s.provider }}</span>
          <span class="shrink-0 text-sm tabular-nums text-ink-500 dark:text-ink-400">
            xG <span class="font-bold text-win">{{ s.prediction.xg_home.toFixed(2) }}</span>
            &ndash;
            <span class="font-bold text-away">{{ s.prediction.xg_away.toFixed(2) }}</span>
          </span>
        </div>
        <!-- compact W/D/L bar, labelled so identity isn't color-only -->
        <div class="flex h-6 w-full gap-0.5 overflow-hidden rounded-md">
          <div class="flex items-center justify-center bg-win" :style="{ width: pct(s.prediction.prob_home_win) }">
            <span v-if="s.prediction.prob_home_win > 0.12" class="text-[10px] font-bold text-white">{{ pct(s.prediction.prob_home_win) }}</span>
          </div>
          <div class="flex items-center justify-center bg-draw" :style="{ width: pct(s.prediction.prob_draw) }">
            <span v-if="s.prediction.prob_draw > 0.12" class="text-[10px] font-bold text-white">{{ pct(s.prediction.prob_draw) }}</span>
          </div>
          <div class="flex items-center justify-center bg-away" :style="{ width: pct(s.prediction.prob_away_win) }">
            <span v-if="s.prediction.prob_away_win > 0.12" class="text-[10px] font-bold text-white">{{ pct(s.prediction.prob_away_win) }}</span>
          </div>
        </div>
      </li>
    </ul>

    <div v-if="failed.length" class="mt-4 border-t border-ink-100 pt-3 dark:border-ink-800">
      <p class="text-xs text-ink-400">
        Skipped:
        <span v-for="(f, i) in failed" :key="f.provider">
          <span class="font-medium text-ink-500 dark:text-ink-400">{{ f.provider }}</span><span v-if="i < failed.length - 1">, </span>
        </span>
      </p>
    </div>
  </div>
</template>
