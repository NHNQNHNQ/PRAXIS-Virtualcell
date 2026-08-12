import { defineConfig } from "@playwright/test";

const port = process.env.PRAXIS_VC_E2E_PORT ?? "8000";
if (!/^\d+$/.test(port)) throw new Error("PRAXIS_VC_E2E_PORT must be numeric");
const baseURL = `http://127.0.0.1:${port}`;

// D-B 前端 e2e:role/text 选择器抗 WIP CSS;webServer 先 build 出 dist 再启 uvicorn
// (dist 挂载是 uvicorn import 时判断,顺序不能反)。固定 1280×720 规避 StepperRail 响应式降级。
export default defineConfig({
  testDir: "./e2e",
  // macOS 外置盘会生成 AppleDouble ._*.spec.ts,会被 testMatch 误当测试文件解析崩溃 → 忽略
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
    // cwd 默认 = 本 config 所在目录(praxis_vc_react/);先 build,再回 repo root 启 uvicorn
    command:
      `npm run build && cd .. && P7_DATA_ROOT="$(mktemp -d /private/tmp/praxis-vc-e2e-data.XXXXXX)" && PRAXIS_VC_RUNS="$(mktemp -d /private/tmp/praxis-vc-e2e-runs.XXXXXX)" PRAXIS_VC_DATA_ROOT="$P7_DATA_ROOT" PRAXIS_VC_UPLOAD_TOKEN="p7-playwright-upload-token-is-at-least-32-bytes" PYTHONPATH="$PWD" "\${PRAXIS_VC_TEST_PYTHON:-.venv/bin/python}" -m uvicorn praxis_vc_api.main:app --host 127.0.0.1 --port ${port}`,
    url: `${baseURL}/api/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 180000,
  },
});
