<script setup>
import { computed } from "vue";

const props = defineProps({
  name: { type: String, required: true },
  logo: { type: String, default: null },
  size: { type: String, default: "md" }, // sm | md | lg
});

const initials = computed(() =>
  props.name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase(),
);

const sizeClass = computed(
  () =>
    ({
      sm: "h-8 w-8 text-xs",
      md: "h-11 w-11 text-sm",
      lg: "h-16 w-16 text-lg",
    })[props.size],
);
</script>

<template>
  <div
    class="flex shrink-0 items-center justify-center rounded-full font-bold"
    :class="[sizeClass, logo ? 'bg-white dark:bg-ink-800' : 'bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300']"
  >
    <img v-if="logo" :src="logo" :alt="name" class="h-3/4 w-3/4 object-contain" />
    <span v-else>{{ initials }}</span>
  </div>
</template>
