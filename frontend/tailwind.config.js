/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      colors: {
        ink: { 950: "#08090c", 900: "#0d0f14", 850: "#12151b", 800: "#171a21", 700: "#20242d", 600: "#2b303b", 500: "#3a404d" },
        accent: { DEFAULT: "#7c6cff", 400: "#9b8fff", 500: "#7c6cff", 600: "#6553f5", soft: "rgba(124,108,255,0.12)" },
      },
      boxShadow: { glow: "0 0 0 1px rgba(124,108,255,.35), 0 8px 30px -12px rgba(124,108,255,.45)" },
      keyframes: {
        fadeUp: { "0%": { opacity: 0, transform: "translateY(6px)" }, "100%": { opacity: 1, transform: "none" } },
        pulseDot: { "0%,100%": { opacity: 1 }, "50%": { opacity: 0.3 } },
      },
      animation: { "fade-up": "fadeUp .35s ease-out both", "pulse-dot": "pulseDot 1.4s ease-in-out infinite" },
    },
  },
  plugins: [],
};
