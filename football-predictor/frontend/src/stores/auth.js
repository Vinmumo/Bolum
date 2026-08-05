import { defineStore } from "pinia";
import client from "../api/client";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem("admin_token") || null,
  }),
  getters: {
    isAuthed: (s) => !!s.token,
  },
  actions: {
    async login(username, password) {
      // OAuth2 password flow expects form-encoded body.
      const body = new URLSearchParams({ username, password });
      const { data } = await client.post("/admin/login", body);
      this.token = data.access_token;
      localStorage.setItem("admin_token", this.token);
    },
    logout() {
      this.token = null;
      localStorage.removeItem("admin_token");
    },
  },
});
