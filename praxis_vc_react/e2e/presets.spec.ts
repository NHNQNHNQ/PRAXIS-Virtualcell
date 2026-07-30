import { expect, test, type Page } from "@playwright/test";

type BrowserFailures = {
  pageErrors: string[];
  consoleErrors: string[];
  http500: string[];
};

type PresetTruth = {
  id: string;
  label: string;
  species: "human" | "mouse" | "yeast" | "bacteria";
  cellType: string;
  perturbationType: "gene";
  targets: string[];
  abstain: boolean;
  abstainReason?: "all_predictors_rejected";
};

const PRESETS: PresetTruth[] = [
  {
    id: "human_k562",
    label: "K562 — human CML (Norman perturb-seq)",
    species: "human",
    cellType: "K562",
    perturbationType: "gene",
    targets: ["AHR", "GATA1"],
    abstain: false,
  },
  {
    id: "mouse_tcell",
    label: "T cell — mouse (ortholog 迁移)",
    species: "mouse",
    cellType: "T cell",
    perturbationType: "gene",
    targets: ["Gata1"],
    abstain: false,
  },
  {
    id: "yeast_scerevisiae",
    label: "S. cerevisiae — yeast GEM (Yeast8)",
    species: "yeast",
    cellType: "S. cerevisiae",
    perturbationType: "gene",
    targets: ["YBR166C"],
    abstain: true,
    abstainReason: "all_predictors_rejected",
  },
  {
    id: "ecoli_iml1515",
    label: "E. coli — iML1515 GEM (KO 生长)",
    species: "bacteria",
    cellType: "E. coli",
    perturbationType: "gene",
    targets: ["b0720"],
    abstain: true,
    abstainReason: "all_predictors_rejected",
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

async function choosePreset(page: Page, presetTruth: PresetTruth): Promise<void> {
  await page.goto("/");
  await page.getByRole("button", { name: "Agent Workspace", exact: true }).click();
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

  const [parseResponse, optionsResponse] = await Promise.all([
    parseResponsePromise,
    optionsResponsePromise,
  ]);
  expect(parseResponse.status()).toBe(200);
  expect(optionsResponse.status()).toBe(200);
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();

  const options = (await optionsResponse.json()) as {
    cell_presets: Array<{
      id: string;
      label: string;
      species: string;
      cell_type: string;
      example_perturbation_type: string;
      example_targets: string[];
    }>;
  };
  expect(options.cell_presets).toContainEqual(
    expect.objectContaining({
      id: presetTruth.id,
      label: presetTruth.label,
      species: presetTruth.species,
      cell_type: presetTruth.cellType,
      example_perturbation_type: presetTruth.perturbationType,
      example_targets: presetTruth.targets,
    }),
  );

  const presetSelect = page.getByLabel("载入常用体系(可再手改)");
  const comboboxes = page.getByRole("combobox");
  const textboxes = page.getByRole("textbox");
  await expect(comboboxes).toHaveCount(3);
  await expect(textboxes).toHaveCount(2);

  await presetSelect.selectOption({ label: presetTruth.label });
  await expect(presetSelect).toHaveValue(presetTruth.id);
  await expect(comboboxes.nth(1)).toHaveValue(presetTruth.species);
  await expect(comboboxes.nth(2)).toHaveValue(presetTruth.perturbationType);
  await expect(textboxes.nth(0)).toHaveValue(presetTruth.cellType);
  await expect(textboxes.nth(1)).toHaveValue(presetTruth.targets.join(", "));
}

async function runToResults(page: Page): Promise<{
  submittedRequest: Record<string, unknown>;
  structuredReport: {
    abstain: boolean;
    abstain_reasons: string[];
    prediction: unknown;
  };
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
    structured_report: {
      abstain: boolean;
      abstain_reasons: string[];
      prediction: unknown;
    };
  };
  return {
    submittedRequest: submitted.request,
    structuredReport: report.structured_report,
  };
}

for (const presetTruth of PRESETS) {
  test(`S5 常用体系预设真实回填并运行 · ${presetTruth.id}`, async ({ page }) => {
    const failures = collectBrowserFailures(page);
    await choosePreset(page, presetTruth);
    const { submittedRequest, structuredReport } = await runToResults(page);

    expect(submittedRequest.species).toBe(presetTruth.species);
    expect(submittedRequest.cell_type).toBe(presetTruth.cellType);
    expect(submittedRequest.perturbation_type).toBe(presetTruth.perturbationType);
    expect(submittedRequest.perturbation_targets).toEqual(presetTruth.targets);
    expect(structuredReport.abstain).toBe(presetTruth.abstain);

    const resultRegion = page.getByRole("region", { name: /^结果 · job/ });
    if (presetTruth.abstain) {
      expect(structuredReport.prediction).toBeNull();
      expect(structuredReport.abstain_reasons).toContain(
        presetTruth.abstainReason,
      );
      await expect(
        resultRegion.getByText("本次未给出预测结论", { exact: true }),
      ).toBeVisible();
      await expect(
        resultRegion.getByText(presetTruth.abstainReason as string, {
          exact: true,
        }),
      ).toBeVisible();
      await page.getByRole("tab", { name: "预测" }).click();
      await expect(
        page.getByText("可靠性判定与原因见「报告」。", { exact: true }),
      ).toBeVisible();
    } else {
      expect(structuredReport.prediction).not.toBeNull();
      await expect(
        resultRegion.getByText("已给出预测", { exact: true }),
      ).toBeVisible();
      await page.getByRole("tab", { name: "预测" }).click();
      await expect(page.getByRole("heading", { name: "结果可靠性" })).toBeVisible();
    }

    expectNoBrowserFailures(failures);
  });
}
