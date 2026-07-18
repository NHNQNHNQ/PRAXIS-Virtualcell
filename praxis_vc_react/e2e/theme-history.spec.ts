import { expect, test, type Page } from "@playwright/test";

type BrowserFailures = {
  pageErrors: string[];
  consoleErrors: string[];
  http500: string[];
};

function collectBrowserFailures(page: Page): BrowserFailures {
  const failures: BrowserFailures = {
    pageErrors: [],
    consoleErrors: [],
    http500: [],
  };

  page.on("pageerror", (error) => failures.pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") failures.consoleErrors.push(message.text());
  });
  page.on("response", (response) => {
    if (response.status() >= 500) {
      failures.http500.push(
        `${response.status()} ${response.request().method()} ${response.url()}`,
      );
    }
  });

  return failures;
}

function expectNoBrowserFailures(failures: BrowserFailures): void {
  expect(failures.pageErrors).toEqual([]);
  expect(failures.consoleErrors).toEqual([]);
  expect(failures.http500).toEqual([]);
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function historyEntry(page: Page, jobId: string) {
  return page.getByRole("button", {
    name: new RegExp(`\\b${escapeRegExp(jobId)}\\b`),
  });
}

async function runQueryFromAsk(page: Page, query: string): Promise<string> {
  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验" }),
  ).toBeVisible();
  await page.getByLabel("研究问题").fill(query);

  const parseResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/parse") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "解读任务 →" }).click();
  expect((await parseResponsePromise).status()).toBe(200);

  await expect(
    page.getByRole("heading", { name: "核对任务解读" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "确认并继续 →" }).click();

  await expect(
    page.getByRole("heading", { name: "预计涉及的功能模块" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "下一步 →" }).click();

  await expect(page.getByRole("heading", { name: "运行前确认" })).toBeVisible();
  const jobResponsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/jobs") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "开始运行 →" }).click();

  const jobResponse = await jobResponsePromise;
  expect(jobResponse.status()).toBe(200);
  const body = (await jobResponse.json()) as { job_id: string };
  expect(body.job_id).toMatch(/^vc_/);
  await expect(
    page.getByRole("heading", {
      name: `结果 · job ${body.job_id}`,
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "概要", exact: true }),
  ).toBeVisible();
  return body.job_id;
}

async function startNewQuery(page: Page): Promise<void> {
  await page
    .getByRole("group", { name: "结果操作" })
    .getByRole("button", { name: "＋ 新建查询", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验" }),
  ).toBeVisible();
}

async function openHistoryJob(page: Page, jobId: string): Promise<void> {
  const entry = historyEntry(page, jobId);
  await expect(entry).toHaveCount(1);
  const reportResponsePromise = page.waitForResponse((response) => {
    const path = new URL(response.url()).pathname;
    return (
      path === `/api/reports/${jobId}` &&
      response.request().method() === "GET"
    );
  });
  await entry.click();
  expect((await reportResponsePromise).status()).toBe(200);
  await expect(
    page.getByRole("heading", {
      name: `结果 · job ${jobId}`,
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "概要", exact: true }),
  ).toBeVisible();
}

test.describe("S7 主题切换", () => {
  test.use({ colorScheme: "dark" });

  test("深色偏好上下文中深浅主题来回切换后完整流程仍可达", async ({
    page,
  }) => {
    const failures = collectBrowserFailures(page);
    await page.goto("/");

    // 应用显式以浅色主题启动；系统深色偏好上下文仍须保留完整语义结构。
    await expect(
      page.getByRole("heading", { name: "描述一次扰动实验" }),
    ).toBeVisible();
    const switchToDark = page.getByRole("button", {
      name: "切换到深色主题",
    });
    await expect(switchToDark).toBeVisible();

    await switchToDark.click();
    const switchToLight = page.getByRole("button", {
      name: "切换到浅色主题",
    });
    await expect(switchToLight).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "描述一次扰动实验" }),
    ).toBeVisible();

    await switchToLight.click();
    await expect(switchToDark).toBeVisible();
    await switchToDark.click();
    await expect(switchToLight).toBeVisible();

    const jobId = await runQueryFromAsk(page, "在 human 细胞敲 AHR");
    await expect(
      page.getByRole("heading", {
        name: `结果 · job ${jobId}`,
        exact: true,
      }),
    ).toBeVisible();

    await switchToLight.click();
    await expect(switchToDark).toBeVisible();
    await expect(
      page.getByRole("group", { name: "结果操作" }),
    ).toBeVisible();
    expectNoBrowserFailures(failures);
  });
});

test("S8 两个不同请求可按唯一 job_id 从历史回看，收藏保持占位", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  await page.goto("/");

  const firstJobId = await runQueryFromAsk(page, "在 human 细胞敲 AHR");
  const firstEntry = historyEntry(page, firstJobId);
  await expect(firstEntry).toHaveCount(1);

  await startNewQuery(page);
  const secondJobId = await runQueryFromAsk(page, "在 human 细胞敲 FASN");
  expect(secondJobId).not.toBe(firstJobId);
  const secondEntry = historyEntry(page, secondJobId);
  await expect(secondEntry).toHaveCount(1);

  await openHistoryJob(page, firstJobId);
  await openHistoryJob(page, secondJobId);

  await expect(page.getByText("收藏", { exact: true })).toBeVisible();
  await expect(page.getByText("暂无收藏", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /收藏/ })).toHaveCount(0);
  expectNoBrowserFailures(failures);
});
