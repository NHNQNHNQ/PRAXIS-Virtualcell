import { expect, test, type Request } from "@playwright/test";
import {
  collectBrowserFailures,
  expectNoBrowserFailures,
  isRequest,
  runChat,
  selectCell,
} from "./chat-helpers";

test("Select a cell, confirm deterministic parsing, and complete parse → job → report", async ({
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

  const query = "Knock down AHR";
  const run = await runChat(page, query);
  const parseBody = run.parseResponse.request().postDataJSON() as {
    text: string;
    mode: string;
  };
  expect(parseBody).toEqual({
    text: `${query}\nStructured description:{"species":"human","cell_type":"K562"}`,
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

test("Parsing requiring clarification fails closed without creating a job", async ({ page }) => {
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
  await expect(clarification).toContainText("No simulation task was created");
  await expect(page.getByLabel("Message PRAXIS")).toBeEnabled();
  await page.waitForLoadState("networkidle");
  expect(jobRequests).toEqual([]);
  expectNoBrowserFailures(failures);
});

test("A rapid double click sends one parse request and creates one job", async ({ page }) => {
  const failures = collectBrowserFailures(page);
  const parses: Request[] = [];
  const jobs: Request[] = [];
  page.on("request", (request) => {
    if (isRequest(request, "POST", "/api/parse")) parses.push(request);
    if (isRequest(request, "POST", "/api/jobs")) jobs.push(request);
  });

  await selectCell(page, "K562");
  await page.getByLabel("Message PRAXIS").fill("Knock down TP53");
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
      name: `Results · job ${jobId}`,
      exact: true,
    }),
  ).toBeVisible();
  await page.waitForLoadState("networkidle");

  expect(parses).toHaveLength(1);
  expect(jobs).toHaveLength(1);
  expectNoBrowserFailures(failures);
});
