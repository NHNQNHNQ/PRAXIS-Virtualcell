import { realpathSync } from "node:fs";
import { tmpdir } from "node:os";
import { defineConfig } from "@playwright/test";

// Resolve macOS symlinks and quote the platform temporary directory for the shell.
const tempRoot = realpathSync(tmpdir()).replaceAll("'", "'\\''");

const port = process.env.PRAXIS_VC_E2E_PORT ?? "8000";
if (!/^\d+$/.test(port)) throw new Error("PRAXIS_VC_E2E_PORT must be numeric");
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "./e2e",
  testIgnore: "**/._*",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL,
    viewport: { width: 1280, height: 720 },
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: {
    // Build before importing the API so it can mount the static assets.
    command:
      `npm run build && cd .. && P7_DATA_ROOT="$(mktemp -d '${tempRoot}/praxis-vc-e2e-data.XXXXXX')" && PRAXIS_VC_RUNS="$(mktemp -d '${tempRoot}/praxis-vc-e2e-runs.XXXXXX')" PRAXIS_VC_DATA_ROOT="$P7_DATA_ROOT" PRAXIS_VC_UPLOAD_TOKEN="p7-playwright-upload-token-is-at-least-32-bytes" PYTHONPATH="$PWD" "\${PRAXIS_VC_TEST_PYTHON:-.venv/bin/python}" -m uvicorn praxis_vc_api.main:app --host 127.0.0.1 --port ${port}`,
    url: `${baseURL}/api/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 180000,
  },
});
