import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0b1220",
        surface: "#121a2b",
        surfaceAlt: "#1a2438",
        border: "#22304a",
        text: "#f1f5f9",
        muted: "#8aa0b9",
        accent: "#38bdf8",
        success: "#34d399",
        warning: "#f59e0b",
        danger: "#f87171"
      },
      boxShadow: {
        panel: "0 10px 30px rgba(2, 8, 23, 0.35)"
      },
      backgroundImage: {
        "ops-grid":
          "radial-gradient(circle at top left, rgba(56,189,248,0.08), transparent 35%), linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)"
      },
      backgroundSize: {
        "ops-grid": "auto, 28px 28px, 28px 28px"
      }
    }
  },
  plugins: [],
} satisfies Config;
