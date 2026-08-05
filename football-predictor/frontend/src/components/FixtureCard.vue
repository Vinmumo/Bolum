<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import TeamBadge from "./TeamBadge.vue";
import { fmtDay, fmtTime } from "../utils/date";

const props = defineProps({
  fixture: { type: Object, required: true },
});
const router = useRouter();

const kickoff = computed(() =>
  props.fixture.date ? `${fmtDay(props.fixture.date)} · ${fmtTime(props.fixture.date)}` : null,
);

function open() {
  router.push({
    name: "fixture",
    query: {
      home: props.fixture.home.name,
      away: props.fixture.away.name,
      league: props.fixture.league_id,
      season: props.fixture.season,
    },
  });
}
</script>

<template>
  <button
    class="card group w-full p-5 text-left transition hover:-translate-y-0.5 hover:shadow-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50"
    @click="open"
  >
    <div class="mb-4 flex items-center justify-between">
      <span class="chip bg-ink-100 text-ink-500 dark:bg-ink-800 dark:text-ink-400">
        {{ kickoff || fixture.round || "Fixture" }}
      </span>
      <span class="chip bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
        Predict →
      </span>
    </div>

    <div class="flex items-center justify-between gap-3">
      <div class="flex flex-1 flex-col items-center gap-2 text-center">
        <TeamBadge :name="fixture.home.name" :logo="fixture.home.logo" />
        <span class="line-clamp-2 text-sm font-semibold">{{ fixture.home.name }}</span>
      </div>

      <div class="flex flex-col items-center">
        <span class="text-xs font-bold text-ink-400">VS</span>
      </div>

      <div class="flex flex-1 flex-col items-center gap-2 text-center">
        <TeamBadge :name="fixture.away.name" :logo="fixture.away.logo" />
        <span class="line-clamp-2 text-sm font-semibold">{{ fixture.away.name }}</span>
      </div>
    </div>
  </button>
</template>
