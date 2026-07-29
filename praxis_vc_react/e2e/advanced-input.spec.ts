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

async function openAdvancedInput(page: Page): Promise<void> {
  await page.goto("/");
  await page.getByRole("button", { name: "Agent Runs", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验" }),
  ).toBeVisible();
  await page.getByText("高级输入(可选)", { exact: true }).click();
  await expect(page.getByLabel("物种(可留空)")).toBeVisible();
  await expect(page.getByLabel("结构化描述(可留空)")).toBeVisible();
}

async function continueToResults(page: Page) {
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
  const traceResponsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/trace") &&
      response.request().method() === "GET",
  );
  const provenanceResponsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/provenance") &&
      response.request().method() === "GET",
  );
  const modulePlanResponsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/module-plan") &&
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

  expect(jobResponse.status()).toBe(200);
  expect(reportResponse.status()).toBe(200);
  expect(traceResponse.status()).toBe(200);
  expect(provenanceResponse.status()).toBe(200);
  expect(modulePlanResponse.status()).toBe(200);
  await expect(page.getByRole("heading", { name: /^结果 · job/ })).toBeVisible();
  return jobResponse;
}

test("合法高级输入随原问题提交，Review 与运行 payload 保持一致并到达 Results", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  const question = "请执行以下结构化任务";
  const structuredJson = JSON.stringify({
    species: "human",
    perturbation_type: "gene",
    perturbation_targets: ["AHR"],
    output_modality: "delta_expression",
  });
  const composedQuestion = `${question}\n物种:human\n结构化描述:${structuredJson}`;

  await openAdvancedInput(page);
  await page.getByLabel("研究问题").fill(question);
  await page.getByLabel("物种(可留空)").selectOption("human");
  await page.getByLabel("结构化描述(可留空)").fill(structuredJson);

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
  const optionsResponse = await optionsResponsePromise;

  expect(parseResponse.status()).toBe(200);
  expect(optionsResponse.status()).toBe(200);
  expect(parseResponse.request().postDataJSON()).toEqual({
    text: composedQuestion,
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
    species: "human",
    perturbation_type: "gene",
    perturbation_targets: ["AHR"],
    output_modality: "delta_expression",
  });

  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  const reviewComboboxes = page.getByRole("combobox");
  await expect(reviewComboboxes).toHaveCount(3);
  await expect(reviewComboboxes.nth(1)).toHaveValue("human");
  await expect(reviewComboboxes.nth(2)).toHaveValue("gene");
  const reviewTextboxes = page.getByRole("textbox");
  await expect(reviewTextboxes).toHaveCount(2);
  await expect(reviewTextboxes.nth(1)).toHaveValue("AHR");

  const jobResponse = await continueToResults(page);
  const submitted = jobResponse.request().postDataJSON() as {
    request: Record<string, unknown>;
    mode: string;
  };
  expect(submitted.mode).toBe("offline");
  expect(submitted.request).toMatchObject({
    species: "human",
    perturbation_type: "gene",
    perturbation_targets: ["AHR"],
    output_modality: "delta_expression",
  });
  expectNoBrowserFailures(failures);
});

test("结构化扰动对象含非字符串时 Review 不会把对象强转成可运行目标", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  const question = "请核对不可信的结构化目标";
  const structuredJson = JSON.stringify({
    species: "human",
    perturbation_type: "gene",
    perturbation_targets: [{ gene: "AHR" }],
    output_modality: "delta_expression",
  });

  await openAdvancedInput(page);
  await page.getByLabel("研究问题").fill(question);
  await page.getByLabel("结构化描述(可留空)").fill(structuredJson);
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
  const parsed = (await parseResponse.json()) as {
    schema_valid: boolean;
    missing_fields: string[];
  };
  expect(parsed.schema_valid).toBe(false);
  expect(parsed.missing_fields).toContain("perturbation_targets");

  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  const reviewTextboxes = page.getByRole("textbox");
  await expect(reviewTextboxes).toHaveCount(2);
  await expect(reviewTextboxes.nth(1)).toHaveValue("");
  const confirm = page.getByRole("button", { name: "确认并继续 →" });
  await expect(confirm).toBeDisabled();

  await reviewTextboxes.nth(1).fill("AHR");
  await expect(confirm).toBeEnabled();
  expectNoBrowserFailures(failures);
});

test("Review 修正可编辑的非法物种与扰动类型后可以继续", async ({ page }) => {
  const failures = collectBrowserFailures(page);
  const structuredJson = JSON.stringify({
    species: "martian",
    perturbation_type: "mutation",
    perturbation_targets: ["AHR"],
    output_modality: "delta_expression",
  });

  await openAdvancedInput(page);
  await page.getByLabel("研究问题").fill("请核对可编辑字段");
  await page.getByLabel("结构化描述(可留空)").fill(structuredJson);
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
  const parsed = (await parseResponse.json()) as { errors: string[] };
  expect(parsed.errors).toEqual([
    "unsupported_species:martian",
    "unsupported_perturbation_type:mutation",
  ]);

  const confirm = page.getByRole("button", { name: "确认并继续 →" });
  await expect(confirm).toBeDisabled();
  const reviewComboboxes = page.getByRole("combobox");
  await expect(reviewComboboxes).toHaveCount(3);
  await reviewComboboxes.nth(1).selectOption("human");
  await reviewComboboxes.nth(2).selectOption("gene");
  await expect(confirm).toBeEnabled();
  await expect(
    page.getByText("这项描述还需进一步澄清后再运行。", { exact: true }),
  ).toHaveCount(0);
  await expect(page.getByText(/已在当前草稿修正的原始问题/)).toBeVisible();
  await confirm.click();
  await expect(
    page.getByRole("heading", { name: "预计涉及的功能模块" }),
  ).toBeVisible();
  expectNoBrowserFailures(failures);
});

test("选项服务降级为文本输入后仍可修正原始字段错误", async ({ page }) => {
  await page.route("**/api/options", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: "not-json",
    });
  });
  const structuredJson = JSON.stringify({
    species: "martian",
    perturbation_type: "mutation",
    perturbation_targets: ["AHR"],
    output_modality: "delta_expression",
  });

  await openAdvancedInput(page);
  await page.getByLabel("研究问题").fill("请在选项降级时修正字段");
  await page.getByLabel("结构化描述(可留空)").fill(structuredJson);
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();

  const reviewTextboxes = page.getByRole("textbox");
  await expect(reviewTextboxes).toHaveCount(4);
  const confirm = page.getByRole("button", { name: "确认并继续 →" });
  await expect(confirm).toBeDisabled();
  await reviewTextboxes.nth(0).fill("human");
  await reviewTextboxes.nth(2).fill("gene");
  await expect(confirm).toBeEnabled();
});

test("畸形 JSON 与非法值进入真实澄清态，不崩溃且不产生 HTTP 500", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  const question = "请执行以下畸形高级输入";
  const malformedJson =
    '{"species":123,"perturbation_type":"invalid","perturbation_targets":[null],"output_modality":-1';

  await openAdvancedInput(page);
  await page.getByLabel("研究问题").fill(question);
  await page.getByLabel("结构化描述(可留空)").fill(malformedJson);

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
  const optionsResponse = await optionsResponsePromise;

  expect(parseResponse.status()).toBe(200);
  expect(optionsResponse.status()).toBe(200);
  expect(parseResponse.request().postDataJSON()).toEqual({
    text: `${question}\n结构化描述:${malformedJson}`,
    mode: "offline",
  });
  const parsed = (await parseResponse.json()) as {
    schema_valid: boolean;
    missing_fields: string[];
    errors: string[];
    clarification_required: boolean;
  };
  expect(parsed.schema_valid).toBe(false);
  expect(parsed.missing_fields).toEqual([
    "species",
    "perturbation_targets",
  ]);
  expect(parsed.errors).toEqual(["structured_description_malformed"]);
  expect(parsed.clarification_required).toBe(true);

  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  await expect(
    page.getByText("尚缺信息:species, perturbation_targets", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "解读时的问题:structured_description_malformed",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByText("这项描述还需进一步澄清后再运行。", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "确认并继续 →" }),
  ).toBeDisabled();
  expectNoBrowserFailures(failures);
});

test("合法 JSON 的非法 output_modality 返回 schema 错误并阻止继续", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  const question = "请执行以下 schema 非法的高级输入";
  const structuredJson = JSON.stringify({
    species: "human",
    perturbation_type: "gene",
    perturbation_targets: ["AHR"],
    output_modality: "invented_output",
  });

  await openAdvancedInput(page);
  await page.getByLabel("研究问题").fill(question);
  await page.getByLabel("结构化描述(可留空)").fill(structuredJson);

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
  const optionsResponse = await optionsResponsePromise;

  expect(parseResponse.status()).toBe(200);
  expect(optionsResponse.status()).toBe(200);
  expect(parseResponse.request().postDataJSON()).toEqual({
    text: `${question}\n结构化描述:${structuredJson}`,
    mode: "offline",
  });
  const parsed = (await parseResponse.json()) as {
    schema_valid: boolean;
    errors: string[];
    clarification_required: boolean;
  };
  expect(parsed.schema_valid).toBe(false);
  expect(parsed.errors).toEqual([
    "unsupported_output_modality:invented_output",
  ]);
  expect(parsed.clarification_required).toBe(true);

  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  await expect(
    page.getByText(
      "解读时的问题:unsupported_output_modality:invented_output",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "确认并继续 →" }),
  ).toBeDisabled();
  expectNoBrowserFailures(failures);
});
