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
        background: "#070A12",
        surface: "#0D1322",
        surfaceCard: "#131C31",
        surfaceElevated: "#1A2642",
        borderDark: "#22304F",
        accent: "#3B82F6",
        accentHover: "#2563EB",
        accentGold: "#F59E0B",
        accentGreen: "#10B981",
        accentRed: "#EF4444",
      },
      boxShadow: {
        glow: "0 0 20px -2px rgba(59, 130, 246, 0.45)",
        glowGreen: "0 0 20px -2px rgba(16, 185, 129, 0.45)",
        glowRed: "0 0 20px -2px rgba(239, 68, 68, 0.45)",
        card: "0 10px 30px -10px rgba(0, 0, 0, 0.65), inset 0 1px 0 0 rgba(255, 255, 255, 0.06)",
      },
    },
  },
  plugins: [],
};
export default config;
