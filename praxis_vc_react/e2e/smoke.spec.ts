import { test, expect } from "@playwright/test";

test("首屏到达 Ask 阶段", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "描述一次扰动实验" })).toBeVisible();
  await expect(page.getByLabel("研究问题")).toBeVisible();
  await expect(page.getByRole("button", { name: "解读任务 →" })).toBeEnabled();
});

test("侧栏版本来自后端 health", async ({ page }) => {
  await page.route("**/api/health", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "ok",
        mode: "offline",
        llm_enabled: false,
        product_version: "9.9.9",
        api_protocol_version: "vc.api.v1",
        runtime_protocol_version: "vc.runtime.v1",
        runtime_version: "v0.3",
        git_sha: "abcdef1234567890",
      }),
    });
  });

  await page.goto("/");
  await expect(page.getByText("后端 ok · 产品 9.9.9")).toBeVisible();
  await expect(page.getByText(/vc\.runtime\.v1 · build abcdef1/)).toBeVisible();
});
