import { test } from "@playwright/test";

const OFFLINE_GATE_REASON =
  "C3 离线门禁：真实 LLM E2E 需要用户显式授权外部网络访问，并通过独立 opt-in 运行配置启用；本规范不读取凭证。";

test("S10 真实 LLM 辅助路径待显式授权与 opt-in", () => {
  test.skip(true, OFFLINE_GATE_REASON);
});
