import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f6f3ec",
        surface: "#fffdf8",
        raised: "#faf7f0",
        ink: "#1b1a15",
        "ink-2": "#5a564b",
        muted: "#8b867a",
        line: "#e6e1d4",
        "line-strong": "#d6d0be",
        accent: "#2a6df4",
        "accent-ink": "#1c53c4",
        court: "#c05327", // clay-court terracotta — used sparingly
        positive: "#1f7a3d",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      letterSpacing: {
        eyebrow: "0.16em",
      },
      boxShadow: {
        panel: "0 1px 2px rgba(27, 26, 21, 0.04), 0 1px 1px rgba(27, 26, 21, 0.03)",
        lift: "0 6px 24px -12px rgba(27, 26, 21, 0.18)",
      },
    },
  },
  plugins: [],
};
export default config;
