import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#0b0f19",
        surface: "#111827",
        surfaceCard: "#1a2234",
        borderDark: "#243049",
        accent: "#3b82f6",
        accentGold: "#f59e0b",
        accentGreen: "#10b981",
        accentRed: "#ef4444",
      },
    },
  },
  plugins: [],
};
export default config;
