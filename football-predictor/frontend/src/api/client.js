import axios from "axios";

// Same-origin relative base — Vite proxies /api to the backend in dev.
const client = axios.create({ baseURL: "/api" });

// Attach admin token when present.
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("admin_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

/**
 * Normalise backend/network errors into a small shape the UI can branch on.
 * Distinguishes rate-limit (429) so views can show a friendly message.
 */
export function toUiError(err) {
  const status = err?.response?.status;
  const detail = err?.response?.data?.detail;
  if (status === 429) {
    return {
      kind: "rate_limit",
      message:
        detail || "Rate limit reached for the data provider. Try again later.",
    };
  }
  if (status === 401) {
    return { kind: "auth", message: detail || "Not authorized." };
  }
  if (!err?.response) {
    return {
      kind: "network",
      message: "Can't reach the server. Is the backend running?",
    };
  }
  return { kind: "error", message: detail || "Something went wrong." };
}

export default client;
