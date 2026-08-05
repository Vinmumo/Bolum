<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { storeToRefs } from "pinia";
import client, { toUiError } from "../api/client";
import { useLeaguesStore } from "../stores/leagues";
import { monthLabel } from "../utils/date";
import GameweekCard from "../components/GameweekCard.vue";
import ErrorState from "../components/ErrorState.vue";

const leaguesStore = useLeaguesStore();
const { selected } = storeToRefs(leaguesStore);

const rounds = ref([]);
const loading = ref(true);
const error = ref(null);

// Group gameweeks under a month heading for a calendar feel.
const grouped = computed(() => {
  const groups = [];
  let currentLabel = null;
  for (const r of rounds.value) {
    const label = monthLabel(r.start_date);
    if (label !== currentLabel) {
      groups.push({ label, rounds: [] });
      currentLabel = label;
    }
    groups[groups.length - 1].rounds.push(r);
  }
  return groups;
});

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const params = {};
    if (selected.value) {
      params.league_external_id = selected.value.external_provider_id;
      params.season = selected.value.season;
    }
    const { data } = await client.get("/fixtures/rounds", { params });
    rounds.value = data;
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
    <div class="mb-6">
      <h1 class="text-2xl font-extrabold tracking-tight sm:text-3xl">Fixtures calendar</h1>
      <p class="mt-1 text-sm text-ink-500 dark:text-ink-400">
        {{ selected ? selected.name : "" }} — pick a gameweek to see its matches and predictions.
      </p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <div v-for="n in 6" :key="n" class="skeleton h-[74px] w-full rounded-2xl" />
    </div>

    <ErrorState v-else-if="error" :error="error" :on-retry="load" />

    <!-- Gameweeks grouped by month -->
    <div v-else-if="rounds.length" class="space-y-8">
      <div v-for="group in grouped" :key="group.label">
        <h2 class="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-400">{{ group.label }}</h2>
        <div class="grid gap-3 sm:grid-cols-2">
          <GameweekCard v-for="r in group.rounds" :key="r.name" :round="r" />
        </div>
      </div>
    </div>

    <div v-else class="card p-10 text-center text-sm text-ink-500 dark:text-ink-400">
      No gameweeks found for this league yet.
    </div>
  </section>
</template>
