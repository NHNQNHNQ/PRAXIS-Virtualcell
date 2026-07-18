import { expect, test, type Page } from "@playwright/test";

const QUERY = "在 human 细胞敲 AHR";

type BrowserFailures = {
  pageErrors: string[];
  consoleErrors: string[];
  http500: string[];
};

type CapturedTruth = {
  submitted: Record<string, unknown>;
  job: Record<string, unknown>;
  report: Record<string, unknown>;
  modulePlan: Record<string, unknown>;
};

type StableTruth = {
  submission: {
    mode: unknown;
    enableLlmReport: unknown;
    species: unknown;
    perturbationType: unknown;
    perturbationTargets: unknown;
    inputModality: unknown;
    outputModality: unknown;
    taskType: unknown;
    cellType: unknown;
  };
  report: {
    prediction: unknown;
    abstain: unknown;
    reliability: unknown;
    modelsUsed: unknown;
    learnedReliability: {
      mode: unknown;
      fallback: unknown;
      score: unknown;
      abstainDecision: unknown;
    };
  };
  modulePlan: {
    primary: unknown;
    secondary: unknown;
    overallVerdict: unknown;
  };
};

function asRecord(value: unknown): Record<string, unknown> {
  return value != null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
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

function stableTruth(captured: CapturedTruth): StableTruth {
  const submittedRequest = asRecord(captured.submitted.request);
  const structuredReport = asRecord(captured.report.structured_report);
  const learnedReliability = asRecord(structuredReport.learned_reliability);
  const modulePlan = asRecord(captured.modulePlan.module_plan);

  // 只选取同一业务请求应稳定的字段。job_id、request_id、时间、trace/message
  // 标识以及带 job_id 的下载 URL 都刻意不进入跨运行比较。
  return {
    submission: {
      mode: captured.submitted.mode,
      enableLlmReport: captured.submitted.enable_llm_report,
      species: submittedRequest.species,
      perturbationType: submittedRequest.perturbation_type,
      perturbationTargets: submittedRequest.perturbation_targets,
      inputModality: submittedRequest.input_modality,
      outputModality: submittedRequest.output_modality,
      taskType: submittedRequest.task_type,
      cellType: submittedRequest.cell_type,
    },
    report: {
      prediction: structuredReport.prediction,
      abstain: structuredReport.abstain,
      reliability: structuredReport.reliability,
      modelsUsed: structuredReport.models_used,
      learnedReliability: {
        mode: learnedReliability.reliability_mode,
        fallback: learnedReliability.fallback,
        score: learnedReliability.reliability_score,
        abstainDecision: learnedReliability.abstain_decision,
      },
    },
    modulePlan: {
      primary: modulePlan.primary,
      secondary: modulePlan.secondary,
      overallVerdict: modulePlan.overall_verdict,
    },
  };
}

async function runFromAskToResults(page: Page): Promise<CapturedTruth> {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验" }),
  ).toBeVisible();
  await page.getByLabel("研究问题").fill(QUERY);

  const parseResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/parse") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "解读任务 →" }).click();
  const parseResponse = await parseResponsePromise;
  expect(parseResponse.status()).toBe(200);

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

  return {
    submitted: jobResponse.request().postDataJSON() as Record<string, unknown>,
    job: (await jobResponse.json()) as Record<string, unknown>,
    report: (await reportResponse.json()) as Record<string, unknown>,
    modulePlan: (await modulePlanResponse.json()) as Record<string, unknown>,
  };
}

async function expectTruthVisible(page: Page, truth: StableTruth): Promise<void> {
  expect(truth.report.abstain).toBe(false);
  await expect(page.getByText("已给出预测", { exact: true })).toBeVisible();

  const modelsUsed = Array.isArray(truth.report.modelsUsed)
    ? truth.report.modelsUsed.map(String).join(", ")
    : "";
  expect(modelsUsed).not.toBe("");
  await expect(page.getByText(modelsUsed, { exact: true })).toHaveCount(1);
  await expect(page.getByText(modelsUsed, { exact: true })).toBeVisible();

  const reliability = String(truth.report.reliability);
  await expect(page.getByText(reliability, { exact: true })).toHaveCount(1);
  await expect(page.getByText(reliability, { exact: true })).toBeVisible();

  await page.getByRole("tab", { name: "预测" }).click();
  await expect(page.getByRole("heading", { name: "结果可靠性" })).toBeVisible();
  const score = truth.report.learnedReliability.score;
  expect(typeof score).toBe("number");
  await expect(
    page.getByRole("img", { name: `可靠性 ${(score as number).toFixed(2)}` }),
  ).toBeVisible();

  await page.getByRole("tab", { name: "模块路由" }).click();
  await expect(page.getByRole("heading", { name: "路由摘要" })).toBeVisible();
  const primaryMatches = page.getByText(String(truth.modulePlan.primary), {
    exact: true,
  });
  const primaryMatchCount = await primaryMatches.count();
  expect(primaryMatchCount).toBeGreaterThan(0);
  await expect(primaryMatches.nth(0)).toBeVisible();
}

test("同一 AHR 查询三次运行的关键业务真值保持确定", async ({ page }) => {
  const failures = collectBrowserFailures(page);
  const captures: CapturedTruth[] = [];
  const stableTruths: StableTruth[] = [];

  for (let run = 0; run < 3; run += 1) {
    const captured = await runFromAskToResults(page);
    const truth = stableTruth(captured);
    captures.push(captured);
    stableTruths.push(truth);

    // 每次 POST /api/jobs 的请求体、响应及随后 report/module-plan 响应都已捕获；
    // 同时验证 Results 与关键模型、可靠性、预测状态、primary 在 UI 可观察。
    expect(captured.job.status).toBe("done");
    await expectTruthVisible(page, truth);
  }

  expect(captures).toHaveLength(3);
  expect(stableTruths).toHaveLength(3);
  const baseline = stableTruths[0];
  for (const truth of stableTruths.slice(1)) {
    expect(truth).toEqual(baseline);
  }

  expect(failures.pageErrors).toEqual([]);
  expect(failures.consoleErrors).toEqual([]);
  expect(failures.http500).toEqual([]);
});
