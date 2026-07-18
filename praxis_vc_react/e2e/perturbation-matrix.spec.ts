import { expect, test, type Page } from "@playwright/test";

type BrowserFailures = {
  pageErrors: string[];
  consoleErrors: string[];
  http500: string[];
};

type MatrixCase = {
  name: string;
  species: "human" | "mouse" | "yeast" | "bacteria";
  cellType: string;
  perturbationType:
    | "gene"
    | "gene_combination"
    | "drug"
    | "ligand"
    | "medium";
  targets: string[];
  abstain: boolean;
  abstainReason?: string;
  emptyRouting: boolean;
};

type StructuredOutputCase = {
  name: string;
  species: "human" | "bacteria";
  cellType: string;
  perturbationType: "gene" | "ligand";
  targets: string[];
  normalizedTargets?: string[];
  outputModality: "growth" | "state";
  expectedDelta: number[];
};

const MATRIX: MatrixCase[] = [
  {
    name: "human gene AHR",
    species: "human",
    cellType: "K562",
    perturbationType: "gene",
    targets: ["AHR"],
    abstain: false,
    emptyRouting: false,
  },
  {
    name: "mouse gene_combination Gata1 + Myc",
    species: "mouse",
    cellType: "T cell",
    perturbationType: "gene_combination",
    targets: ["Gata1", "Myc"],
    abstain: false,
    emptyRouting: false,
  },
  {
    name: "human drug vorinostat",
    species: "human",
    cellType: "A549",
    perturbationType: "drug",
    targets: ["vorinostat"],
    abstain: false,
    emptyRouting: false,
  },
  {
    name: "human ligand IFNB1",
    species: "human",
    cellType: "PBMC",
    perturbationType: "ligand",
    targets: ["IFNB1"],
    abstain: true,
    abstainReason: "all_predictors_rejected",
    emptyRouting: false,
  },
  {
    name: "bacteria medium acetate",
    species: "bacteria",
    cellType: "E. coli",
    perturbationType: "medium",
    targets: ["acetate"],
    abstain: true,
    abstainReason: "all_predictors_rejected",
    emptyRouting: true,
  },
  {
    name: "yeast gene YBR166C",
    species: "yeast",
    cellType: "S. cerevisiae",
    perturbationType: "gene",
    targets: ["YBR166C"],
    abstain: true,
    abstainReason: "all_predictors_rejected",
    emptyRouting: true,
  },
];

const STRUCTURED_OUTPUT_CASES: StructuredOutputCase[] = [
  {
    name: "bacteria gene b0720 + b1136 growth",
    species: "bacteria",
    cellType: "E. coli",
    perturbationType: "gene",
    targets: ["b0720", "b1136"],
    normalizedTargets: ["B0720", "B1136"],
    outputModality: "growth",
    expectedDelta: [-1, -1],
  },
  {
    name: "human ligand IFNB1 state",
    species: "human",
    cellType: "PBMC",
    perturbationType: "ligand",
    targets: ["IFNB1"],
    outputModality: "state",
    expectedDelta: [2.485],
  },
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

async function reachReviewAndEdit(page: Page, matrixCase: MatrixCase): Promise<void> {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验" }),
  ).toBeVisible();
  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");

  const parseResponsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/parse") &&
      response.request().method() === "POST",
  );
  const optionsResponsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/options") &&
      response.request().method() === "GET",
  );
  await page.getByRole("button", { name: "解读任务 →" }).click();

  const parseResponse = await parseResponsePromise;
  expect(parseResponse.status()).toBe(200);
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();

  const optionsResponse = await optionsResponsePromise;
  expect(optionsResponse.status()).toBe(200);
  const options = (await optionsResponse.json()) as {
    species: string[];
    perturbation_type: string[];
  };
  expect(options.species).toContain(matrixCase.species);
  expect(options.perturbation_type).toContain(matrixCase.perturbationType);

  // Review 有三个 combobox(预设、物种、扰动类型)和两个 textbox(细胞类型、扰动对象)。
  // nth 前先钉死可访问控件数量，避免 UI 结构变化时悄悄编辑错字段。
  const comboboxes = page.getByRole("combobox");
  const textboxes = page.getByRole("textbox");
  await expect(comboboxes).toHaveCount(3);
  await expect(textboxes).toHaveCount(2);
  expect(await comboboxes.count()).toBe(3);
  expect(await textboxes.count()).toBe(2);

  await comboboxes.nth(1).selectOption(matrixCase.species);
  await comboboxes.nth(2).selectOption(matrixCase.perturbationType);
  await textboxes.nth(0).fill(matrixCase.cellType);
  await textboxes.nth(1).fill(matrixCase.targets.join(", "));

  await expect(comboboxes.nth(1)).toHaveValue(matrixCase.species);
  await expect(comboboxes.nth(2)).toHaveValue(matrixCase.perturbationType);
  await expect(textboxes.nth(0)).toHaveValue(matrixCase.cellType);
  await expect(textboxes.nth(1)).toHaveValue(matrixCase.targets.join(", "));
}

async function reachReviewFromStructuredInput(
  page: Page,
  outputCase: StructuredOutputCase,
): Promise<void> {
  const normalizedTargets = outputCase.normalizedTargets ?? outputCase.targets;
  const question = "请执行以下结构化非表达输出任务";
  const structuredDescription = JSON.stringify({
    species: outputCase.species,
    cell_type: outputCase.cellType,
    perturbation_type: outputCase.perturbationType,
    perturbation_targets: outputCase.targets,
    output_modality: outputCase.outputModality,
  });

  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验" }),
  ).toBeVisible();
  await page.getByLabel("研究问题").fill(question);
  await page.getByText("高级输入(可选)", { exact: true }).click();
  await page
    .getByLabel("结构化描述(可留空)")
    .fill(structuredDescription);

  const parseResponsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/parse") &&
      response.request().method() === "POST",
  );
  const optionsResponsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/options") &&
      response.request().method() === "GET",
  );
  await page.getByRole("button", { name: "解读任务 →" }).click();

  const [parseResponse, optionsResponse] = await Promise.all([
    parseResponsePromise,
    optionsResponsePromise,
  ]);
  expect(parseResponse.status()).toBe(200);
  expect(optionsResponse.status()).toBe(200);
  expect(parseResponse.request().postDataJSON()).toEqual({
    text: `${question}\n结构化描述:${structuredDescription}`,
    mode: "offline",
  });

  const parsed = (await parseResponse.json()) as {
    candidate_request: Record<string, unknown>;
    schema_valid: boolean;
    clarification_required: boolean;
  };
  expect(parsed.schema_valid).toBe(true);
  expect(parsed.clarification_required).toBe(false);
  expect(parsed.candidate_request).toMatchObject({
    species: outputCase.species,
    cell_type: outputCase.cellType,
    perturbation_type: outputCase.perturbationType,
    perturbation_targets: normalizedTargets,
    output_modality: outputCase.outputModality,
  });

  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  const comboboxes = page.getByRole("combobox");
  const textboxes = page.getByRole("textbox");
  await expect(comboboxes).toHaveCount(3);
  await expect(textboxes).toHaveCount(2);
  await expect(comboboxes.nth(1)).toHaveValue(outputCase.species);
  await expect(comboboxes.nth(2)).toHaveValue(outputCase.perturbationType);
  await expect(textboxes.nth(0)).toHaveValue(outputCase.cellType);
  await expect(textboxes.nth(1)).toHaveValue(normalizedTargets.join(", "));
}

async function submitAndReachResults(page: Page): Promise<{
  submittedRequest: Record<string, unknown>;
  structuredReport: Record<string, unknown>;
}> {
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

  await page.getByRole("button", { name: "开始运行 →" }).click();
  const [jobResponse, reportResponse] = await Promise.all([
    jobResponsePromise,
    reportResponsePromise,
  ]);
  expect(jobResponse.status()).toBe(200);
  expect(reportResponse.status()).toBe(200);
  await expect(page.getByRole("heading", { name: /^结果 · job/ })).toBeVisible();

  const submitted = jobResponse.request().postDataJSON() as {
    request: Record<string, unknown>;
  };
  const report = (await reportResponse.json()) as {
    structured_report: Record<string, unknown>;
  };
  return {
    submittedRequest: submitted.request,
    structuredReport: report.structured_report,
  };
}

for (const matrixCase of MATRIX) {
  test(`S4 Review 扰动矩阵 · ${matrixCase.name}`, async ({ page }) => {
    const failures = collectBrowserFailures(page);
    await reachReviewAndEdit(page, matrixCase);
    const { submittedRequest, structuredReport } = await submitAndReachResults(page);

    expect(submittedRequest.species).toBe(matrixCase.species);
    expect(submittedRequest.cell_type).toBe(matrixCase.cellType);
    expect(submittedRequest.perturbation_type).toBe(matrixCase.perturbationType);
    expect(submittedRequest.perturbation_targets).toEqual(matrixCase.targets);
    expect(structuredReport.abstain).toBe(matrixCase.abstain);

    const resultRegion = page.getByRole("region", { name: /^结果 · job/ });
    await expect(
      resultRegion.getByText("结果由确定性模型给出,未经语言模型改写", {
        exact: true,
      }),
    ).toBeVisible();

    if (matrixCase.abstain) {
      const reasons = Array.isArray(structuredReport.abstain_reasons)
        ? structuredReport.abstain_reasons.map(String)
        : [];
      expect(reasons).toContain(matrixCase.abstainReason);
      await expect(
        resultRegion.getByText("本次未给出预测结论", { exact: true }),
      ).toBeVisible();

      await page.getByRole("tab", { name: "预测" }).click();
      await expect(
        page.getByText("可靠性判定与原因见「报告」。", { exact: true }),
      ).toBeVisible();

      await page.getByRole("tab", { name: "模块路由" }).click();
      if (matrixCase.emptyRouting) {
        await expect(
          resultRegion.getByText("未产生模块路由", { exact: true }),
        ).toBeVisible();
      } else {
        await expect(page.getByRole("heading", { name: "路由摘要" })).toBeVisible();
      }
    } else {
      await expect(
        resultRegion.getByText("已给出预测", { exact: true }),
      ).toBeVisible();
      await page.getByRole("tab", { name: "预测" }).click();
      await expect(page.getByRole("heading", { name: "结果可靠性" })).toBeVisible();
    }

    expectNoBrowserFailures(failures);
  });
}

for (const outputCase of STRUCTURED_OUTPUT_CASES) {
  test(`S4 高级输入非 expression 正例 · ${outputCase.name}`, async ({ page }) => {
    const normalizedTargets = outputCase.normalizedTargets ?? outputCase.targets;
    const failures = collectBrowserFailures(page);
    await reachReviewFromStructuredInput(page, outputCase);
    const { submittedRequest, structuredReport } = await submitAndReachResults(page);

    expect(submittedRequest).toMatchObject({
      species: outputCase.species,
      cell_type: outputCase.cellType,
      perturbation_type: outputCase.perturbationType,
      perturbation_targets: normalizedTargets,
      output_modality: outputCase.outputModality,
    });
    expect(structuredReport.abstain).toBe(false);
    expect(structuredReport.models_used).toEqual(["CaseRunner"]);
    const prediction = structuredReport.prediction as {
      delta?: unknown;
    } | null;
    expect(prediction).not.toBeNull();
    expect(prediction?.delta).toEqual(outputCase.expectedDelta);

    const resultRegion = page.getByRole("region", { name: /^结果 · job/ });
    await expect(
      resultRegion.getByText("已给出预测", { exact: true }),
    ).toBeVisible();
    await page.getByRole("tab", { name: "预测" }).click();
    await expect(page.getByRole("heading", { name: "结果可靠性" })).toBeVisible();
    expectNoBrowserFailures(failures);
  });
}
