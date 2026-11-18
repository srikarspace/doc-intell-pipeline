import { defineConfig, devices } from "@playwright/test";
import { tmpdir } from "node:os";
import { join } from "node:path";

// The e2e test runs the real API on its own port, with a new, empty database in the temp folder.
// It seeds two stored answers (from web/src/fixtures/) so that reviews and undo work against the real API.
// The model is never called: the test replays the stored stream, and the key below is a fake one.
const PORT = 8010;
const DB = join(tmpdir(), "docintel-e2e.duckdb");
const seed = (name: string) => `uv run python web/e2e/fixtures.py seed web/src/fixtures/${name}-stream.json`;

export default defineConfig({
  testDir: "e2e",
  workers: 1,
  reporter: "list",
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "retain-on-failure",
    video: process.env.VIDEO ? "on" : "off", // VIDEO=1 make e2e: a silent recording, a backup for the demo
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 860 } } }],
  webServer: {
    cwd: "..", // the repo root: web/dist and the Python package are found from there
    command: [
      `rm -f ${DB} ${DB}.wal`,
      seed("kubient"),
      seed("ecoscience"),
      `uv run uvicorn docintel.api.app:app --port ${PORT} --no-access-log`,
    ].join(" && "),
    url: `http://localhost:${PORT}/health`,
    reuseExistingServer: false,
    env: { APP_DB: DB, TRACING: "false", OPENROUTER_API_KEY: "sk-or-v1-e2e-not-used" },
  },
});
