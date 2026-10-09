import { expect, test, type Request } from "@playwright/test";
import {
  collectBrowserFailures,
  expectNoBrowserFailures,
  isRequest,
  runChat,
  selectCell,
} from "./chat-helpers";

test("选择 cell 后确认确定性解析并完成 parse → job → report", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "Choose a cell to begin.",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByLabel("Message PRAXIS")).toHaveCount(0);

  await selectCell(page, "K562", { openPage: false });
  await expect(page.getByText("human · catalog preset", { exact: true })).toBeVisible();

  const query = "敲低 AHR";
  const run = await runChat(page, query);
  const parseBody = run.parseResponse.request().postDataJSON() as {
    text: string;
    mode: string;
  };
  expect(parseBody).toEqual({
    text: `${query}\n结构化描述:{"species":"human","cell_type":"K562"}`,
    mode: "llm_assisted",
  });

  const parsed = (await run.parseResponse.json()) as {
    candidate_request: Record<string, unknown>;
  };
  const submitted = run.jobResponse.request().postDataJSON() as {
    request: Record<string, unknown>;
    mode: string;
    enable_llm_report: boolean;
  };
  expect(submitted).toEqual({
    request: parsed.candidate_request,
    mode: "llm_assisted",
    enable_llm_report: true,
  });
  expect(submitted.request).toMatchObject({
    species: "human",
    cell_type: "K562",
    perturbation_type: "gene",
    perturbation_targets: ["AHR"],
  });
  expectNoBrowserFailures(failures);
});

test("解析需要澄清时 fail-closed 且不创建 job", async ({ page }) => {
  const failures = collectBrowserFailures(page);
  const jobRequests: Request[] = [];
  page.on("request", (request) => {
    if (isRequest(request, "POST", "/api/jobs")) jobRequests.push(request);
  });

  await selectCell(page, "K562");
  const parseResponsePromise = page.waitForResponse((response) =>
    isRequest(response.request(), "POST", "/api/parse"),
  );
  await page.getByLabel("Message PRAXIS").fill("🧬🧪");
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  expect((await parseResponsePromise).status()).toBe(200);

  const clarification = page
    .getByRole("alert")
    .filter({ hasText: "I need one more detail." });
  await expect(clarification).toBeVisible();
  await expect(clarification).toContainText("perturbation_targets");
  await expect(clarification).toContainText("未创建模拟任务");
  await expect(page.getByLabel("Message PRAXIS")).toBeEnabled();
  await page.waitForLoadState("networkidle");
  expect(jobRequests).toEqual([]);
  expectNoBrowserFailures(failures);
});

test("快速双击发送只产生一次 parse 和一次 job", async ({ page }) => {
  const failures = collectBrowserFailures(page);
  const parses: Request[] = [];
  const jobs: Request[] = [];
  page.on("request", (request) => {
    if (isRequest(request, "POST", "/api/parse")) parses.push(request);
    if (isRequest(request, "POST", "/api/jobs")) jobs.push(request);
  });

  await selectCell(page, "K562");
  await page.getByLabel("Message PRAXIS").fill("敲低 TP53");
  const parseResponsePromise = page.waitForResponse((response) =>
    isRequest(response.request(), "POST", "/api/parse"),
  );
  await page
    .getByRole("button", { name: "Send message", exact: true })
    .dblclick();
  expect((await parseResponsePromise).status()).toBe(200);
  await expect(
    page.getByText("Please confirm this interpretation.", { exact: true }),
  ).toBeVisible();
  expect(parses).toHaveLength(1);

  const jobResponsePromise = page.waitForResponse((response) =>
    isRequest(response.request(), "POST", "/api/jobs"),
  );
  await page
    .getByRole("button", {
      name: "Confirm interpretation and generate report",
      exact: true,
    })
    .dblclick();
  const jobResponse = await jobResponsePromise;
  const { job_id: jobId } = (await jobResponse.json()) as { job_id: string };
  await expect(
    page.getByRole("region", {
      name: `结果 · job ${jobId}`,
      exact: true,
    }),
  ).toBeVisible();
  await page.waitForLoadState("networkidle");

  expect(parses).toHaveLength(1);
  expect(jobs).toHaveLength(1);
  expectNoBrowserFailures(failures);
});
