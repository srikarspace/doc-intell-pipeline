import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, Vite serves the UI on :5173 and sends API calls to FastAPI.
// The browser sees one origin, so there is no CORS, just like `make app`.
const api = process.env.API_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // pdf.js is about 630 kB. It is in its own file (PdfPane), loaded only when a result is shown.
  build: { chunkSizeWarningLimit: 700 },
  server: {
    port: 5173,
    proxy: { "/v1": api, "/health": api },
  },
});
