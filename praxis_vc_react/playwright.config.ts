import { defineConfig } from "@playwright/test";

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
    baseURL: "http://127.0.0.1:8000",
    viewport: { width: 1280, height: 720 },
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: {
    // cwd 默认 = 本 config 所在目录(praxis_vc_react/);先 build,再回 repo root 启 uvicorn
    command:
      'npm run build && cd .. && P7_DATA_ROOT="$(mktemp -d)" && PRAXIS_VC_RUNS="$(mktemp -d)" PRAXIS_VC_DATA_ROOT="$P7_DATA_ROOT" PRAXIS_VC_UPLOAD_TOKEN="p7-playwright-upload-token-is-at-least-32-bytes" PYTHONPATH="$PWD" "${PRAXIS_VC_TEST_PYTHON:-.venv/bin/python}" -m uvicorn praxis_vc_api.main:app --host 127.0.0.1 --port 8000',
    url: "http://127.0.0.1:8000/api/health",
    reuseExistingServer: !process.env.CI,
    timeout: 180000,
  },
});
