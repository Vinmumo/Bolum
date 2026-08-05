<script setup>
// Friendly, differentiated error states. Rate-limit gets its own treatment
// because API-Football throttling is expected, not a bug.
defineProps({
  error: { type: Object, required: true }, // { kind, message }
  onRetry: { type: Function, default: null },
});
</script>

<template>
  <div class="card flex flex-col items-center gap-3 p-8 text-center">
    <div
      class="flex h-12 w-12 items-center justify-center rounded-full"
      :class="error.kind === 'rate_limit'
        ? 'bg-draw/15 text-draw'
        : 'bg-away/15 text-away'"
    >
      <svg v-if="error.kind === 'rate_limit'" class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="9" />
        <path stroke-linecap="round" d="M12 7v5l3 3" />
      </svg>
      <svg v-else class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" d="M12 8v5m0 3h.01M10.3 4.3 2.7 17.5A2 2 0 0 0 4.4 20.5h15.2a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0Z" />
      </svg>
    </div>
    <h3 class="text-base font-semibold">
      {{ error.kind === 'rate_limit' ? 'Rate limit reached' : 'Something went wrong' }}
    </h3>
    <p class="max-w-sm text-sm text-ink-500 dark:text-ink-400">{{ error.message }}</p>
    <button v-if="onRetry" class="btn-primary mt-1" @click="onRetry">Try again</button>
  </div>
</template>
