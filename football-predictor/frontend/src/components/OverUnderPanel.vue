<script setup>
// Overs/unders across goal lines: the model's probability, and — when The Odds
// API is configured & has this fixture — the bookmakers' margin-free implied
// probability with the model-vs-market edge.
import { computed } from "vue";

const props = defineProps({
  overLines: { type: Object, required: true }, // {"1.5": 0.78, ...}
  expectedTotal: { type: Number, default: null },
  market: { type: Object, default: null }, // odds endpoint payload or null
});

const pct = (v) => `${Math.round(v * 100)}%`;

const rows = computed(() =>
  Object.entries(props.overLines).map(([line, pOver]) => {
    const mkt = props.market?.lines?.[line] || null;
    const edge = mkt ? pOver - mkt.implied_p_over : null;
    return { line, pOver, mkt, edge };
  }),
);
const hasMarket = computed(() => props.market?.found && Object.keys(props.market.lines).length);
</script>

<template>
  <div class="card p-6">
    <div class="mb-1 flex items-center justify-between">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-ink-400">Overs / Unders</h2>
      <span v-if="expectedTotal" class="chip bg-ink-100 text-ink-500 dark:bg-ink-800 dark:text-ink-400">
        exp. total {{ expectedTotal.toFixed(1) }} goals
      </span>
    </div>
    <p class="mb-4 text-xs text-ink-400">
      <template v-if="hasMarket">Model vs bookmaker average ({{ Object.values(market.lines)[0]?.bookmaker_count }} books, margin removed).</template>
      <template v-else>Model probability that the match goes over each goal line.</template>
    </p>

    <div class="space-y-4">
      <div v-for="r in rows" :key="r.line">
        <div class="mb-1 flex items-baseline justify-between">
          <span class="text-sm font-bold">Over {{ r.line }}</span>
          <span class="text-sm tabular-nums">
            <span class="font-bold text-brand-600 dark:text-brand-400">{{ pct(r.pOver) }}</span>
            <template v-if="r.mkt">
              <span class="mx-1 text-ink-300 dark:text-ink-600">·</span>
              <span class="text-ink-500 dark:text-ink-400">market {{ pct(r.mkt.implied_p_over) }}</span>
              <span
                class="ml-1.5 font-semibold"
                :class="r.edge > 0.03 ? 'text-brand-600 dark:text-brand-400' : r.edge < -0.03 ? 'text-away' : 'text-ink-400'"
              >{{ r.edge > 0 ? "+" : "" }}{{ Math.round(r.edge * 100) }}%</span>
            </template>
          </span>
        </div>
        <!-- model bar with a market tick overlaid -->
        <div class="relative h-2.5 overflow-hidden rounded-full bg-ink-100 dark:bg-ink-800">
          <div class="h-full rounded-full bg-brand-500" :style="{ width: pct(r.pOver) }" />
          <div
            v-if="r.mkt"
            class="absolute top-0 h-full w-0.5 bg-ink-900 dark:bg-white"
            :style="{ left: pct(r.mkt.implied_p_over) }"
            :title="`Market: ${pct(r.mkt.implied_p_over)}`"
          />
        </div>
        <p v-if="r.mkt" class="mt-0.5 text-[11px] text-ink-400">
          avg odds: over {{ r.mkt.avg_over_odds }} / under {{ r.mkt.avg_under_odds }}
        </p>
      </div>
    </div>

    <p v-if="market && market.configured && !market.found" class="mt-4 text-xs text-ink-400">
      No bookmaker lines for this fixture yet (odds appear close to kick-off).
    </p>
  </div>
</template>
