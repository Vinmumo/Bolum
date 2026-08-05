<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { RouterLink } from "vue-router";
import { storeToRefs } from "pinia";
import client, { toUiError } from "../api/client";
import { useLeaguesStore } from "../stores/leagues";
import { monthLabel, fmtDay } from "../utils/date";
import GameweekCard from "../components/GameweekCard.vue";
import ErrorState from "../components/ErrorState.vue";

const leaguesStore = useLeaguesStore();
const { selected } = storeToRefs(leaguesStore);

const rounds = ref([]);
const seasonsInfo = ref(null); // { current_season, past_seasons }
const loading = ref(true);
const error = ref(null);

// ---- Hero: the current/upcoming gameweek + season framing ----
const currentRound = computed(
  () => rounds.value.find((r) => r.is_current) || rounds.value[0] || null,
);
const seasonLabel = computed(() => {
  const y = seasonsInfo.value?.current_season;
  return y ? `${y}–${String(y + 1).slice(2)}` : "";
});
const daysToKickoff = computed(() => {
  if (!currentRound.value?.start_date) return null;
  const diff = new Date(currentRound.value.start_date) - new Date();
  return diff > 0 ? Math.ceil(diff / 86400000) : 0;
});

// Upcoming gameweeks only (the current one onwards), grouped by month.
const upcomingGrouped = computed(() => {
  const idx = rounds.value.findIndex((r) => r.is_current);
  const upcoming = idx >= 0 ? rounds.value.slice(idx) : rounds.value;
  const groups = [];
  let label = null;
  for (const r of upcoming) {
    const l = monthLabel(r.start_date);
    if (l !== label) {
      groups.push({ label: l, rounds: [] });
      label = l;
    }
    groups[groups.length - 1].rounds.push(r);
  }
  return groups;
});

const pastSeasons = computed(() => seasonsInfo.value?.past_seasons || []);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const params = {};
    if (selected.value) params.league_external_id = selected.value.external_provider_id;
    const [r, s] = await Promise.all([
      client.get("/fixtures/rounds", { params }),
      client.get("/leagues/seasons", { params }),
    ]);
    rounds.value = r.data;
    seasonsInfo.value = s.data;
  } catch (err) {
    error.value = toUiError(err);
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  if (!leaguesStore.loaded) {
    try {
      await leaguesStore.fetch();
    } catch (err) {
      error.value = toUiError(err);
    }
  }
  load();
});
watch(() => selected.value?.id, () => load());
</script>

<template>
  <section>
    <!-- Loading -->
    <div v-if="loading" class="space-y-4">
      <div class="skeleton h-40 w-full rounded-2xl" />
      <div class="grid gap-3 sm:grid-cols-2">
        <div v-for="n in 4" :key="n" class="skeleton h-[74px] rounded-2xl" />
      </div>
    </div>

    <ErrorState v-else-if="error" :error="error" :on-retry="load" />

    <template v-else>
      <!-- HERO: upcoming season front and centre -->
      <div class="card relative overflow-hidden p-6 sm:p-8">
        <div
          class="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-brand-500/10 blur-2xl"
        />
        <p class="text-xs font-semibold uppercase tracking-widest text-brand-600 dark:text-brand-400">
          {{ selected ? selected.name : "Season" }} · {{ seasonLabel }}
        </p>
        <h1 class="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">
          <template v-if="daysToKickoff > 0">
            New season kicks off in
            <span class="text-brand-600 dark:text-brand-400">{{ daysToKickoff }} day{{ daysToKickoff === 1 ? "" : "s" }}</span>
          </template>
          <template v-else>This gameweek</template>
        </h1>
        <p v-if="currentRound" class="mt-2 text-sm text-ink-500 dark:text-ink-400">
          {{ currentRound.name }} · starts {{ fmtDay(currentRound.start_date) }} ·
          {{ currentRound.fixture_count }} fixtures
        </p>
        <div class="mt-5 flex flex-wrap gap-2">
          <RouterLink
            v-if="currentRound"
            class="btn-primary"
            :to="{ name: 'gameweek', query: {
              round: currentRound.name,
              start: currentRound.start_date,
              end: currentRound.end_date,
              ...(selected ? { league: selected.external_provider_id, season: seasonsInfo.current_season } : {}),
            } }"
          >
            View {{ currentRound.name }} predictions →
          </RouterLink>
          <a href="#past-seasons" class="btn-ghost">Past seasons &amp; backtests</a>
        </div>
      </div>

      <!-- UPCOMING GAMEWEEKS -->
      <div class="mt-10">
        <h2 class="mb-1 text-xl font-extrabold tracking-tight">Upcoming gameweeks</h2>
        <p class="mb-5 text-sm text-ink-500 dark:text-ink-400">
          Pick a gameweek to see fixtures and Poisson predictions.
        </p>
        <div class="space-y-8">
          <div v-for="group in upcomingGrouped" :key="group.label">
            <h3 class="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-400">{{ group.label }}</h3>
            <div class="grid gap-3 sm:grid-cols-2">
              <GameweekCard v-for="r in group.rounds" :key="r.name" :round="r" />
            </div>
          </div>
        </div>
      </div>

      <!-- PAST SEASONS: stats + backtesting -->
      <div id="past-seasons" class="mt-12">
        <h2 class="mb-1 text-xl font-extrabold tracking-tight">Past seasons</h2>
        <p class="mb-5 text-sm text-ink-500 dark:text-ink-400">
          Final tables, plus gameweek replays: what Bolum <em>would have</em> predicted
          with only the data available at the time — scored against what actually happened.
        </p>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <RouterLink
            v-for="y in pastSeasons"
            :key="y"
            class="card group flex items-center justify-between p-5 transition hover:-translate-y-0.5 hover:shadow-lg"
            :to="{ name: 'season', params: { year: y } }"
          >
            <div>
              <p class="text-lg font-extrabold tracking-tight">{{ y }}–{{ String(y + 1).slice(2) }}</p>
              <p class="mt-0.5 text-xs text-ink-500 dark:text-ink-400">Stats · O/U backtest</p>
            </div>
            <svg class="h-5 w-5 text-ink-300 transition group-hover:translate-x-0.5 group-hover:text-brand-500 dark:text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m9 6 6 6-6 6" />
            </svg>
          </RouterLink>
        </div>
      </div>
    </template>
  </section>
</template>
