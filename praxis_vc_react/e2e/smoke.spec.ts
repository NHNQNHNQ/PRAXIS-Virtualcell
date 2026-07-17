import { test, expect } from "@playwright/test";

test("首屏到达 Ask 阶段", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "描述一次扰动实验" })).toBeVisible();
  await expect(page.getByLabel("研究问题")).toBeVisible();
  await expect(page.getByRole("button", { name: "解读任务 →" })).toBeEnabled();
});
