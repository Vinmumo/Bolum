<script setup>
import { onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useLeaguesStore } from "../stores/leagues";

const store = useLeaguesStore();
const { leagues, selectedId, loaded } = storeToRefs(store);

onMounted(() => {
  if (!store.loaded) store.fetch().catch(() => {});
});
</script>

<template>
  <div class="relative">
    <select
      v-if="loaded && leagues.length"
      :value="selectedId"
      class="input appearance-none pr-9 font-semibold"
      @change="store.select(Number($event.target.value))"
    >
      <option v-for="l in leagues" :key="l.id" :value="l.id">
        {{ l.name }}
      </option>
    </select>
    <div v-else class="skeleton h-9 w-40 rounded-xl" />
    <svg
      v-if="loaded && leagues.length"
      class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400"
      viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
    >
      <path stroke-linecap="round" stroke-linejoin="round" d="m6 9 6 6 6-6" />
    </svg>
  </div>
</template>
