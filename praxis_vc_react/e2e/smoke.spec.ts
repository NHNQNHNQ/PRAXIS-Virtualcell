import { test, expect, type Page } from "@playwright/test";

function collectFailures(page: Page) {
  const failures = { pageErrors: [] as string[], consoleErrors: [] as string[], http500: [] as string[] };
  page.on("pageerror", (error) => failures.pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") failures.consoleErrors.push(message.text());
  });
  page.on("response", (response) => {
    if (response.status() >= 500) failures.http500.push(`${response.status()} ${response.url()}`);
  });
  return failures;
}

function expectNoFailures(failures: ReturnType<typeof collectFailures>) {
  expect(failures).toEqual({ pageErrors: [], consoleErrors: [], http500: [] });
}

test("从首页进入 Agent Workspace 后到达 Ask 阶段", async ({ page }) => {
  const failures = collectFailures(page);
  const healthResponse = page.waitForResponse(
    (response) => response.url().endsWith("/api/health"),
  );
  const jobsResponse = page.waitForResponse(
    (response) => response.url().endsWith("/api/jobs"),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Agent Workspace", exact: true }).click();
  expect((await healthResponse).status()).toBe(200);
  expect((await jobsResponse).status()).toBe(200);
  await expect(page.getByRole("heading", { name: "描述一次扰动实验" })).toBeVisible();
  await expect(page.getByLabel("研究问题")).toBeVisible();
  await expect(page.getByRole("button", { name: "解读任务 →" })).toBeEnabled();
  expectNoFailures(failures);
});

test("侧栏版本来自后端 health", async ({ page }) => {
  const failures = collectFailures(page);
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

  const healthResponse = page.waitForResponse(
    (response) => response.url().endsWith("/api/health"),
  );
  const jobsResponse = page.waitForResponse(
    (response) => response.url().endsWith("/api/jobs"),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Agent Workspace", exact: true }).click();
  expect((await healthResponse).status()).toBe(200);
  expect((await jobsResponse).status()).toBe(200);
  await expect(page.getByText("后端 ok · 产品 9.9.9")).toBeVisible();
  await expect(page.getByText(/vc\.runtime\.v1 · build abcdef1/)).toBeVisible();
  expectNoFailures(failures);
});
