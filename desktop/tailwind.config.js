/** @type {import('tailwindcss').Config} */
export default {
  /** Prefer `:where(.dark, .dark *)` over legacy `:is(.dark *)` (matches subtree reliably). */
  darkMode: "selector",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
