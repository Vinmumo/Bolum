<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import { fmtRange } from "../utils/date";
import { useLeaguesStore } from "../stores/leagues";

const props = defineProps({
  round: { type: Object, required: true }, // { name, start_date, end_date, fixture_count, is_current }
});
const router = useRouter();
const leagues = useLeaguesStore();

const dateRange = computed(() => fmtRange(props.round.start_date, props.round.end_date));

function open() {
  const l = leagues.selected;
  router.push({
    name: "gameweek",
    query: {
      round: props.round.name,
      start: props.round.start_date,
      end: props.round.end_date,
      ...(l ? { league: l.external_provider_id, season: l.season } : {}),
    },
  });
}
</script>

<template>
  <button
    class="card group flex w-full items-center gap-4 p-4 text-left transition hover:-translate-y-0.5 hover:shadow-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50"
    :class="round.is_current ? 'ring-2 ring-brand-500/60' : ''"
    @click="open"
  >
    <!-- calendar-tile date -->
    <div class="flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-xl bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
      <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="4" width="18" height="17" rx="2" />
        <path stroke-linecap="round" d="M3 9h18M8 2v4M16 2v4" />
      </svg>
    </div>

    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-2">
        <span class="font-bold">{{ round.name }}</span>
        <span v-if="round.is_current" class="chip bg-brand-600 text-white dark:bg-brand-500 dark:text-ink-950">Current</span>
      </div>
      <p class="mt-0.5 text-sm text-ink-500 dark:text-ink-400">{{ dateRange }}</p>
    </div>

    <div class="shrink-0 text-right">
      <p class="text-sm font-semibold tabular-nums">{{ round.fixture_count }}</p>
      <p class="text-xs text-ink-400">matches</p>
    </div>

    <svg class="h-5 w-5 shrink-0 text-ink-300 transition group-hover:translate-x-0.5 group-hover:text-brand-500 dark:text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path stroke-linecap="round" stroke-linejoin="round" d="m9 6 6 6-6 6" />
    </svg>
  </button>
</template>
