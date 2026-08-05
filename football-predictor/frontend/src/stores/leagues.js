import { defineStore } from "pinia";
import client from "../api/client";

// Holds the active leagues + the currently-selected one for the nav switcher.
export const useLeaguesStore = defineStore("leagues", {
  state: () => ({
    leagues: [],
    selectedId: null,
    loaded: false,
  }),
  getters: {
    selected: (s) => s.leagues.find((l) => l.id === s.selectedId) || s.leagues[0] || null,
  },
  actions: {
    async fetch() {
      const { data } = await client.get("/leagues");
      this.leagues = data;
      if (this.selectedId == null && data.length) this.selectedId = data[0].id;
      this.loaded = true;
    },
    select(id) {
      this.selectedId = id;
    },
  },
});
