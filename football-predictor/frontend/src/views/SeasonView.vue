<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import client, { toUiError } from "../api/client";
import { useLeaguesStore } from "../stores/leagues";
import ErrorState from "../components/ErrorState.vue";
import TeamBadge from "../components/TeamBadge.vue";

const route = useRoute();
const router = useRouter();
const leaguesStore = useLeaguesStore();
const { selected } = storeToRefs(leaguesStore);

const year = computed(() => Number(route.params.year));
const seasonLabel = computed(() => `${year.value}–${String(year.value + 1).slice(2)}`);

const standings = ref([]);
const summary = ref(null);
const rounds = ref([]);
const loading = ref(true);
const error = ref(null);

// replay state
const replay = ref(null); // payload of the selected gameweek replay
const replaying = ref(null); // matchday currently being computed
const replayError = ref(null);

const leagueParams = () =>
  selected.value ? { league_external_id: selected.value.external_provider_id } : {};

const matchdayCount = computed(() => rounds.value.length || 38);
const replayedSet = computed(() => new Set(summary.value?.matchdays_replayed || []));

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const params = { ...leagueParams(), season: year.value };
    const [st, sum, r] = await Promise.all([
      client.get("/leagues/standings", { params }),
      client.get("/backtest/summary", { params }),
      client.get("/fixtures/rounds", { params }),
    ]);
    standings.value = st.data;
    summary.value = sum.data;
    rounds.value = r.data;
  } catch (err) {
    error.value = toUiError(err);
  } finally {
    loading.value = false;
  }
}

async function runReplay(md) {
  replaying.value = md;
  replayError.value = null;
  try {
    const { data } = await client.get("/backtest/gameweek", {
      params: { ...leagueParams(), season: year.value, matchday: md },
    });
    replay.value = data;
    // refresh the aggregate after a new gameweek lands
    const { data: sum } = await client.get("/backtest/summary", {
      params: { ...leagueParams(), season: year.value },
    });
    summary.value = sum;
  } catch (err) {
    replayError.value = toUiError(err);
  } finally {
    replaying.value = null;
  }
}

const pct = (v) => (v == null ? "—" : `${Math.round(v * 100)}%`);

onMounted(async () => {
  if (!leaguesStore.loaded) await leaguesStore.fetch().catch(() => {});
  load();
});
watch(year, () => {
  replay.value = null;
  load();
});
</script>

<template>
  <section>
    <button class="btn-ghost mb-4 -ml-2" @click="router.push({ name: 'gameweeks' })">
      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="m15 18-6-6 6-6" />
      </svg>
      Home
    </button>

    <div class="mb-6">
      <p class="text-xs font-semibold uppercase tracking-widest text-brand-600 dark:text-brand-400">
        {{ selected ? selected.name : "" }} · past season
      </p>
      <h1 class="mt-1 text-3xl font-extrabold tracking-tight">Season {{ seasonLabel }}</h1>
    </div>

    <div v-if="loading" class="grid gap-6 lg:grid-cols-5">
      <div class="skeleton h-96 rounded-2xl lg:col-span-3" />
      <div class="skeleton h-96 rounded-2xl lg:col-span-2" />
    </div>

    <ErrorState v-else-if="error" :error="error" :on-retry="load" />

    <div v-else class="grid items-start gap-6 lg:grid-cols-5">
      <!-- STANDINGS -->
      <div class="card overflow-hidden lg:col-span-3">
        <h2 class="px-5 pb-2 pt-5 text-sm font-semibold uppercase tracking-wide text-ink-400">
          Final table
        </h2>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-ink-50 text-left text-xs uppercase text-ink-400 dark:bg-ink-950">
              <tr>
                <th class="px-3 py-2">#</th>
                <th class="px-3 py-2">Team</th>
                <th class="px-2 py-2 text-right">P</th>
                <th class="px-2 py-2 text-right">W</th>
                <th class="px-2 py-2 text-right">D</th>
                <th class="px-2 py-2 text-right">L</th>
                <th class="px-2 py-2 text-right">GF</th>
                <th class="px-2 py-2 text-right">GA</th>
                <th class="px-2 py-2 text-right">GD</th>
                <th class="px-3 py-2 text-right">Pts</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-ink-100 dark:divide-ink-800">
              <tr v-for="r in standings" :key="r.team_id">
                <td class="px-3 py-2 tabular-nums text-ink-400">{{ r.position }}</td>
                <td class="px-3 py-2">
                  <span class="flex items-center gap-2">
                    <TeamBadge :name="r.team_name" :logo="r.crest" size="sm" />
                    <span class="font-medium">{{ r.team_name }}</span>
                  </span>
                </td>
                <td class="px-2 py-2 text-right tabular-nums">{{ r.played }}</td>
                <td class="px-2 py-2 text-right tabular-nums">{{ r.won }}</td>
                <td class="px-2 py-2 text-right tabular-nums">{{ r.draw }}</td>
                <td class="px-2 py-2 text-right tabular-nums">{{ r.lost }}</td>
                <td class="px-2 py-2 text-right tabular-nums">{{ r.goals_for }}</td>
                <td class="px-2 py-2 text-right tabular-nums">{{ r.goals_against }}</td>
                <td class="px-2 py-2 text-right tabular-nums">{{ r.goal_difference }}</td>
                <td class="px-3 py-2 text-right font-bold tabular-nums">{{ r.points }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- BACKTEST PANEL -->
      <div class="space-y-6 lg:col-span-2">
        <!-- Season accuracy so far -->
        <div class="card p-5">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-ink-400">
            Backtest accuracy
          </h2>
          <p class="mt-1 text-xs text-ink-400">
            From {{ summary?.fixtures_backtested || 0 }} replayed fixtures
            ({{ (summary?.matchdays_replayed || []).length }} gameweeks). Predictions use only
            the table as it stood before each gameweek.
          </p>
          <div v-if="summary?.fixtures_backtested" class="mt-4 space-y-3">
            <div v-for="(s, line) in summary.over_under" :key="line" class="flex items-center gap-3">
              <span class="w-16 text-sm font-semibold">O/U {{ line }}</span>
              <div class="h-2.5 flex-1 overflow-hidden rounded-full bg-ink-100 dark:bg-ink-800">
                <div class="h-full rounded-full bg-brand-500" :style="{ width: pct(s.hit_rate) }" />
              </div>
              <span class="w-20 text-right text-sm tabular-nums text-ink-500 dark:text-ink-400">
                {{ s.hits }}/{{ s.count }} · {{ pct(s.hit_rate) }}
              </span>
            </div>
            <p class="pt-1 text-xs text-ink-400">
              1X2 result: {{ summary.result_1x2.hits }}/{{ summary.result_1x2.count }}
              ({{ pct(summary.result_1x2.hit_rate) }})
            </p>
          </div>
          <p v-else class="mt-4 text-sm text-ink-500 dark:text-ink-400">
            No gameweeks replayed yet — pick one below.
          </p>
        </div>

        <!-- Gameweek picker -->
        <div class="card p-5">
          <h2 class="mb-1 text-sm font-semibold uppercase tracking-wide text-ink-400">
            Replay a gameweek
          </h2>
          <p class="mb-3 text-xs text-ink-400">
            First replay of a gameweek makes live API calls (~20s); after that it's cached.
          </p>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="md in matchdayCount"
              :key="md"
              class="h-9 w-9 rounded-lg text-xs font-bold transition"
              :class="[
                replayedSet.has(md)
                  ? 'bg-brand-600 text-white dark:bg-brand-500 dark:text-ink-950'
                  : 'bg-ink-100 text-ink-600 hover:bg-ink-200 dark:bg-ink-800 dark:text-ink-300 dark:hover:bg-ink-700',
                replaying === md ? 'animate-pulse' : '',
              ]"
              :disabled="replaying !== null"
              @click="runReplay(md)"
            >
              {{ md }}
            </button>
          </div>
          <ErrorState v-if="replayError" :error="replayError" class="mt-4" />
        </div>

        <!-- Selected replay results -->
        <div v-if="replay" class="card p-5">
          <h2 class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-400">
            Gameweek {{ replay.matchday }} — what Bolum would have said
          </h2>
          <ul class="space-y-3">
            <li v-for="f in replay.fixtures" :key="f.home_team + f.away_team" class="text-sm">
              <div class="flex items-center justify-between gap-2">
                <span class="font-medium">
                  {{ f.home_team }} <span class="font-bold tabular-nums">{{ f.home_goals }}–{{ f.away_goals }}</span> {{ f.away_team }}
                </span>
                <span
                  class="chip shrink-0"
                  :class="f.lines['2.5'].hit
                    ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300'
                    : 'bg-away/10 text-away'"
                >
                  {{ f.lines['2.5'].hit ? "HIT" : "MISS" }}
                </span>
              </div>
              <p class="mt-0.5 text-xs text-ink-400">
                xG {{ f.xg_home.toFixed(2) }}–{{ f.xg_away.toFixed(2) }} ·
                picked <span class="font-semibold uppercase">{{ f.lines['2.5'].pick }} 2.5</span>
                ({{ Math.round(f.lines['2.5'].p_over * 100) }}% over) ·
                actual {{ f.home_goals + f.away_goals }} goals
              </p>
            </li>
          </ul>
          <p v-if="replay.skipped?.length" class="mt-3 text-xs text-ink-400">
            Skipped (no prior data): {{ replay.skipped.join(", ") }}
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
