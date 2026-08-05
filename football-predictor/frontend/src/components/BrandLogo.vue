<script setup>
import { computed } from "vue";

const props = defineProps({
  size: { type: String, default: "md" }, // sm | md | lg
  showWord: { type: Boolean, default: true },
});

const badge = computed(
  () =>
    ({
      sm: "h-8 w-8 rounded-lg",
      md: "h-9 w-9 rounded-xl",
      lg: "h-11 w-11 rounded-2xl",
    })[props.size],
);
const word = computed(
  () => ({ sm: "text-base", md: "text-lg", lg: "text-2xl" })[props.size],
);
</script>

<template>
  <span class="flex items-center gap-2.5">
    <!-- Bolum mark: a green badge with a stylised football/monogram -->
    <span
      class="relative flex items-center justify-center bg-brand-600 text-white shadow-card dark:bg-brand-500 dark:text-ink-950"
      :class="badge"
    >
      <svg class="h-2/3 w-2/3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" aria-hidden="true">
        <circle cx="12" cy="12" r="9" />
        <path stroke-linejoin="round" d="m12 6.5 3.3 2.4-1.25 3.9H9.95L8.7 8.9 12 6.5Z" />
        <path stroke-linecap="round" d="M12 3v1.6M12 19.4V21M4.6 8.5l1.5.6M17.9 14.9l1.5.6M19.4 8.5l-1.5.6M6.1 14.9l-1.5.6" />
      </svg>
      <span
        class="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-brand-300 ring-2 ring-ink-50 dark:bg-brand-400 dark:ring-ink-950"
      />
    </span>
    <span v-if="showWord" class="font-extrabold tracking-tight" :class="word">
      Bolum
    </span>
  </span>
</template>
