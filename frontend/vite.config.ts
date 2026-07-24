import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// The dev server proxies API calls to the Spandana backend (FastAPI/Flask on
// :8000). Services still fall back to mock data when the backend is offline,
// so the UI is fully demoable without a running backend.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/predict": "http://localhost:8000",
      "/history": "http://localhost:8000",
      "/report": "http://localhost:8000",
      "/stream": "http://localhost:8000",
      "/machines": "http://localhost:8000",
    },
  },
});
