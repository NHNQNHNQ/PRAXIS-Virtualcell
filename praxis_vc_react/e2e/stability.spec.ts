import {
  expect,
  test,
  type Page,
  type Request,
  type Response,
} from "@playwright/test";

type BrowserFailures = {
  pageErrors: string[];
  consoleErrors: string[];
  http500: string[];
};

const RESULT_PANELS: Array<[tab: string, heading: string]> = [
  ["报告", "概要"],
  ["预测", "结果可靠性"],
  ["模块路由", "路由摘要"],
  ["证据", "证据与审计"],
  ["运行轨迹", "运行轨迹"],
  ["溯源", "运行标识"],
  ["数据与执行身份", "数据与执行身份"],
];

function isJobsPost(request: Request): boolean {
  return (
    new URL(request.url()).pathname === "/api/jobs" &&
    request.method() === "POST"
  );
}

function isJobsPostResponse(response: Response): boolean {
  return isJobsPost(response.request());
}

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

async function reachRun(page: Page): Promise<void> {
  await page.goto("/");
  await page.getByRole("button", { name: "Agent Workspace", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验" }),
  ).toBeVisible();
  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");

  const parseResponsePromise = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/api/parse" &&
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
}

test("Results 七面板反复切换并滚动真实轨迹与溯源时保持稳定", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  await reachRun(page);

  const jobResponsePromise = page.waitForResponse(isJobsPostResponse);
  const reportResponsePromise = page.waitForResponse((response) => {
    const path = new URL(response.url()).pathname;
    return (
      /^\/api\/reports\/[^/]+$/.test(path) &&
      response.request().method() === "GET"
    );
  });
  const traceResponsePromise = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname.endsWith("/trace") &&
      response.request().method() === "GET",
  );
  const provenanceResponsePromise = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname.endsWith("/provenance") &&
      response.request().method() === "GET",
  );
  const modulePlanResponsePromise = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname.endsWith("/module-plan") &&
      response.request().method() === "GET",
  );

  await page.getByRole("button", { name: "开始运行 →" }).click();
  const [
    jobResponse,
    reportResponse,
    traceResponse,
    provenanceResponse,
    modulePlanResponse,
  ] = await Promise.all([
    jobResponsePromise,
    reportResponsePromise,
    traceResponsePromise,
    provenanceResponsePromise,
    modulePlanResponsePromise,
  ]);
  expect(
    [
      jobResponse,
      reportResponse,
      traceResponse,
      provenanceResponse,
      modulePlanResponse,
    ].map((response) => response.status()),
  ).toEqual([200, 200, 200, 200, 200]);

  const tracePayload = (await traceResponse.json()) as { trace?: unknown };
  const traceSteps = Array.isArray(tracePayload.trace) ? tracePayload.trace : [];
  expect(traceSteps.length).toBeGreaterThan(0);

  const provenancePayload = (await provenanceResponse.json()) as {
    provenance?: unknown;
  };
  const provenance = provenancePayload.provenance;
  const provenanceKeys =
    provenance !== null &&
    typeof provenance === "object" &&
    !Array.isArray(provenance)
      ? Object.keys(provenance)
      : [];
  expect(provenanceKeys.length).toBeGreaterThan(0);

  const result = page.getByRole("region", { name: /^结果 · job/ });
  await expect(result).toHaveCount(1);
  await expect(result).toBeVisible();
  await expect(result.getByRole("tab")).toHaveCount(7);

  for (let pass = 0; pass < 3; pass += 1) {
    for (const [tabName, headingName] of RESULT_PANELS) {
      const tab = result.getByRole("tab", { name: tabName, exact: true });
      await expect(tab).toHaveCount(1);
      await tab.click();

      const heading = result.getByRole("heading", {
        name: headingName,
        exact: true,
      });
      await expect(heading).toHaveCount(1);
      await heading.scrollIntoViewIfNeeded();
      await expect(heading).toBeVisible();
      await expect(tab).toHaveAttribute("aria-selected", "true");
    }
  }

  await result
    .getByRole("tab", { name: "运行轨迹", exact: true })
    .click();
  const traceSummary = result.getByText(
    new RegExp(
      `^运行轨迹 · 共 ${traceSteps.length} 步(?:,精简显示 \\d+ 步)?$`,
    ),
  );
  await expect(traceSummary).toHaveCount(1);
  await traceSummary.scrollIntoViewIfNeeded();
  await expect(traceSummary).toBeVisible();
  await expect(
    result.getByRole("list", {
      name: `运行轨迹时间线,共 ${traceSteps.length} 步`,
      exact: true,
    }),
  ).toBeVisible();

  await result.getByRole("tab", { name: "溯源", exact: true }).click();
  const provenanceJson = result.getByText("完整 provenance JSON", {
    exact: true,
  });
  await expect(provenanceJson).toHaveCount(1);
  await provenanceJson.scrollIntoViewIfNeeded();
  await expect(provenanceJson).toBeVisible();

  expectNoBrowserFailures(failures);
});

test("快速双击开始运行只提交一个 job 并只进入一个 Results", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  await reachRun(page);

  const jobRequests: Request[] = [];
  const jobResponses: Response[] = [];
  page.on("request", (request) => {
    if (isJobsPost(request)) jobRequests.push(request);
  });
  page.on("response", (response) => {
    if (isJobsPostResponse(response)) jobResponses.push(response);
  });

  const jobResponsePromise = page.waitForResponse(isJobsPostResponse);
  const startButton = page.getByRole("button", { name: "开始运行 →" });
  await expect(startButton).toHaveCount(1);
  await startButton.dblclick();

  const jobResponse = await jobResponsePromise;
  expect(jobResponse.status()).toBe(200);
  const body = (await jobResponse.json()) as { job_id: string };
  expect(body.job_id).toMatch(/^vc_/);

  const resultHeadings = page.getByRole("heading", {
    name: /^结果 · job/,
  });
  await expect(resultHeadings).toHaveCount(1);
  await expect(
    page.getByRole("heading", {
      name: `结果 · job ${body.job_id}`,
      exact: true,
    }),
  ).toBeVisible();
  await page.waitForLoadState("networkidle");

  expect(jobRequests).toHaveLength(1);
  expect(jobResponses.map((response) => response.status())).toEqual([200]);
  await expect(resultHeadings).toHaveCount(1);
  expectNoBrowserFailures(failures);
});
