<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import client, { toUiError } from "../api/client";
import { fmtRange } from "../utils/date";
import FixtureCard from "../components/FixtureCard.vue";
import SkeletonCard from "../components/SkeletonCard.vue";
import ErrorState from "../components/ErrorState.vue";

const route = useRoute();
const router = useRouter();

const fixtures = ref([]);
const loading = ref(true);
const error = ref(null);

const roundName = computed(() => route.query.round || "Gameweek");
const dateRange = computed(() => fmtRange(route.query.start, route.query.end));

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const params = { round: route.query.round };
    if (route.query.league) params.league_external_id = Number(route.query.league);
    if (route.query.season) params.season = Number(route.query.season);
    const { data } = await client.get("/fixtures", { params });
    fixtures.value = data;
  } catch (err) {
    error.value = toUiError(err);
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(() => route.query.round, () => load());
</script>

<template>
  <section>
    <button class="btn-ghost mb-4 -ml-2" @click="router.push({ name: 'gameweeks' })">
      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="m15 18-6-6 6-6" />
      </svg>
      All gameweeks
    </button>

    <div class="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-extrabold tracking-tight sm:text-3xl">{{ roundName }}</h1>
        <p class="mt-1 text-sm text-ink-500 dark:text-ink-400">
          {{ dateRange }} — tap a fixture for a full Poisson breakdown.
        </p>
      </div>
      <span v-if="!loading && !error" class="chip bg-ink-100 text-ink-500 dark:bg-ink-800 dark:text-ink-400">
        {{ fixtures.length }} fixtures
      </span>
    </div>

    <div v-if="loading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <SkeletonCard v-for="n in 5" :key="n" />
    </div>

    <ErrorState v-else-if="error" :error="error" :on-retry="load" />

    <div v-else-if="fixtures.length" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <FixtureCard v-for="f in fixtures" :key="f.id" :fixture="f" />
    </div>

    <div v-else class="card p-10 text-center text-sm text-ink-500 dark:text-ink-400">
      No fixtures found for this gameweek.
    </div>
  </section>
</template>
