import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0f1115",
        surface: "#171a1f",
        surfaceAlt: "#1d2128",
        border: "#2a3038",
        text: "#f5f7fa",
        muted: "#98a0ab",
        accent: "#d7dde6",
        accentStrong: "#8fb4d6",
        success: "#8eb8a2",
        warning: "#c7ae81",
        danger: "#d28f95",
      },
      boxShadow: {
        panel: "0 18px 50px rgba(0, 0, 0, 0.22)",
        soft: "0 8px 24px rgba(0, 0, 0, 0.14)",
      },
      backgroundImage: {
        "ops-grid":
          "radial-gradient(circle at top left, rgba(143, 180, 214, 0.08), transparent 32%), linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px)",
      },
      backgroundSize: {
        "ops-grid": "auto, 28px 28px, 28px 28px",
      },
    },
  },
  plugins: [],
} satisfies Config;
