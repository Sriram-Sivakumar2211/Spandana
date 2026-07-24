import { Moon, Sun } from "lucide-react";
import { motion } from "framer-motion";
import { useTheme } from "@/hooks/useTheme";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  return (
    <button
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="relative grid h-10 w-10 place-items-center rounded-xl border border-border bg-card text-muted transition-colors hover:text-primary"
    >
      <motion.span
        key={theme}
        initial={{ rotate: -30, opacity: 0, scale: 0.7 }}
        animate={{ rotate: 0, opacity: 1, scale: 1 }}
        transition={{ duration: 0.25 }}
        className="grid place-items-center"
      >
        {isDark ? <Moon size={17} /> : <Sun size={17} />}
      </motion.span>
    </button>
  );
}
