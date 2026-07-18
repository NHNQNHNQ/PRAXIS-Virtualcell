import { expect, test, type Page } from "@playwright/test";

type BrowserFailures = {
  pageErrors: string[];
  consoleErrors: string[];
  http500: string[];
};

type RunResponses = {
  jobResponse: Awaited<ReturnType<Page["waitForResponse"]>>;
  reportResponse: Awaited<ReturnType<Page["waitForResponse"]>>;
  modulePlanResponse: Awaited<ReturnType<Page["waitForResponse"]>>;
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

async function parseToReview(page: Page, query: string): Promise<Record<string, unknown>> {
  await page.goto("/");
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

  const parseResponse = await parseResponsePromise;
  expect(parseResponse.status()).toBe(200);
  const parsed = (await parseResponse.json()) as Record<string, unknown>;
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  return parsed;
}

async function continueToResults(page: Page): Promise<RunResponses> {
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
  const reportResponsePromise = page.waitForResponse((response) => {
    const path = new URL(response.url()).pathname;
    return (
      /^\/api\/reports\/[^/]+$/.test(path) &&
      response.request().method() === "GET"
    );
  });
  const modulePlanResponsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/module-plan") &&
      response.request().method() === "GET",
  );

  await page.getByRole("button", { name: "开始运行 →" }).click();
  const [jobResponse, reportResponse, modulePlanResponse] = await Promise.all([
    jobResponsePromise,
    reportResponsePromise,
    modulePlanResponsePromise,
  ]);

  expect(jobResponse.status()).toBe(200);
  expect(reportResponse.status()).toBe(200);
  expect(modulePlanResponse.status()).toBe(200);
  await expect(page.getByRole("heading", { name: /^结果 · job/ })).toBeVisible();

  return { jobResponse, reportResponse, modulePlanResponse };
}

test("human gene FASN OOV 显示弃权原因、预测空态且可新建查询", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  const parsed = await parseToReview(page, "在 human 细胞敲 FASN");
  const candidate = parsed.candidate_request as Record<string, unknown>;
  expect(candidate.species).toBe("human");
  expect(candidate.perturbation_type).toBe("gene");
  expect(candidate.perturbation_targets).toEqual(["FASN"]);
  expect(candidate.output_modality).toBe("delta_expression");

  const { reportResponse } = await continueToResults(page);
  const report = (await reportResponse.json()) as {
    structured_report: {
      abstain: boolean;
      abstain_reasons: string[];
      prediction: unknown;
    };
  };
  expect(report.structured_report.abstain).toBe(true);
  expect(report.structured_report.abstain_reasons).toContain(
    "learned_abstain_low_reliability",
  );
  expect(report.structured_report.prediction).toBeNull();

  await expect(
    page.getByText("本次未给出预测结论", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("learned_abstain_low_reliability", { exact: true }),
  ).toBeVisible();

  await page.getByRole("tab", { name: "预测" }).click();
  await expect(
    page.getByText("本次未给出预测结论", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("可靠性判定与原因见「报告」。", { exact: true }),
  ).toBeVisible();

  await page
    .getByRole("group", { name: "结果操作" })
    .getByRole("button", { name: "＋ 新建查询", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验" }),
  ).toBeVisible();
  await expect(page.getByLabel("研究问题")).toHaveValue("在 human 细胞敲 AHR");
  expectNoBrowserFailures(failures);
});

test("bacteria gene b0720 expression 显示模块路由与预测空态", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  const parsed = await parseToReview(page, "在 human 细胞敲 AHR");
  const candidate = parsed.candidate_request as Record<string, unknown>;
  expect(candidate.output_modality).toBe("delta_expression");

  // Review 的三个 combobox 依次为预设、物种、扰动类型；两个 textbox
  // 依次为细胞类型、扰动对象。全程只按可访问角色定位，不依赖样式或 test id。
  await expect(page.getByRole("combobox")).toHaveCount(3);
  await expect(page.getByRole("textbox")).toHaveCount(2);
  await page.getByRole("combobox").nth(1).selectOption("bacteria");
  await page.getByRole("combobox").nth(2).selectOption("gene");
  await page.getByRole("textbox").nth(1).fill("b0720");

  const { jobResponse, reportResponse, modulePlanResponse } =
    await continueToResults(page);
  const submitted = jobResponse.request().postDataJSON() as {
    request: Record<string, unknown>;
  };
  expect(submitted.request.species).toBe("bacteria");
  expect(submitted.request.perturbation_type).toBe("gene");
  expect(submitted.request.perturbation_targets).toEqual(["b0720"]);
  expect(submitted.request.output_modality).toBe("delta_expression");

  const report = (await reportResponse.json()) as {
    structured_report: {
      abstain: boolean;
      abstain_reasons: string[];
      prediction: unknown;
    };
  };
  expect(report.structured_report.abstain).toBe(true);
  expect(report.structured_report.abstain_reasons).toContain(
    "all_predictors_rejected",
  );
  expect(report.structured_report.prediction).toBeNull();
  expect(await modulePlanResponse.json()).toEqual({ module_plan: {} });

  await page.getByRole("tab", { name: "模块路由" }).click();
  await expect(page.getByText("未产生模块路由", { exact: true })).toBeVisible();
  await expect(
    page.getByText(
      "本次运行未产生可展示的主/辅模块路由(不可路由或已弃权)。",
      { exact: true },
    ),
  ).toBeVisible();

  await page.getByRole("tab", { name: "预测" }).click();
  await expect(
    page.getByText("本次未给出预测结论", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("可靠性判定与原因见「报告」。", { exact: true }),
  ).toBeVisible();
  expectNoBrowserFailures(failures);
});
