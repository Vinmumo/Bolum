<script setup>
import { RouterLink, RouterView, useRouter } from "vue-router";
import ThemeToggle from "../components/ThemeToggle.vue";
import BrandLogo from "../components/BrandLogo.vue";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();

function logout() {
  auth.logout();
  router.push({ name: "admin-login" });
}
</script>

<template>
  <div class="min-h-full">
    <header class="border-b border-ink-200/70 bg-white dark:border-ink-800 dark:bg-ink-900">
      <div class="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <div class="flex items-center gap-2.5">
          <BrandLogo size="sm" />
          <span class="chip bg-ink-900 text-white dark:bg-white dark:text-ink-900">ADMIN</span>
        </div>
        <div class="flex items-center gap-2">
          <RouterLink :to="{ name: 'gameweeks' }" class="btn-ghost">View site</RouterLink>
          <ThemeToggle />
          <button class="btn-ghost" @click="logout">Log out</button>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-6xl px-4 py-8">
      <RouterView />
    </main>
  </div>
</template>
