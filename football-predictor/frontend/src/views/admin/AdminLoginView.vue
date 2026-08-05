<script setup>
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import { toUiError } from "../../api/client";
import ThemeToggle from "../../components/ThemeToggle.vue";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();

const username = ref("");
const password = ref("");
const loading = ref(false);
const error = ref(null);

async function submit() {
  loading.value = true;
  error.value = null;
  try {
    await auth.login(username.value, password.value);
    router.push(route.query.redirect || { name: "admin" });
  } catch (err) {
    const e = toUiError(err);
    error.value = e.kind === "auth" ? "Incorrect username or password." : e.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center px-4">
    <div class="absolute right-4 top-4"><ThemeToggle /></div>
    <div class="card w-full max-w-sm p-8">
      <div class="mb-6 flex items-center gap-2.5">
        <span class="chip bg-ink-900 text-white dark:bg-white dark:text-ink-900">ADMIN</span>
        <h1 class="text-lg font-bold">Sign in</h1>
      </div>

      <form class="space-y-4" @submit.prevent="submit">
        <div>
          <label class="mb-1 block text-xs font-medium text-ink-500">Username</label>
          <input v-model="username" class="input" autocomplete="username" required />
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-ink-500">Password</label>
          <input v-model="password" type="password" class="input" autocomplete="current-password" required />
        </div>

        <p v-if="error" class="rounded-lg bg-away/10 px-3 py-2 text-sm text-away">{{ error }}</p>

        <button class="btn-primary w-full" :disabled="loading">
          {{ loading ? "Signing in…" : "Sign in" }}
        </button>
      </form>
      <p class="mt-4 text-center text-xs text-ink-400">
        Credentials are set in the backend <code>.env</code>.
      </p>
    </div>
  </div>
</template>
