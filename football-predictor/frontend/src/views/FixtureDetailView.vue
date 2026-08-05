<script setup>
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import client, { toUiError } from "../api/client";
import TeamBadge from "../components/TeamBadge.vue";
import ProbabilityBar from "../components/ProbabilityBar.vue";
import ScorelineList from "../components/ScorelineList.vue";
import StatTile from "../components/StatTile.vue";
import ErrorState from "../components/ErrorState.vue";
import SourceBreakdown from "../components/SourceBreakdown.vue";
import OverUnderPanel from "../components/OverUnderPanel.vue";

const route = useRoute();
const router = useRouter();

const data = ref(null);
const odds = ref(null);
const loading = ref(true);
const error = ref(null);

const homeName = computed(() => route.query.home);
const awayName = computed(() => route.query.away);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const body = { home: homeName.value, away: awayName.value };
    if (route.query.league) body.league_external_id = Number(route.query.league);
    if (route.query.season) body.season = Number(route.query.season);
    const res = await client.post("/predictions/predict", body);
    data.value = res.data;
    loadOdds(); // non-blocking; panel stays model-only if odds unavailable
  } catch (err) {
    error.value = toUiError(err);
  } finally {
    loading.value = false;
  }
}

async function loadOdds() {
  try {
    const params = { home: homeName.value, away: awayName.value };
    if (route.query.league) params.league_external_id = Number(route.query.league);
    const res = await client.get("/odds/totals", { params });
    odds.value = res.data;
  } catch {
    odds.value = null; // odds are a bonus — never surface an error for them
  }
}

const pct = (v) => `${Math.round(v * 100)}%`;
onMounted(load);

const p = computed(() => data.value?.consensus);
const sources = computed(() => data.value?.sources || []);
const sourceCount = computed(() => data.value?.meta?.source_count || 0);
const failed = computed(() => data.value?.meta?.providers_failed || []);
</script>

<template>
  <section>
    <button class="btn-ghost mb-5 -ml-2" @click="router.back()">
      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="m15 18-6-6 6-6" />
      </svg>
      Back
    </button>

    <!-- Loading -->
    <div v-if="loading" class="space-y-6">
      <div class="skeleton h-40 w-full rounded-2xl" />
      <div class="grid gap-4 sm:grid-cols-4">
        <div v-for="n in 4" :key="n" class="skeleton h-24 rounded-2xl" />
      </div>
      <div class="skeleton h-64 w-full rounded-2xl" />
    </div>

    <ErrorState v-else-if="error" :error="error" :on-retry="load" />

    <template v-else-if="data">
      <!-- Hero: teams + xG -->
      <div class="card p-6 sm:p-8">
        <div class="grid grid-cols-3 items-center gap-4">
          <div class="flex flex-col items-center gap-3 text-center">
            <TeamBadge :name="data.home_team.name" :logo="data.home_team.logo" size="lg" />
            <div>
              <p class="font-bold">{{ data.home_team.name }}</p>
              <p class="text-xs text-ink-400">Home</p>
            </div>
          </div>

          <div class="flex flex-col items-center">
            <p class="text-xs font-medium uppercase tracking-wide text-ink-400">
              {{ sourceCount > 1 ? "Consensus xG" : "Expected goals" }}
            </p>
            <p class="mt-1 text-4xl font-extrabold tabular-nums">
              <span class="text-win">{{ p.xg_home.toFixed(2) }}</span>
              <span class="mx-2 text-ink-300 dark:text-ink-600">–</span>
              <span class="text-away">{{ p.xg_away.toFixed(2) }}</span>
            </p>
          </div>

          <div class="flex flex-col items-center gap-3 text-center">
            <TeamBadge :name="data.away_team.name" :logo="data.away_team.logo" size="lg" />
            <div>
              <p class="font-bold">{{ data.away_team.name }}</p>
              <p class="text-xs text-ink-400">Away</p>
            </div>
          </div>
        </div>

        <div class="mt-8">
          <div class="mb-3 flex items-center justify-between">
            <p class="text-xs font-medium uppercase tracking-wide text-ink-400">Match result probability</p>
            <span
              v-if="sourceCount > 1"
              class="chip bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300"
            >Consensus · {{ sourceCount }} sources</span>
          </div>
          <ProbabilityBar
            :home="p.prob_home_win"
            :draw="p.prob_draw"
            :away="p.prob_away_win"
            :home-name="data.home_team.name"
            :away-name="data.away_team.name"
          />
        </div>
      </div>

      <!-- Overs/unders (multi-line, with market comparison when available) -->
      <div class="mt-6 grid items-start gap-4 lg:grid-cols-3">
        <div class="lg:col-span-2">
          <OverUnderPanel
            :over-lines="p.over_lines || { '2.5': p.prob_over_2_5 }"
            :expected-total="p.expected_total_goals"
            :market="odds"
          />
        </div>
        <div class="grid grid-cols-2 gap-4 lg:grid-cols-1">
          <StatTile label="Both teams score" :value="pct(p.prob_btts)" accent="draw" />
          <StatTile
            label="Most likely"
            :value="`${p.top_scorelines[0].home}–${p.top_scorelines[0].away}`"
            :sub="`${pct(p.top_scorelines[0].probability)} chance`"
            accent="win"
          />
        </div>
      </div>

      <!-- Scorelines + H2H -->
      <div class="mt-6 grid gap-6 lg:grid-cols-2">
        <div class="card p-6">
          <h2 class="mb-4 text-sm font-semibold uppercase tracking-wide text-ink-400">Likely scorelines</h2>
          <ScorelineList :scorelines="p.top_scorelines" />
        </div>

        <div class="card p-6">
          <h2 class="mb-4 text-sm font-semibold uppercase tracking-wide text-ink-400">Head to head</h2>
          <p class="text-sm leading-relaxed text-ink-600 dark:text-ink-300">{{ data.h2h.summary }}</p>
          <div v-if="data.h2h.played" class="mt-5 grid grid-cols-3 gap-2 text-center">
            <div>
              <p class="text-2xl font-bold tabular-nums text-win">{{ data.h2h.home_wins }}</p>
              <p class="text-xs text-ink-400">{{ data.home_team.name }}</p>
            </div>
            <div>
              <p class="text-2xl font-bold tabular-nums text-draw">{{ data.h2h.draws }}</p>
              <p class="text-xs text-ink-400">Draws</p>
            </div>
            <div>
              <p class="text-2xl font-bold tabular-nums text-away">{{ data.h2h.away_wins }}</p>
              <p class="text-xs text-ink-400">{{ data.away_team.name }}</p>
            </div>
          </div>

          <!-- recent form -->
          <div class="mt-6 space-y-2">
            <div class="flex items-center gap-3">
              <span class="w-28 truncate text-xs font-medium text-ink-500 dark:text-ink-400">{{ data.home_team.name }}</span>
              <div class="flex gap-1">
                <span v-for="(r, i) in data.form.home" :key="'h'+i"
                  class="flex h-6 w-6 items-center justify-center rounded text-[10px] font-bold text-white"
                  :class="{ 'bg-win': r==='W', 'bg-draw': r==='D', 'bg-away': r==='L' }">{{ r }}</span>
                <span v-if="!data.form.home.length" class="text-xs text-ink-400">no data</span>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <span class="w-28 truncate text-xs font-medium text-ink-500 dark:text-ink-400">{{ data.away_team.name }}</span>
              <div class="flex gap-1">
                <span v-for="(r, i) in data.form.away" :key="'a'+i"
                  class="flex h-6 w-6 items-center justify-center rounded text-[10px] font-bold text-white"
                  :class="{ 'bg-win': r==='W', 'bg-draw': r==='D', 'bg-away': r==='L' }">{{ r }}</span>
                <span v-if="!data.form.away.length" class="text-xs text-ink-400">no data</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Per-source comparison (always shown; averaging spans these) -->
      <div class="mt-6">
        <SourceBreakdown :sources="sources" :failed="failed" />
      </div>

      <p class="mt-6 text-center text-xs text-ink-400">
        Model: independent Poisson on attack/defence strengths, with light form &amp; H2H adjustments.
        Sources: {{ data.meta.providers_used.join(", ") || "—" }} · season {{ data.meta.season }}.
      </p>
    </template>
  </section>
</template>
