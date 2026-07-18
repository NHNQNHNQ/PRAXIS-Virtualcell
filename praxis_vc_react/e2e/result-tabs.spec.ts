import { test, expect, type Download, type Page } from "@playwright/test";

type BrowserFailures = {
  pageErrors: string[];
  consoleErrors: string[];
  http500: string[];
};

type ResultsTruth = {
  jobId: string;
  report: {
    llm_used_for_prediction: boolean;
  };
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

// 先走完 5 阶段到 Results,再逐个点 6 tab 断面板 h2(切 tab 纯前端不发请求)。
async function reachResults(page: Page): Promise<ResultsTruth> {
  await page.goto("/");
  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await page.getByRole("button", { name: "确认并继续 →" }).click();
  await page.getByRole("button", { name: "下一步 →" }).click();
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
      response.url().endsWith("/trace") && response.request().method() === "GET",
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
  const body = (await jobResponse.json()) as { job_id: string };
  const report = (await reportResponse.json()) as ResultsTruth["report"];
  await expect(page.getByRole("heading", { name: /^结果 · job/ })).toBeVisible();
  return { jobId: body.job_id, report };
}

async function downloadedBytes(download: Download): Promise<number> {
  const stream = await download.createReadStream();
  let size = 0;
  for await (const chunk of stream) {
    size += (chunk as Uint8Array).byteLength;
  }
  return size;
}

const TABS: Array<[string, string]> = [
  ["报告", "概要"],
  ["预测", "结果可靠性"],
  ["模块路由", "路由摘要"],
  ["证据", "证据与审计"],
  ["运行轨迹", "运行轨迹"],
  ["溯源", "运行标识"],
];

test("Results 6 tab 逐个可达 + 面板 h2 出现", async ({ page }) => {
  const failures = collectBrowserFailures(page);
  await reachResults(page);
  for (const [tab, h2] of TABS) {
    await page.getByRole("tab", { name: tab }).click();
    await expect(page.getByRole("heading", { name: h2 })).toBeVisible();
  }
  expectNoBrowserFailures(failures);
});

test("Results 关键结论、路由、证据与溯源均可审计", async ({ page }) => {
  const failures = collectBrowserFailures(page);
  const { jobId, report } = await reachResults(page);
  const result = page.getByRole("region", { name: `结果 · job ${jobId}` });

  expect(report.llm_used_for_prediction).toBe(false);
  await expect(
    result.getByText("结果由确定性模型给出,未经语言模型改写", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(result.getByText(/llm_used_for_prediction:/)).toContainText(
    "llm_used_for_prediction:false",
  );
  await expect(result.getByText("request_id", { exact: true })).toBeVisible();
  await expect(result.getByText(/^vc-[a-f0-9]{16}$/)).toBeVisible();
  await expect(
    result.getByText("MockLinear, MockCPA, MockGEARS", { exact: true }),
  ).toBeVisible();
  await expect(result.getByText(/"delta":\s*\[\s*0\.3\s*\]/)).toBeVisible();
  await expect(result.getByText("已给出预测", { exact: true })).toBeVisible();

  await result.getByRole("tab", { name: "预测" }).click();
  await expect(result.getByRole("heading", { name: "结果可靠性" })).toBeVisible();
  await expect(result.getByText("可靠性判定:high", { exact: true })).toBeVisible();

  await result.getByRole("tab", { name: "模块路由" }).click();
  await expect(
    result.getByRole("row", { name: "genetic_hub primary accept —" }),
  ).toBeVisible();

  await result.getByRole("tab", { name: "证据" }).click();
  await expect(
    result.getByRole("row", {
      name: "采纳模型 3 个 MockLinear MockCPA MockGEARS",
    }),
  ).toBeVisible();

  await result.getByRole("tab", { name: "溯源" }).click();
  await expect(
    result.getByRole("row", { name: `job 标识 ${jobId}` }),
  ).toBeVisible();
  await expect(result.getByText("完整 provenance JSON", { exact: true })).toBeVisible();
  expectNoBrowserFailures(failures);
});

test("Results 下载、离线禁用与复制操作保持诚实", async ({ page, context }) => {
  const failures = collectBrowserFailures(page);
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const { jobId } = await reachResults(page);
  const actions = page.getByRole("group", { name: "结果操作" });

  const jsonDownloadPromise = page.waitForEvent("download");
  await actions.getByRole("button", { name: "下载 report.json" }).click();
  const jsonDownload = await jsonDownloadPromise;
  expect(jsonDownload.suggestedFilename()).toBe(
    `${jobId}_structured_report.json`,
  );
  expect(await downloadedBytes(jsonDownload)).toBeGreaterThan(0);

  const markdownDownloadPromise = page.waitForEvent("download");
  await actions.getByRole("button", { name: "下载 report.md" }).click();
  const markdownDownload = await markdownDownloadPromise;
  expect(markdownDownload.suggestedFilename()).toBe(`${jobId}_report.md`);
  expect(await downloadedBytes(markdownDownload)).toBeGreaterThan(0);

  await expect(
    actions.getByRole("button", { name: "下载 narrative.md" }),
  ).toBeDisabled();

  await actions.getByRole("button", { name: "复制报告" }).click();
  await expect
    .poll(() => page.evaluate(() => navigator.clipboard.readText()))
    .toContain('"prediction"');
  expectNoBrowserFailures(failures);
});

test("1280×720 Results 动作区不挤压标题或按钮", async ({ page }) => {
  const failures = collectBrowserFailures(page);
  await reachResults(page);

  const title = page.getByRole("heading", { name: /^结果 · job/ });
  const card = page.getByRole("region", { name: /^结果 · job/ });
  const actions = page.getByRole("group", { name: "结果操作" });
  const buttons = actions.getByRole("button");

  await expect(title).toBeVisible();
  await expect(card).toBeVisible();
  await expect(actions).toBeVisible();
  await expect(buttons).toHaveCount(5);

  const layout = await card.evaluate((element) => {
    const heading = element.querySelector("h2");
    const actionGroup = element.querySelector<HTMLElement>(".card-actions");
    const actionButtons = [...(actionGroup?.querySelectorAll("button") ?? [])];
    if (!(heading instanceof HTMLElement) || !actionGroup) {
      throw new Error("Results card header structure is missing");
    }

    const titleRect = heading.getBoundingClientRect();
    const actionRect = actionGroup.getBoundingClientRect();
    const separated =
      titleRect.right <= actionRect.left + 1 ||
      titleRect.bottom <= actionRect.top + 1 ||
      actionRect.bottom <= titleRect.top + 1;

    return {
      cardFits: element.scrollWidth <= element.clientWidth + 1,
      actionsFit: actionGroup.scrollWidth <= actionGroup.clientWidth + 1,
      titleAndActionsSeparated: separated,
      buttons: actionButtons.map((button) => {
        const rect = button.getBoundingClientRect();
        return {
          horizontal: rect.width > rect.height,
          contentFits:
            button.scrollWidth <= button.clientWidth + 1 &&
            button.scrollHeight <= button.clientHeight + 1,
          whiteSpace: getComputedStyle(button).whiteSpace,
        };
      }),
    };
  });

  expect(layout.cardFits).toBe(true);
  expect(layout.actionsFit).toBe(true);
  expect(layout.titleAndActionsSeparated).toBe(true);
  expect(layout.buttons).toHaveLength(5);
  for (const button of layout.buttons) {
    expect(button.horizontal).toBe(true);
    expect(button.contentFits).toBe(true);
    expect(button.whiteSpace).toBe("nowrap");
  }
  expectNoBrowserFailures(failures);
});
