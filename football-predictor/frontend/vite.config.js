import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// The backend runs on :8000 in dev. We proxy /api so the frontend can use
// same-origin relative URLs (no CORS surprises, no hardcoded host).
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
