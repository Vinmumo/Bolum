import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

const routes = [
  {
    path: "/",
    component: () => import("../layouts/PublicLayout.vue"),
    children: [
      { path: "", name: "gameweeks", component: () => import("../views/GameweeksView.vue") },
      {
        path: "gameweek",
        name: "gameweek",
        component: () => import("../views/GameweekView.vue"),
      },
      {
        path: "fixture",
        name: "fixture",
        component: () => import("../views/FixtureDetailView.vue"),
      },
      {
        path: "season/:year(\\d+)",
        name: "season",
        component: () => import("../views/SeasonView.vue"),
      },
    ],
  },
  {
    path: "/admin/login",
    name: "admin-login",
    component: () => import("../views/admin/AdminLoginView.vue"),
  },
  {
    path: "/admin",
    component: () => import("../layouts/AdminLayout.vue"),
    meta: { requiresAdmin: true },
    children: [
      { path: "", name: "admin", component: () => import("../views/admin/AdminDashboardView.vue") },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});

router.beforeEach((to) => {
  if (to.meta.requiresAdmin) {
    const auth = useAuthStore();
    if (!auth.isAuthed) return { name: "admin-login", query: { redirect: to.fullPath } };
  }
});

export default router;
