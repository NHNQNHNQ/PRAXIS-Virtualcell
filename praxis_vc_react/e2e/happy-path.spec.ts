import { test, expect } from "@playwright/test";

// 5 阶段 happy path:ask→review→route→run→results 五跳全绿。
// 选择器全走 role/text/label(抗前端 WIP CSS);API 调用是阶段推进的硬证据(waitForResponse)。
test("5 阶段 happy path 五跳到达 Results", async ({ page }) => {
  await page.goto("/");

  // ── 阶段 1:Ask ──(heading + 预填输入 + 点解读任务 → POST /api/parse)
  await expect(page.getByRole("heading", { name: "描述一次扰动实验" })).toBeVisible();
  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");
  const parseResp = page.waitForResponse(
    (r) => r.url().includes("/api/parse") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await parseResp;

  // ── 阶段 2:Review ──(heading 出现 → species 已回填 → 点确认并继续)
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  const reviewNext = page.getByRole("button", { name: "确认并继续 →" });
  await expect(reviewNext).toBeEnabled();
  await reviewNext.click();

  // ── 阶段 3:Route ──(heading + amber 横幅 → 点下一步)
  await expect(page.getByRole("heading", { name: "预计涉及的功能模块" })).toBeVisible();
  await expect(page.getByText("这里是预期,不是实际结果。")).toBeVisible();
  await page.getByRole("button", { name: "下一步 →" }).click();

  // ── 阶段 4:Run ──(heading → 点开始运行 → POST /api/jobs 同步拿 job_id)
  await expect(page.getByRole("heading", { name: "运行前确认" })).toBeVisible();
  const jobsResp = page.waitForResponse(
    (r) => r.url().includes("/api/jobs") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "开始运行 →" }).click();
  await jobsResp;

  // ── 阶段 5:Results ──(heading /^结果 · job/ 出现 = 五跳到达)
  await expect(page.getByRole("heading", { name: /^结果 · job/ })).toBeVisible();
});
