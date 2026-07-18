import { test, expect, type Page } from "@playwright/test";

type BrowserFailures = {
  pageErrors: string[];
  consoleErrors: string[];
  http500: string[];
};

const failuresByPage = new WeakMap<Page, BrowserFailures>();

test.beforeEach(async ({ page }) => {
  const failures: BrowserFailures = {
    pageErrors: [],
    consoleErrors: [],
    http500: [],
  };
  failuresByPage.set(page, failures);
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
});

test.afterEach(async ({ page }) => {
  const failures = failuresByPage.get(page);
  expect(failures?.pageErrors ?? []).toEqual([]);
  expect(failures?.consoleErrors ?? []).toEqual([]);
  expect(failures?.http500 ?? []).toEqual([]);
});

// 5 阶段 happy path:ask→review→route→run→results 五跳全绿。
// 选择器全走 role/text/label(抗前端 WIP CSS);API 调用是阶段推进的硬证据(waitForResponse)。
test("5 阶段 happy path 五跳到达 Results", async ({ page }) => {
  await page.goto("/");

  // ── 阶段 1:Ask ──(heading + 预填输入 + 点解读任务 → POST /api/parse)
  await expect(page.getByRole("heading", { name: "描述一次扰动实验" })).toBeVisible();
  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");
  const parseResp = page.waitForResponse(
    (r) => r.url().includes("/api/parse") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await parseResp;

  // ── 阶段 2:Review ──(heading 出现 → species 已回填 → 点确认并继续)
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  const reviewNext = page.getByRole("button", { name: "确认并继续 →" });
  await expect(reviewNext).toBeEnabled();
  await reviewNext.click();

  // ── 阶段 3:Route ──(heading + amber 横幅 → 点下一步)
  await expect(page.getByRole("heading", { name: "预计涉及的功能模块" })).toBeVisible();
  await expect(page.getByText("这里是预期,不是实际结果。")).toBeVisible();
  await page.getByRole("button", { name: "下一步 →" }).click();

  // ── 阶段 4:Run ──(heading → 点开始运行 → POST /api/jobs 同步拿 job_id)
  await expect(page.getByRole("heading", { name: "运行前确认" })).toBeVisible();
  const jobsResp = page.waitForResponse(
    (r) => r.url().includes("/api/jobs") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "开始运行 →" }).click();
  await jobsResp;

  // ── 阶段 5:Results ──(heading /^结果 · job/ 出现 = 五跳到达)
  await expect(page.getByRole("heading", { name: /^结果 · job/ })).toBeVisible();
});

test("Review 切换到 Route 时主内容从顶部开始", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();

  const mainScroll = page.getByRole("main");
  await mainScroll.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });
  await expect
    .poll(() => mainScroll.evaluate((element) => element.scrollTop))
    .toBeGreaterThan(0);

  await page.getByRole("button", { name: "确认并继续 →" }).click();

  const routeHeading = page.getByRole("heading", {
    name: "预计涉及的功能模块",
  });
  await expect(routeHeading).toBeInViewport();
  await expect
    .poll(() => mainScroll.evaluate((element) => element.scrollTop))
    .toBe(0);
});

test("Review 返回 Ask 后保留问题与尚未确认的编辑", async ({ page }) => {
  const query = "在 mouse 细胞敲 GATA1";
  await page.goto("/");
  await page.getByLabel("研究问题").fill(query);
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();

  const comboboxes = page.getByRole("combobox");
  const textboxes = page.getByRole("textbox");
  await expect(comboboxes).toHaveCount(3);
  await expect(textboxes).toHaveCount(2);
  await comboboxes.nth(1).selectOption("mouse");
  await textboxes.nth(0).fill("T cell");
  await textboxes.nth(1).fill("GATA1, MYC");

  await page.getByRole("button", { name: "← 返回" }).click();
  await expect(page.getByRole("heading", { name: "描述一次扰动实验" })).toBeVisible();
  await expect(page.getByLabel("研究问题")).toHaveValue(query);

  await page.getByRole("button", { name: "解读任务 →" }).click();
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  await expect(comboboxes).toHaveCount(3);
  await expect(textboxes).toHaveCount(2);
  await expect(comboboxes.nth(1)).toHaveValue("mouse");
  await expect(textboxes.nth(0)).toHaveValue("T cell");
  await expect(textboxes.nth(1)).toHaveValue("GATA1, MYC");
  await expect(
    page.getByRole("button", { name: "路由 查看模块与物种适配" }),
  ).toBeDisabled();

  await page.getByRole("button", { name: "确认并继续 →" }).click();
  await expect(
    page.getByRole("heading", { name: "预计涉及的功能模块" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "运行 确认参数并执行预测" }),
  ).toBeDisabled();
});

test("Route 与 Run 返回后保留已确认的请求", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("研究问题").fill("在 human 细胞敲 TP53");
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  await page.getByRole("button", { name: "确认并继续 →" }).click();
  await expect(
    page.getByRole("heading", { name: "预计涉及的功能模块" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "← 返回" }).click();
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  const textboxes = page.getByRole("textbox");
  await expect(textboxes).toHaveCount(2);
  await expect(textboxes.nth(1)).toHaveValue("TP53");

  await page.getByRole("button", { name: "确认并继续 →" }).click();
  await page.getByRole("button", { name: "下一步 →" }).click();
  await expect(page.getByRole("heading", { name: "运行前确认" })).toBeVisible();
  await page.getByRole("button", { name: "← 返回" }).click();
  await expect(
    page.getByRole("heading", { name: "预计涉及的功能模块" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "下一步 →" }).click();
  await expect(page.getByRole("heading", { name: "运行前确认" })).toBeVisible();
  await expect(page.getByText("TP53", { exact: true })).toBeVisible();
});

test("高级输入返回 Ask 后按字段恢复且不会重复拼接", async ({ page }) => {
  const question = "请运行这个结构化请求";
  const structuredDescription = JSON.stringify({
    species: "mouse",
    perturbation_type: "ligand",
    perturbation_targets: ["IFNB1"],
    output_modality: "state",
  });
  const composed = `${question}\n物种:mouse\n结构化描述:${structuredDescription}`;

  await page.goto("/");
  await page.getByLabel("研究问题").fill(question);
  await page.getByText("高级输入(可选)", { exact: true }).click();
  await page.getByLabel("物种(可留空)").selectOption("mouse");
  await page
    .getByLabel("结构化描述(可留空)")
    .fill(structuredDescription);

  const firstParse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/parse") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "解读任务 →" }).click();
  expect((await firstParse).request().postDataJSON()).toEqual({
    text: composed,
    mode: "offline",
  });
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  await page.getByRole("button", { name: "← 返回" }).click();

  await expect(page.getByLabel("研究问题")).toHaveValue(question);
  await page.getByText("高级输入(可选)", { exact: true }).click();
  await expect(page.getByLabel("物种(可留空)")).toHaveValue("mouse");
  await expect(page.getByLabel("结构化描述(可留空)")).toHaveValue(
    structuredDescription,
  );

  const secondParse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/parse") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "解读任务 →" }).click();
  expect((await secondParse).request().postDataJSON()).toEqual({
    text: composed,
    mode: "offline",
  });
});

test("Ask 中新建查询重置表单且迟到解析不会恢复旧任务", async ({ page }) => {
  let releaseParse!: () => void;
  const parseGate = new Promise<void>((resolve) => {
    releaseParse = resolve;
  });
  await page.route("**/api/parse", async (route) => {
    await parseGate;
    await route.continue();
  });

  await page.goto("/");
  await page.getByLabel("研究问题").fill("在 mouse 细胞敲 GATA1");
  const parseRequest = page.waitForRequest(
    (request) =>
      request.url().endsWith("/api/parse") && request.method() === "POST",
  );
  const parseResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/parse") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await parseRequest;

  const newQuery = page.getByRole("button", {
    name: "＋ 新建查询",
    exact: true,
  });
  await expect(newQuery).toHaveCount(1);
  await newQuery.click();
  await expect(page.getByLabel("研究问题")).toHaveValue("在 human 细胞敲 AHR");

  releaseParse();
  expect((await parseResponse).status()).toBe(200);
  await page.waitForLoadState("networkidle");
  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "核对任务解读" }),
  ).toHaveCount(0);
});

test("已完成任务在 Review 编辑后必须重新路由与运行", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await page.getByRole("button", { name: "确认并继续 →" }).click();
  await page.getByRole("button", { name: "下一步 →" }).click();
  const firstJobResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/jobs") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "开始运行 →" }).click();
  const firstJob = (await (await firstJobResponse).json()) as { job_id: string };
  await expect(page.getByRole("heading", { name: /^结果 · job/ })).toBeVisible();

  await page
    .getByRole("button", { name: "核对 核对并确认解析出的请求" })
    .click();
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  const textboxes = page.getByRole("textbox");
  await expect(textboxes).toHaveCount(2);
  await textboxes.nth(1).fill("TP53");
  await expect(
    page.getByRole("button", { name: "路由 查看模块与物种适配" }),
  ).toBeDisabled();

  await page.getByRole("button", { name: "确认并继续 →" }).click();
  await expect(
    page.getByRole("button", { name: "运行 确认参数并执行预测" }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "结果 查看预测报告与溯源" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "下一步 →" }).click();
  await expect(
    page.getByRole("button", { name: "结果 查看预测报告与溯源" }),
  ).toBeDisabled();

  const secondJobResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/jobs") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "开始运行 →" }).click();
  const secondResponse = await secondJobResponse;
  const secondSubmission = secondResponse.request().postDataJSON() as {
    request: { perturbation_targets?: unknown };
  };
  expect(secondSubmission.request.perturbation_targets).toEqual(["TP53"]);
  const secondJob = (await secondResponse.json()) as { job_id: string };
  expect(secondJob.job_id).not.toBe(firstJob.job_id);
  await expect(
    page.getByRole("heading", {
      name: `结果 · job ${secondJob.job_id}`,
      exact: true,
    }),
  ).toBeVisible();
});

test("Ask 草稿变更后旧解析与下游阶段立即失效", async ({ page }) => {
  const firstStructured = JSON.stringify({
    species: "human",
    perturbation_type: "gene",
    perturbation_targets: ["AHR"],
    output_modality: "delta_expression",
  });

  await page.goto("/");
  await page.getByLabel("研究问题").fill("请运行结构化请求");
  await page.getByText("高级输入(可选)", { exact: true }).click();
  await page.getByLabel("结构化描述(可留空)").fill(firstStructured);
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  await page.getByRole("button", { name: "确认并继续 →" }).click();
  await expect(
    page.getByRole("heading", { name: "预计涉及的功能模块" }),
  ).toBeVisible();

  await page
    .getByRole("button", { name: "提问 描述要预测的扰动实验" })
    .click();
  await page.getByText("高级输入(可选)", { exact: true }).click();
  await page.getByLabel("研究问题").fill("请运行另一条结构化请求");
  await page.getByLabel("结构化描述(可留空)").fill(
    JSON.stringify({
      species: "mouse",
      perturbation_type: "gene",
      perturbation_targets: ["GATA1"],
      output_modality: "delta_expression",
    }),
  );

  await expect(
    page.getByRole("button", { name: "核对 核对并确认解析出的请求" }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "路由 查看模块与物种适配" }),
  ).toBeDisabled();
});

test("解析后切换模式会回到 Ask 并使旧解析链失效", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();

  await page.getByRole("button", { name: "切换", exact: true }).click();
  await expect(page.getByRole("heading", { name: "描述一次扰动实验" })).toBeVisible();
  await expect(page.getByLabel("运行方式")).toHaveValue("llm_assisted");
  await expect(
    page.getByRole("button", { name: "核对 核对并确认解析出的请求" }),
  ).toBeDisabled();
});

test("pending 解析期间清空问题后迟到成功响应不会进入 Review", async ({ page }) => {
  let releaseParse!: () => void;
  const parseGate = new Promise<void>((resolve) => {
    releaseParse = resolve;
  });
  await page.route("**/api/parse", async (route) => {
    await parseGate;
    await route.continue();
  });

  await page.goto("/");
  const parseRequest = page.waitForRequest(
    (request) =>
      request.url().endsWith("/api/parse") && request.method() === "POST",
  );
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await parseRequest;
  await page.getByLabel("研究问题").fill("");

  releaseParse();
  const parseResponse = await page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/parse") &&
      response.request().method() === "POST",
  );
  expect(parseResponse.status()).toBe(200);
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: "描述一次扰动实验" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toHaveCount(0);
});

for (const invalidate of ["草稿", "模式"] as const) {
  test(`pending 解析失败后${invalidate}变更不会污染当前 Ask 状态`, async ({
    page,
  }) => {
    let releaseParse!: () => void;
    const parseGate = new Promise<void>((resolve) => {
      releaseParse = resolve;
    });
    await page.route("**/api/parse", async (route) => {
      await parseGate;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "not-json",
      });
    });

    await page.goto("/");
    const parseRequest = page.waitForRequest(
      (request) =>
        request.url().endsWith("/api/parse") && request.method() === "POST",
    );
    await page.getByRole("button", { name: "解读任务 →" }).click();
    await parseRequest;

    if (invalidate === "草稿") {
      await page.getByLabel("研究问题").fill("在 human 细胞敲 TP53");
    } else {
      await page.getByLabel("运行方式").selectOption("llm_assisted");
    }

    releaseParse();
    const parseResponse = await page.waitForResponse(
      (response) =>
        response.url().endsWith("/api/parse") &&
        response.request().method() === "POST",
    );
    expect(parseResponse.status()).toBe(200);
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "解读任务 →" })).toBeEnabled();
  });
}

test("pending Run 期间阶段轨锁定以防重复提交", async ({ page }) => {
  let releaseJob!: () => void;
  const jobGate = new Promise<void>((resolve) => {
    releaseJob = resolve;
  });
  await page.route("**/api/jobs", async (route) => {
    if (route.request().method() === "POST") await jobGate;
    await route.continue();
  });

  await page.goto("/");
  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await page.getByRole("button", { name: "确认并继续 →" }).click();
  await page.getByRole("button", { name: "下一步 →" }).click();
  const jobRequest = page.waitForRequest(
    (request) =>
      request.url().endsWith("/api/jobs") && request.method() === "POST",
  );
  const jobResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/jobs") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "开始运行 →" }).click();
  await jobRequest;

  await expect(
    page.getByRole("button", { name: "路由 查看模块与物种适配" }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "核对 核对并确认解析出的请求" }),
  ).toBeDisabled();

  releaseJob();
  expect((await jobResponse).status()).toBe(200);
  await expect(page.getByRole("heading", { name: /^结果 · job/ })).toBeVisible();
});

test("离开 pending Run 后迟到响应不会打开旧任务结果", async ({ page }) => {
  let releaseJob!: () => void;
  const jobGate = new Promise<void>((resolve) => {
    releaseJob = resolve;
  });
  await page.route("**/api/jobs", async (route) => {
    if (route.request().method() === "POST") {
      await jobGate;
    }
    await route.continue();
  });

  await page.goto("/");
  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await page.getByRole("button", { name: "确认并继续 →" }).click();
  await page.getByRole("button", { name: "下一步 →" }).click();

  const jobRequest = page.waitForRequest(
    (request) =>
      request.url().endsWith("/api/jobs") && request.method() === "POST",
  );
  const jobResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/jobs") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "开始运行 →" }).click();
  await jobRequest;

  await page.getByRole("button", { name: "＋ 新建查询" }).click();
  await expect(page.getByRole("heading", { name: "描述一次扰动实验" })).toBeVisible();

  releaseJob();
  expect((await jobResponse).status()).toBe(200);
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: "描述一次扰动实验" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /^结果 · job/ })).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "结果 查看预测报告与溯源" }),
  ).toBeDisabled();
});
