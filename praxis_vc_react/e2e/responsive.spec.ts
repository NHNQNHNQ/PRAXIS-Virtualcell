import { expect, test, type Page, type Response } from "@playwright/test";

type BrowserFailures = {
  pageErrors: string[];
  consoleErrors: string[];
  http500: string[];
};

type ResponsiveCase = {
  name: string;
  viewport: { width: number; height: number };
};

const RESPONSIVE_CASES: ResponsiveCase[] = [
  { name: "mobile 375×812", viewport: { width: 375, height: 812 } },
  { name: "landscape 667×375", viewport: { width: 667, height: 375 } },
  { name: "tablet 768×1024", viewport: { width: 768, height: 1024 } },
];

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

function hasRequest(
  response: Response,
  method: string,
  pathPattern: RegExp,
): boolean {
  return (
    response.request().method() === method &&
    pathPattern.test(new URL(response.url()).pathname)
  );
}

async function expectOk(responsePromise: Promise<Response>): Promise<Response> {
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  return response;
}

async function runResponsiveJourney(page: Page): Promise<void> {
  const failures = collectBrowserFailures(page);
  const healthResponsePromise = page.waitForResponse((response) =>
    hasRequest(response, "GET", /^\/api\/health$/),
  );
  // options 会随 Review 加载；在导航前监听，避免快速响应先于 Ask 操作完成。
  const optionsResponsePromise = page.waitForResponse((response) =>
    hasRequest(response, "GET", /^\/api\/options$/),
  );
  await page.goto("/");
  await expectOk(healthResponsePromise);
  await expect(
    page.getByText(
      "语言模型仅用于解析与解释，不参与数值预测或最终裁决",
      { exact: true },
    ),
  ).toBeVisible();
  await page.getByRole("button", { name: "Agent Workspace", exact: true }).click();

  // Ask:标题、主操作和解析相关 API 在窄视口仍可达。
  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验", exact: true }),
  ).toBeVisible();
  const parseButton = page.getByRole("button", {
    name: "解读任务 →",
    exact: true,
  });
  await expect(parseButton).toBeVisible();
  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");
  await expect(parseButton).toBeEnabled();

  const parseResponsePromise = page.waitForResponse((response) =>
    hasRequest(response, "POST", /^\/api\/parse$/),
  );
  await parseButton.click();
  await Promise.all([
    expectOk(parseResponsePromise),
    expectOk(optionsResponsePromise),
  ]);

  // Review。
  await expect(
    page.getByRole("heading", { name: "核对任务解读", exact: true }),
  ).toBeVisible();
  const reviewButton = page.getByRole("button", {
    name: "确认并继续 →",
    exact: true,
  });
  await expect(reviewButton).toBeVisible();
  await expect(reviewButton).toBeEnabled();
  const modulesResponsePromise = page.waitForResponse((response) =>
    hasRequest(response, "GET", /^\/api\/modules$/),
  );
  await reviewButton.click();
  await expectOk(modulesResponsePromise);

  // Route。
  await expect(
    page.getByRole("heading", {
      name: "预计涉及的功能模块",
      exact: true,
    }),
  ).toBeVisible();
  const routeButton = page.getByRole("button", {
    name: "下一步 →",
    exact: true,
  });
  await expect(routeButton).toBeVisible();
  await expect(routeButton).toBeEnabled();
  await routeButton.click();

  // Run:运行提交及 Results 所依赖的报告/路由 API 必须都返回 200。
  await expect(
    page.getByRole("heading", { name: "运行前确认", exact: true }),
  ).toBeVisible();
  const runButton = page.getByRole("button", {
    name: "开始运行 →",
    exact: true,
  });
  await expect(runButton).toBeVisible();
  await expect(runButton).toBeEnabled();

  const jobResponsePromise = page.waitForResponse((response) =>
    hasRequest(response, "POST", /^\/api\/jobs$/),
  );
  const reportResponsePromise = page.waitForResponse((response) =>
    hasRequest(response, "GET", /^\/api\/reports\/[^/]+$/),
  );
  const modulePlanResponsePromise = page.waitForResponse((response) =>
    hasRequest(response, "GET", /^\/api\/reports\/[^/]+\/module-plan$/),
  );
  await runButton.click();
  const [jobResponse] = await Promise.all([
    expectOk(jobResponsePromise),
    expectOk(reportResponsePromise),
    expectOk(modulePlanResponsePromise),
  ]);
  const { job_id: jobId } = (await jobResponse.json()) as { job_id: string };
  expect(jobId).toMatch(/^vc_/);

  // Results:用 region/group/button/tab 的可访问语义验证操作与内容切换。
  const resultName = `结果 · job ${jobId}`;
  await expect(
    page.getByRole("heading", { name: resultName, exact: true }),
  ).toBeVisible();
  const result = page.getByRole("region", { name: resultName, exact: true });
  await expect(result).toBeVisible();

  const actions = result.getByRole("group", { name: "结果操作", exact: true });
  await expect(actions).toBeVisible();
  await expect(actions.getByRole("button")).toHaveCount(5);
  for (const actionName of [
    "下载 report.json",
    "下载 narrative.md",
    "下载 report.md",
    "复制报告",
    "＋ 新建查询",
  ]) {
    await expect(
      actions.getByRole("button", { name: actionName, exact: true }),
    ).toBeVisible();
  }

  await expect(result.getByRole("tab")).toHaveCount(7);
  await expect(
    result.getByRole("heading", { name: "概要", exact: true }),
  ).toBeVisible();
  await result.getByRole("tab", { name: "预测", exact: true }).click();
  await expect(
    result.getByRole("heading", { name: "结果可靠性", exact: true }),
  ).toBeVisible();
  await result.getByRole("tab", { name: "模块路由", exact: true }).click();
  await expect(
    result.getByRole("heading", { name: "路由摘要", exact: true }),
  ).toBeVisible();
  await result
    .getByRole("tab", { name: "数据与执行身份", exact: true })
    .click();
  await expect(
    result.getByRole("heading", {
      name: "数据与执行身份",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    result.getByText("未绑定 VirtualCellPack", { exact: true }),
  ).toBeVisible();
  await expect(
    result.getByText("未记录 dataset identity", { exact: true }),
  ).toBeVisible();

  expectNoBrowserFailures(failures);
}

for (const responsiveCase of RESPONSIVE_CASES) {
  test(`S12 ${responsiveCase.name} 完整五阶段与 Results 语义可达`, async ({
    page,
  }) => {
    await page.setViewportSize(responsiveCase.viewport);
    await runResponsiveJourney(page);
  });
}
