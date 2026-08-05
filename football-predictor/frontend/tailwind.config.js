/** @type {import('tailwindcss').Config} */
// A real color system — not default slate/blue.
//  - `brand`  : emerald/pitch green, the product accent.
//  - `ink`    : a warm charcoal neutral scale for surfaces & text.
//  - win/draw/away: the validated W/D/L palette, wired to CSS vars in style.css
//    so they re-step correctly between light and dark.
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#ecfdf5",
          100: "#d1fae5",
          200: "#a7f3d0",
          300: "#6ee7b7",
          400: "#34d399",
          500: "#10b981",
          600: "#059669",
          700: "#047857",
          800: "#065f46",
          900: "#064e3b",
          950: "#022c22",
        },
        ink: {
          50: "#f7f7f5",
          100: "#eeedea",
          200: "#dcdad4",
          300: "#c3c0b6",
          400: "#a19d90",
          500: "#827e72",
          600: "#6a675d",
          700: "#565349",
          800: "#3b3934",
          900: "#232220",
          950: "#141312",
        },
        // Outcome colors — defined as CSS vars so they swap by theme.
        win: "rgb(var(--c-win) / <alpha-value>)",
        draw: "rgb(var(--c-draw) / <alpha-value>)",
        away: "rgb(var(--c-away) / <alpha-value>)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.04), 0 8px 24px -12px rgba(0,0,0,0.12)",
      },
    },
  },
  plugins: [],
};
