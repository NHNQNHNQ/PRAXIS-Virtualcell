import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const REQUEST = {
  species: "human",
  perturbation_type: "gene",
  perturbation_targets: ["AHR"],
  input_modality: "scRNA",
  output_modality: "delta_expression",
  task_type: "predict_delta_expression",
};

function resultResponses(page: Page, jobId: string) {
  const paths = [
    `/api/reports/${jobId}`,
    `/api/reports/${jobId}/trace`,
    `/api/reports/${jobId}/provenance`,
    `/api/reports/${jobId}/module-plan`,
  ];
  return paths.map((path) =>
    page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === path &&
        response.request().method() === "GET",
    ),
  );
}

async function createJob(request: APIRequestContext): Promise<string> {
  const response = await request.post("/api/jobs", {
    data: { request: REQUEST, mode: "offline" },
  });
  expect(response.status()).toBe(200);
  const body = (await response.json()) as { job_id: string };
  expect(body.job_id).toMatch(/^vc_/);
  return body.job_id;
}

test("Results 代码只在进入结果时加载并提供可访问等待状态", async ({
  page,
}) => {
  let resultsChunkRequests = 0;
  let releaseChunk: (() => void) | undefined;
  const chunkGate = new Promise<void>((resolve) => {
    releaseChunk = resolve;
  });

  await page.route("**/assets/ResultsStage-*.js", async (route) => {
    resultsChunkRequests += 1;
    await chunkGate;
    await route.continue();
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Agent Workspace", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验" }),
  ).toBeVisible();
  expect(resultsChunkRequests).toBe(0);

  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await expect(
    page.getByRole("heading", { name: "核对任务解读" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "确认并继续 →" }).click();
  await expect(
    page.getByRole("heading", { name: "预计涉及的功能模块" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "下一步 →" }).click();
  await expect(page.getByRole("heading", { name: "运行前确认" })).toBeVisible();

  const jobResponse = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/api/jobs" &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "开始运行 →" }).click();
  const completedJobResponse = await jobResponse;
  expect(completedJobResponse.status()).toBe(200);
  const { job_id: jobId } = (await completedJobResponse.json()) as {
    job_id: string;
  };

  await expect.poll(() => resultsChunkRequests).toBe(1);
  await expect(
    page.getByRole("status", { name: "正在加载结果", exact: true }),
  ).toBeVisible();

  const responses = resultResponses(page, jobId);
  releaseChunk?.();
  expect((await Promise.all(responses)).map((response) => response.status())).toEqual([
    200, 200, 200, 200,
  ]);
  await expect(page.getByRole("heading", { name: /^结果 · job/ })).toBeVisible();
  expect(resultsChunkRequests).toBe(1);
});

test("全新页面从历史记录进入 Results 时也走延迟加载边界", async ({
  page,
  request,
}) => {
  const jobId = await createJob(request);
  let resultsChunkRequests = 0;
  let releaseChunk: (() => void) | undefined;
  const chunkGate = new Promise<void>((resolve) => {
    releaseChunk = resolve;
  });

  await page.route("**/assets/ResultsStage-*.js", async (route) => {
    resultsChunkRequests += 1;
    await chunkGate;
    await route.continue();
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Agent Workspace", exact: true }).click();
  expect(resultsChunkRequests).toBe(0);
  const historyEntry = page.getByRole("button", { name: new RegExp(jobId) });
  await expect(historyEntry).toBeVisible();
  const responses = resultResponses(page, jobId);
  await historyEntry.click();

  await expect.poll(() => resultsChunkRequests).toBe(1);
  await expect(
    page.getByRole("status", { name: "正在加载结果", exact: true }),
  ).toBeVisible();

  releaseChunk?.();
  expect((await Promise.all(responses)).map((response) => response.status())).toEqual([
    200, 200, 200, 200,
  ]);
  await expect(
    page.getByRole("heading", { name: `结果 · job ${jobId}`, exact: true }),
  ).toBeVisible();
  expect(resultsChunkRequests).toBe(1);
});
