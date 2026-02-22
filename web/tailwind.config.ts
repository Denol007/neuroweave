import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: { DEFAULT: "#0a0a0b", card: "#111113", hover: "#18181b", sidebar: "#0e0e10" },
        border: { DEFAULT: "#1e1e22", hover: "#2a2a30" },
        accent: { DEFAULT: "#6366f1", hover: "#818cf8", glow: "rgba(99,102,241,0.15)" },
        muted: "#71717a",
        dim: "#52525b",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
