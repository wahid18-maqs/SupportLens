import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite config for the SupportLens frontend.
// The FastAPI backend URL is read from VITE_API_BASE_URL at build/dev time
// (see src/api.ts), so no dev-server proxy is required.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
