<script setup>
import { ref, onMounted } from "vue";
import client, { toUiError } from "../../api/client";
import ErrorState from "../../components/ErrorState.vue";

const tabs = ["Providers", "Leagues", "Usage", "Predictions"];
const tab = ref("Providers");

const providers = ref([]);
const leagues = ref([]);
const usage = ref([]);
const predictions = ref([]);
const providerTypes = ref([]);
const error = ref(null);

// Sensible base URL + auth header per provider type (prefilled on select).
const PROVIDER_DEFAULTS = {
  api_football: { base_url: "https://v3.football.api-sports.io", auth_header: "x-apisports-key" },
  football_data_org: { base_url: "https://api.football-data.org/v4", auth_header: "X-Auth-Token" },
  sportmonks: { base_url: "https://api.sportmonks.com/v3/football", auth_header: "Authorization" },
  sportradar: { base_url: "https://api.sportradar.com/soccer/trial/v4/en", auth_header: "x-api-key" },
  sample: { base_url: "local://sample", auth_header: "x-apisports-key" },
};

const blankProvider = () => ({
  name: "", provider_type: "api_football", base_url: "https://v3.football.api-sports.io",
  auth_header: "x-apisports-key", api_key: "", active: true,
});
const blankLeague = () => ({ name: "", country: "", external_provider_id: 39, season: 2023, active: true });

const providerForm = ref(null); // null=closed, {} = new/edit
const leagueForm = ref(null);

async function refresh() {
  error.value = null;
  try {
    const [p, l, u, pr, pt] = await Promise.all([
      client.get("/admin/providers"),
      client.get("/admin/leagues"),
      client.get("/admin/usage"),
      client.get("/admin/predictions"),
      client.get("/admin/provider-types"),
    ]);
    providers.value = p.data;
    leagues.value = l.data;
    usage.value = u.data;
    predictions.value = pr.data;
    providerTypes.value = pt.data.types;
  } catch (err) {
    error.value = toUiError(err);
  }
}
onMounted(refresh);

// ---- Providers ----
function newProvider() { providerForm.value = { ...blankProvider(), id: null }; }
function onProviderTypeChange() {
  const d = PROVIDER_DEFAULTS[providerForm.value.provider_type];
  if (d) {
    providerForm.value.base_url = d.base_url;
    providerForm.value.auth_header = d.auth_header;
  }
}
function editProvider(p) { providerForm.value = { ...p, api_key: "" }; }
async function saveProvider() {
  const f = providerForm.value;
  const payload = { ...f };
  if (!payload.api_key) delete payload.api_key; // don't overwrite key with blank
  try {
    if (f.id) await client.put(`/admin/providers/${f.id}`, payload);
    else await client.post("/admin/providers", payload);
    providerForm.value = null;
    refresh();
  } catch (err) { error.value = toUiError(err); }
}
async function toggleProvider(p) {
  await client.put(`/admin/providers/${p.id}`, { active: !p.active });
  refresh();
}
async function deleteProvider(p) {
  if (!confirm(`Delete provider "${p.name}"?`)) return;
  await client.delete(`/admin/providers/${p.id}`);
  refresh();
}

// ---- Leagues ----
function newLeague() { leagueForm.value = { ...blankLeague(), id: null }; }
function editLeague(l) { leagueForm.value = { ...l }; }
async function saveLeague() {
  const f = leagueForm.value;
  try {
    if (f.id) await client.put(`/admin/leagues/${f.id}`, f);
    else await client.post("/admin/leagues", f);
    leagueForm.value = null;
    refresh();
  } catch (err) { error.value = toUiError(err); }
}
async function toggleLeague(l) {
  await client.put(`/admin/leagues/${l.id}`, { active: !l.active });
  refresh();
}
async function deleteLeague(l) {
  if (!confirm(`Delete league "${l.name}"?`)) return;
  await client.delete(`/admin/leagues/${l.id}`);
  refresh();
}
</script>

<template>
  <section>
    <h1 class="mb-6 text-2xl font-extrabold tracking-tight">Admin</h1>

    <div class="mb-6 flex flex-wrap gap-1 rounded-xl bg-ink-100 p-1 dark:bg-ink-900 sm:inline-flex">
      <button v-for="t in tabs" :key="t"
        class="rounded-lg px-4 py-1.5 text-sm font-semibold transition"
        :class="tab === t ? 'bg-white text-ink-900 shadow-card dark:bg-ink-700 dark:text-white' : 'text-ink-500 hover:text-ink-800 dark:hover:text-ink-200'"
        @click="tab = t">{{ t }}</button>
    </div>

    <ErrorState v-if="error" :error="error" :on-retry="refresh" class="mb-6" />

    <!-- PROVIDERS -->
    <div v-show="tab === 'Providers'" class="space-y-4">
      <div class="flex items-center justify-between">
        <p class="max-w-xl text-sm text-ink-500 dark:text-ink-400">Every <span class="font-medium">active</span> provider is averaged into the consensus prediction. The first active one also serves fixtures &amp; the calendar. Enable two (e.g. API-Football + football-data.org) to get a real multi-source average.</p>
        <button class="btn-primary" @click="newProvider">+ Add provider</button>
      </div>

      <div v-if="providerForm" class="card space-y-3 p-5">
        <h3 class="font-semibold">{{ providerForm.id ? "Edit" : "New" }} provider</h3>
        <div class="grid gap-3 sm:grid-cols-2">
          <label class="text-sm">Name<input v-model="providerForm.name" class="input mt-1" /></label>
          <label class="text-sm">Type
            <select v-model="providerForm.provider_type" class="input mt-1" @change="onProviderTypeChange">
              <option v-for="t in providerTypes" :key="t" :value="t">{{ t }}</option>
            </select>
          </label>
          <label class="text-sm sm:col-span-2">Base URL<input v-model="providerForm.base_url" class="input mt-1" /></label>
          <label class="text-sm">Auth header<input v-model="providerForm.auth_header" class="input mt-1" /></label>
          <label class="text-sm">API key
            <input v-model="providerForm.api_key" type="password" class="input mt-1"
              :placeholder="providerForm.id ? 'leave blank to keep current' : ''" />
          </label>
        </div>
        <label class="flex items-center gap-2 text-sm"><input v-model="providerForm.active" type="checkbox" /> Active</label>
        <div class="flex gap-2">
          <button class="btn-primary" @click="saveProvider">Save</button>
          <button class="btn-ghost" @click="providerForm = null">Cancel</button>
        </div>
      </div>

      <div class="card divide-y divide-ink-100 dark:divide-ink-800">
        <div v-for="p in providers" :key="p.id" class="flex flex-wrap items-center justify-between gap-3 p-4">
          <div>
            <div class="flex items-center gap-2">
              <span class="font-semibold">{{ p.name }}</span>
              <span class="chip" :class="p.active ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300' : 'bg-ink-100 text-ink-400 dark:bg-ink-800'">
                {{ p.active ? "active" : "disabled" }}
              </span>
            </div>
            <p class="text-xs text-ink-400">{{ p.provider_type }} · {{ p.base_url }} · key {{ p.has_key ? p.api_key_masked : "—" }}</p>
          </div>
          <div class="flex gap-1">
            <button class="btn-ghost !px-2 text-xs" @click="toggleProvider(p)">{{ p.active ? "Disable" : "Enable" }}</button>
            <button class="btn-ghost !px-2 text-xs" @click="editProvider(p)">Edit</button>
            <button class="btn-ghost !px-2 text-xs text-away" @click="deleteProvider(p)">Delete</button>
          </div>
        </div>
      </div>
    </div>

    <!-- LEAGUES -->
    <div v-show="tab === 'Leagues'" class="space-y-4">
      <div class="flex items-center justify-between">
        <p class="text-sm text-ink-500 dark:text-ink-400">Enable La Liga, Serie A, etc. without a code change.</p>
        <button class="btn-primary" @click="newLeague">+ Add league</button>
      </div>

      <div v-if="leagueForm" class="card space-y-3 p-5">
        <h3 class="font-semibold">{{ leagueForm.id ? "Edit" : "New" }} league</h3>
        <div class="grid gap-3 sm:grid-cols-2">
          <label class="text-sm">Name<input v-model="leagueForm.name" class="input mt-1" /></label>
          <label class="text-sm">Country<input v-model="leagueForm.country" class="input mt-1" /></label>
          <label class="text-sm">Provider league id<input v-model.number="leagueForm.external_provider_id" type="number" class="input mt-1" /></label>
          <label class="text-sm">Season<input v-model.number="leagueForm.season" type="number" class="input mt-1" /></label>
        </div>
        <label class="flex items-center gap-2 text-sm"><input v-model="leagueForm.active" type="checkbox" /> Active</label>
        <div class="flex gap-2">
          <button class="btn-primary" @click="saveLeague">Save</button>
          <button class="btn-ghost" @click="leagueForm = null">Cancel</button>
        </div>
      </div>

      <div class="card divide-y divide-ink-100 dark:divide-ink-800">
        <div v-for="l in leagues" :key="l.id" class="flex flex-wrap items-center justify-between gap-3 p-4">
          <div>
            <div class="flex items-center gap-2">
              <span class="font-semibold">{{ l.name }}</span>
              <span class="chip" :class="l.active ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300' : 'bg-ink-100 text-ink-400 dark:bg-ink-800'">
                {{ l.active ? "active" : "disabled" }}
              </span>
            </div>
            <p class="text-xs text-ink-400">{{ l.country }} · provider id {{ l.external_provider_id }} · season {{ l.season }}</p>
          </div>
          <div class="flex gap-1">
            <button class="btn-ghost !px-2 text-xs" @click="toggleLeague(l)">{{ l.active ? "Disable" : "Enable" }}</button>
            <button class="btn-ghost !px-2 text-xs" @click="editLeague(l)">Edit</button>
            <button class="btn-ghost !px-2 text-xs text-away" @click="deleteLeague(l)">Delete</button>
          </div>
        </div>
      </div>
    </div>

    <!-- USAGE -->
    <div v-show="tab === 'Usage'">
      <p class="mb-4 text-sm text-ink-500 dark:text-ink-400">Outbound API calls per provider (cache hits are not counted). Watch your quota here.</p>
      <div class="card overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-ink-50 text-left text-xs uppercase text-ink-400 dark:bg-ink-950">
            <tr><th class="px-4 py-3">Provider</th><th class="px-4 py-3 text-right">Total</th><th class="px-4 py-3 text-right">OK</th><th class="px-4 py-3 text-right">Failed</th></tr>
          </thead>
          <tbody class="divide-y divide-ink-100 dark:divide-ink-800">
            <tr v-for="u in usage" :key="u.provider_id">
              <td class="px-4 py-3 font-medium">{{ u.provider_name }}</td>
              <td class="px-4 py-3 text-right tabular-nums">{{ u.total_calls }}</td>
              <td class="px-4 py-3 text-right tabular-nums text-brand-600 dark:text-brand-400">{{ u.successful }}</td>
              <td class="px-4 py-3 text-right tabular-nums text-away">{{ u.failed }}</td>
            </tr>
            <tr v-if="!usage.length"><td colspan="4" class="px-4 py-6 text-center text-ink-400">No calls logged yet.</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- PREDICTIONS -->
    <div v-show="tab === 'Predictions'">
      <p class="mb-4 text-sm text-ink-500 dark:text-ink-400">Recent predictions the model has produced.</p>
      <div class="card overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-ink-50 text-left text-xs uppercase text-ink-400 dark:bg-ink-950">
            <tr><th class="px-4 py-3">Fixture</th><th class="px-4 py-3 text-right">xG</th><th class="px-4 py-3 text-right">H / D / A</th><th class="px-4 py-3">When</th></tr>
          </thead>
          <tbody class="divide-y divide-ink-100 dark:divide-ink-800">
            <tr v-for="r in predictions" :key="r.id">
              <td class="px-4 py-3 font-medium">{{ r.home_team }} vs {{ r.away_team }}</td>
              <td class="px-4 py-3 text-right tabular-nums">{{ r.xg_home.toFixed(2) }}–{{ r.xg_away.toFixed(2) }}</td>
              <td class="px-4 py-3 text-right tabular-nums">
                {{ Math.round(r.prob_home*100) }}/{{ Math.round(r.prob_draw*100) }}/{{ Math.round(r.prob_away*100) }}
              </td>
              <td class="px-4 py-3 text-ink-400">{{ new Date(r.created_at).toLocaleString() }}</td>
            </tr>
            <tr v-if="!predictions.length"><td colspan="4" class="px-4 py-6 text-center text-ink-400">No predictions yet.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
