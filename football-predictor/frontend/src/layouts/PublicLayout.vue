<script setup>
import { RouterLink, RouterView } from "vue-router";
import ThemeToggle from "../components/ThemeToggle.vue";
import LeagueSwitcher from "../components/LeagueSwitcher.vue";
import BrandLogo from "../components/BrandLogo.vue";
</script>

<template>
  <div class="min-h-full">
    <header class="sticky top-0 z-20 border-b border-ink-200/70 bg-ink-50/80 backdrop-blur dark:border-ink-800 dark:bg-ink-950/80">
      <div class="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <RouterLink :to="{ name: 'gameweeks' }" aria-label="Bolum home">
          <BrandLogo size="md" />
        </RouterLink>

        <div class="flex items-center gap-2">
          <div class="hidden sm:block"><LeagueSwitcher /></div>
          <ThemeToggle />
          <RouterLink :to="{ name: 'admin' }" class="btn-ghost hidden sm:inline-flex">Admin</RouterLink>
        </div>
      </div>
      <div class="mx-auto max-w-6xl px-4 pb-3 sm:hidden"><LeagueSwitcher /></div>
    </header>

    <main class="mx-auto max-w-6xl px-4 py-8">
      <RouterView />
    </main>

    <footer class="mx-auto max-w-6xl px-4 py-8 text-center text-xs text-ink-400">
      Poisson-based predictions · for analysis only, not betting advice.
    </footer>
  </div>
</template>
