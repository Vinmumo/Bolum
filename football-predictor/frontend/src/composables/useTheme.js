import { ref } from "vue";

const isDark = ref(document.documentElement.classList.contains("dark"));

export function useTheme() {
  function toggle() {
    isDark.value = !isDark.value;
    document.documentElement.classList.toggle("dark", isDark.value);
    localStorage.setItem("theme", isDark.value ? "dark" : "light");
  }
  return { isDark, toggle };
}
