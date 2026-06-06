import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite config for the React frontend.
// The dev server runs on port 5173 (Vite's default), which the FastAPI
// backend already allows via CORS in backend/main.py.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
