import { expect, test, type Page } from "@playwright/test";

type BrowserFailures = {
  pageErrors: string[];
  consoleErrors: string[];
  httpServerErrors: string[];
  dialogs: string[];
  mutatingRequests: string[];
};

type ParseBody = {
  candidate_request: {
    species?: unknown;
    perturbation_targets?: unknown;
  };
  missing_fields: string[];
  clarification_required: boolean;
};

function collectBrowserFailures(page: Page): BrowserFailures {
  const failures: BrowserFailures = {
    pageErrors: [],
    consoleErrors: [],
    httpServerErrors: [],
    dialogs: [],
    mutatingRequests: [],
  };

  page.on("pageerror", (error) => failures.pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") failures.consoleErrors.push(message.text());
  });
  page.on("response", (response) => {
    if (response.status() >= 500) {
      failures.httpServerErrors.push(
        `${response.status()} ${response.request().method()} ${response.url()}`,
      );
    }
  });
  page.on("dialog", (dialog) => {
    failures.dialogs.push(`${dialog.type()}: ${dialog.message()}`);
    void dialog.dismiss();
  });
  page.on("request", (request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) {
      failures.mutatingRequests.push(
        `${request.method()} ${new URL(request.url()).pathname}`,
      );
    }
  });

  return failures;
}

function expectNoBrowserFailures(
  failures: BrowserFailures,
  expectedMutations: string[],
): void {
  expect(failures.pageErrors).toEqual([]);
  expect(failures.consoleErrors).toEqual([]);
  expect(failures.httpServerErrors).toEqual([]);
  expect(failures.dialogs).toEqual([]);
  expect(failures.mutatingRequests).toEqual(expectedMutations);
}

async function openAsk(page: Page): Promise<void> {
  const healthResponsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/health") &&
      response.request().method() === "GET",
  );
  const jobsResponsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/jobs") &&
      response.request().method() === "GET",
  );

  await page.goto("/");
  await page.getByRole("button", { name: "Agent Workspace", exact: true }).click();
  const [healthResponse, jobsResponse] = await Promise.all([
    healthResponsePromise,
    jobsResponsePromise,
  ]);
  expect(healthResponse.status()).toBe(200);
  expect(jobsResponse.status()).toBe(200);
  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验" }),
  ).toBeVisible();
}

async function submitForReview(page: Page, query: string): Promise<ParseBody> {
  await page.getByLabel("研究问题").fill(query);

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
    text: query,
    mode: "offline",
  });
  await expect(
    page.getByRole("heading", { name: "核对任务解读" }),
  ).toBeVisible();
  return (await parseResponse.json()) as ParseBody;
}

test("空研究问题禁用解读任务", async ({ page }) => {
  const failures = collectBrowserFailures(page);
  await openAsk(page);

  await page.getByLabel("研究问题").fill("");
  await expect(
    page.getByRole("button", { name: "解读任务 →" }),
  ).toBeDisabled();

  expectNoBrowserFailures(failures, []);
});

test("Review 缺失 species 时禁止继续并显示澄清", async ({ page }) => {
  const failures = collectBrowserFailures(page);
  await openAsk(page);
  const parsed = await submitForReview(page, "AHR");

  expect(parsed.missing_fields).toContain("species");
  expect(parsed.clarification_required).toBe(true);
  expect(parsed.candidate_request.species).toBe("");
  await expect(page.getByText(/尚缺信息:.*species/)).toBeVisible();
  await expect(
    page.getByText("这项描述还需进一步澄清后再运行。", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "确认并继续 →" }),
  ).toBeDisabled();

  expectNoBrowserFailures(failures, ["POST /api/parse"]);
});

const boundaryCases: Array<{
  name: string;
  query: string;
  expectedMissing: string[];
  expectedSpecies: string;
  expectedTargets?: string[];
  clarificationRequired: boolean;
}> = [
  {
    name: "超长输入",
    query: `human AHR ${"🧬".repeat(20_000)}`,
    expectedMissing: [],
    expectedSpecies: "human",
    expectedTargets: ["AHR"],
    clarificationRequired: false,
  },
  {
    name: "emoji 输入",
    query: "🧬🧪",
    expectedMissing: ["species", "perturbation_targets"],
    expectedSpecies: "",
    expectedTargets: [],
    clarificationRequired: true,
  },
  {
    name: "script payload",
    query: '<script>alert("PRAXIS_XSS")</script>',
    expectedMissing: ["species", "perturbation_targets"],
    expectedSpecies: "",
    expectedTargets: [],
    clarificationRequired: true,
  },
  {
    name: "SQL-like payload",
    query: "AHR;DROP TABLE jobs",
    expectedMissing: ["species"],
    expectedSpecies: "",
    clarificationRequired: true,
  },
];

for (const boundaryCase of boundaryCases) {
  test(`${boundaryCase.name} 只解析到 Review 且无执行或服务错误`, async ({
    page,
  }) => {
    const failures = collectBrowserFailures(page);
    await openAsk(page);
    const parsed = await submitForReview(page, boundaryCase.query);

    expect(parsed.missing_fields).toEqual(boundaryCase.expectedMissing);
    expect(parsed.clarification_required).toBe(
      boundaryCase.clarificationRequired,
    );
    expect(parsed.candidate_request.species).toBe(boundaryCase.expectedSpecies);
    if (boundaryCase.expectedTargets !== undefined) {
      expect(parsed.candidate_request.perturbation_targets).toEqual(
        boundaryCase.expectedTargets,
      );
    }

    const continueButton = page.getByRole("button", {
      name: "确认并继续 →",
    });
    if (boundaryCase.clarificationRequired) {
      await expect(
        page.getByText("这项描述还需进一步澄清后再运行。", { exact: true }),
      ).toBeVisible();
      await expect(continueButton).toBeDisabled();
    } else {
      await expect(
        page.getByText("这项描述还需进一步澄清后再运行。", { exact: true }),
      ).toHaveCount(0);
      await expect(continueButton).toBeEnabled();
    }

    // 不点击继续：唯一写请求必须是纯解析 POST，不能产生 /api/jobs。
    expectNoBrowserFailures(failures, ["POST /api/parse"]);
  });
}
