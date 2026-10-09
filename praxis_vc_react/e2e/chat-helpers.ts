import {
  expect,
  type Page,
  type Request,
  type Response,
} from "@playwright/test";

export type BrowserFailures = {
  pageErrors: string[];
  consoleErrors: string[];
  http500: string[];
};

export type RunCapture = {
  parseResponse: Response;
  jobResponse: Response;
  reportResponse: Response;
  traceResponse: Response;
  provenanceResponse: Response;
  modulePlanResponse: Response;
  jobId: string;
};

function pathOf(request: Request): string {
  return new URL(request.url()).pathname;
}

export function isRequest(
  request: Request,
  method: string,
  path: string | RegExp,
): boolean {
  const pathname = pathOf(request);
  return (
    request.method() === method &&
    (typeof path === "string" ? pathname === path : path.test(pathname))
  );
}

export function collectBrowserFailures(page: Page): BrowserFailures {
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

export function expectNoBrowserFailures(failures: BrowserFailures): void {
  expect(failures).toEqual({
    pageErrors: [],
    consoleErrors: [],
    http500: [],
  });
}

export async function selectCell(
  page: Page,
  cellType: string,
  options: { openPage?: boolean } = {},
): Promise<void> {
  if (options.openPage !== false) await page.goto("/");
  const card = page
    .getByRole("article")
    .filter({
      has: page.getByRole("heading", {
        name: cellType,
        level: 2,
        exact: true,
      }),
    });
  await expect(card).toHaveCount(1);
  await card.getByRole("button", { name: "Select cell", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: cellType,
      level: 1,
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByLabel("Message PRAXIS")).toBeVisible();
}

export async function runChat(page: Page, query: string): Promise<RunCapture> {
  const jobRequests: Request[] = [];
  page.on("request", (request) => {
    if (isRequest(request, "POST", "/api/jobs")) jobRequests.push(request);
  });
  const parseResponsePromise = page.waitForResponse((response) =>
    isRequest(response.request(), "POST", "/api/parse"),
  );
  const jobResponsePromise = page.waitForResponse((response) =>
    isRequest(response.request(), "POST", "/api/jobs"),
  );
  const reportResponsePromise = page.waitForResponse((response) =>
    isRequest(response.request(), "GET", /^\/api\/reports\/[^/]+$/),
  );
  const traceResponsePromise = page.waitForResponse((response) =>
    isRequest(response.request(), "GET", /^\/api\/reports\/[^/]+\/trace$/),
  );
  const provenanceResponsePromise = page.waitForResponse((response) =>
    isRequest(
      response.request(),
      "GET",
      /^\/api\/reports\/[^/]+\/provenance$/,
    ),
  );
  const modulePlanResponsePromise = page.waitForResponse((response) =>
    isRequest(
      response.request(),
      "GET",
      /^\/api\/reports\/[^/]+\/module-plan$/,
    ),
  );

  await page.getByLabel("Message PRAXIS").fill(query);
  await page.getByRole("button", { name: "Send message", exact: true }).click();

  const parseResponse = await parseResponsePromise;
  expect(parseResponse.status()).toBe(200);
  const parsed = (await parseResponse.json()) as {
    fallback_used: boolean;
    llm_used: boolean;
  };
  if (parsed.fallback_used && !parsed.llm_used) {
    await expect(
      page.getByText("Please confirm this interpretation.", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText(
        "Language parsing: deterministic fallback · awaiting confirmation",
        { exact: true },
      ),
    ).toBeVisible();
    expect(jobRequests).toHaveLength(0);
    await page
      .getByRole("button", {
        name: "Confirm interpretation and generate report",
        exact: true,
      })
      .click();
  }

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
  expect(
    [
      jobResponse,
      reportResponse,
      traceResponse,
      provenanceResponse,
      modulePlanResponse,
    ].map((response) => response.status()),
  ).toEqual([200, 200, 200, 200, 200]);

  const { job_id: jobId } = (await jobResponse.json()) as { job_id: string };
  await expect(
    page
      .getByRole("status")
      .filter({
        hasText:
          "Report generated. Prediction or abstention is shown below.",
      }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", {
      name: `结果 · job ${jobId}`,
      exact: true,
    }),
  ).toBeVisible();

  return {
    parseResponse,
    jobResponse,
    reportResponse,
    traceResponse,
    provenanceResponse,
    modulePlanResponse,
    jobId,
  };
}
