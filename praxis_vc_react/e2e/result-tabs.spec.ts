import { test, expect, type Page } from "@playwright/test";

// 先走完 5 阶段到 Results,再逐个点 6 tab 断面板 h2(切 tab 纯前端不发请求)。
async function reachResults(page: Page): Promise<void> {
  await page.goto("/");
  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await page.getByRole("button", { name: "确认并继续 →" }).click();
  await page.getByRole("button", { name: "下一步 →" }).click();
  await page.getByRole("button", { name: "开始运行 →" }).click();
  await expect(page.getByRole("heading", { name: /^结果 · job/ })).toBeVisible();
}

const TABS: Array<[string, string]> = [
  ["报告", "概要"],
  ["预测", "结果可靠性"],
  ["模块路由", "路由摘要"],
  ["证据", "证据与审计"],
  ["运行轨迹", "运行轨迹"],
  ["溯源", "运行标识"],
];

test("Results 6 tab 逐个可达 + 面板 h2 出现", async ({ page }) => {
  await reachResults(page);
  for (const [tab, h2] of TABS) {
    await page.getByRole("tab", { name: tab }).click();
    await expect(page.getByRole("heading", { name: h2 })).toBeVisible();
  }
});
