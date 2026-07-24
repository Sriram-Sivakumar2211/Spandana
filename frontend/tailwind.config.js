/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // All colors resolve to CSS variables defined in src/index.css, so a
        // single class like `bg-card` follows the active (light/dark) theme.
        background: "var(--bg)",
        sidebar: "var(--sidebar)",
        card: "var(--card)",
        border: "var(--border)",
        primary: {
          DEFAULT: "var(--primary)",
          hover: "var(--primary-hover)",
          foreground: "var(--primary-foreground)",
        },
        foreground: "var(--text)",
        muted: "var(--text-muted)",
        success: "var(--success)",
        warning: "var(--warning)",
        critical: "var(--critical)",
        ring: "var(--ring)",
      },
      fontFamily: {
        // "Anthropic serif" editorial feel applied across the app: a refined
        // screen serif (Newsreader) is the default body face, DM Serif Display
        // carries large display headings, Inter is the numeric/utility fallback.
        serif: ["Newsreader", "Georgia", "Cambria", "serif"],
        display: ['"DM Serif Display"', "Newsreader", "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xl: "0.9rem",
        "2xl": "1.15rem",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06)",
        "soft-lg": "0 2px 6px rgba(0,0,0,0.06), 0 18px 48px rgba(0,0,0,0.10)",
        glow: "0 0 0 1px var(--primary), 0 8px 30px -8px var(--primary)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        pulseline: {
          "0%,100%": { opacity: "0.5" },
          "50%": { opacity: "1" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.4s ease-out both",
        pulseline: "pulseline 2s ease-in-out infinite",
        shimmer: "shimmer 1.5s infinite",
      },
    },
  },
  plugins: [],
};
