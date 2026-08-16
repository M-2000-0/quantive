/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: { DEFAULT: "#131313", low: "#1b1b1b", container: "#1f1f1f", high: "#2a2a2a", variant: "#353535" },
        primary: { DEFAULT: "#facc15", dim: "#e6b800" },
        on: { surface: "#e2e2e2", variant: "#a0a0a4", muted: "#646468" },
        error: { DEFAULT: "#ffb4ab", bg: "rgba(255,180,171,0.1)" },
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"], mono: ["JetBrains Mono", "monospace"] },
    },
  },
  plugins: [],
};
