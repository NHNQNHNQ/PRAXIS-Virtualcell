import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import {
  collectBrowserFailures,
  expectNoBrowserFailures,
  isRequest,
  selectCell,
} from "./chat-helpers";

const GOLDEN_REQUEST = JSON.parse(
  readFileSync(
    new URL("../../examples/golden_ahr_klf1_request_v2.json", import.meta.url),
    "utf8",
  ),
) as Record<string, unknown>;
const PREVIEW_LABEL = "Preview registered AHR+KLF1 · 5d · research-only";
const JOB_ID = "golden-ui-job";
const DESCRIPTOR_FINGERPRINT = "d".repeat(64);
const COMPATIBILITY_FINGERPRINT = "e".repeat(64);

const researchTask = {
  schema_version: "vc.research-task.v1",
  task_id: "norman-2019-ahr-klf1-research",
  request: GOLDEN_REQUEST,
  pack_id: "norman-2019-k562-golden",
  pack_version: "1.0.0",
  model_name: "norman_additive_linear",
  model_version: "1.0.0-research.1",
  execution_scope: "research_only",
  scientifically_validated: false,
};

const compatibilityReport = {
  model_name: "norman_additive_linear",
  model_version: "1.0.0-research.1",
  pack_id: "norman-2019-k562-golden",
  pack_version: "1.0.0",
  executable: true,
  benchmark_passed: false,
  scientifically_validated: false,
  production_promoted: false,
  research_execution_authorized: true,
  research_execution_scope: "research_only",
};

const executionPlan = {
  schema_version: "vc.execution-plan.v2",
  plan_id: "plan_golden_ui_fixture",
  pack_id: "norman-2019-k562-golden",
  pack_version: "1.0.0",
  executable: true,
  legacy_adapter: false,
  steps: [
    {
      model_name: "norman_additive_linear",
      model_version: "1.0.0-research.1",
      model_fingerprint: "a".repeat(64),
      compatibility_fingerprint: "b".repeat(64),
    },
  ],
  reports: [compatibilityReport],
};

const structuredReport = {
  request_id: "golden-norman-ahr-klf1-research",
  abstain: false,
  abstain_reasons: [],
  models_used: ["norman_additive_linear"],
  models_rejected: [],
  models_failed: [],
  execution_scope: "research_only",
  scientifically_validated: false,
  prediction: {
    schema_version: "vc.adapter-output-envelope.v1",
    task: "predict_delta_expression",
    output: "delta_expression",
    shape: [5045],
    values: Array.from({ length: 5045 }, (_, index) =>
      index === 0 ? 0.42 : 0,
    ),
    projection_metadata: {
      baseline: "additive_linear",
      feature_ids_sha256:
        "ecca6c636629e35ae5f5a0ec6fe84c1a7983e1adb263fbbcaea70a0c5495b2b7",
      n_features: 5045,
      value_type: "delta_expression",
      unseen_train_targets: [],
    },
    ood: { detected: false, dimensions: [], reason: null },
    uncertainty: {
      available: false,
      method: "point_estimate",
      calibrated: false,
      value: null,
      sigma: null,
      reason: "additive baseline has no calibrated predictive uncertainty",
    },
  },
};

test("K562 registered task submits exact direct-v2 contract and renders the real vector shape", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  const executionBodies: unknown[] = [];
  const genericJobBodies: unknown[] = [];
  let parseRequests = 0;
  let compatibilityRequests = 0;
  let created = false;

  page.on("request", (request) => {
    if (isRequest(request, "POST", "/api/parse")) parseRequests += 1;
  });
  await page.route("**/api/research-tasks", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ tasks: [researchTask] }),
    });
  });
  await page.route("**/api/research-tasks/*/compatibility", async (route) => {
    compatibilityRequests += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        schema_version: "vc.research-task-compatibility.v1",
        task_id: researchTask.task_id,
        descriptor_fingerprint: DESCRIPTOR_FINGERPRINT,
        compatibility_fingerprint: COMPATIBILITY_FINGERPRINT,
        execution_plan: executionPlan,
      }),
    });
  });
  await page.route("**/api/research-tasks/*/execute", async (route) => {
    created = true;
    executionBodies.push(route.request().postDataJSON());
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ job_id: JOB_ID, status: "done" }),
    });
  });
  await page.route("**/api/jobs", async (route) => {
    const request = route.request();
    if (request.method() === "POST") {
      genericJobBodies.push(request.postDataJSON());
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "generic_job_path_forbidden" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        jobs: created
          ? [
              {
                job_id: JOB_ID,
                status: "done",
                species: "human",
                perturbation_targets: [
                  "ENSG00000106546",
                  "ENSG00000105610",
                ],
                abstain: false,
                reliability: "research_only",
                pack_id: "norman-2019-k562-golden",
                pack_version: "1.0.0",
                pack_fingerprint: "a".repeat(64),
                execution_scope: "research_only",
                scientifically_validated: false,
                models_used: ["norman_additive_linear"],
              },
            ]
          : [],
      }),
    });
  });
  await page.route(new RegExp(`/api/reports/${JOB_ID}(?:/[^?]+)?$`), async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const payload = pathname.endsWith("/trace")
      ? { trace: [] }
      : pathname.endsWith("/provenance")
        ? {
            provenance: {
              execution_contract: "vc.direct-v2-execution.v1",
              execution_plan: executionPlan,
              compatibility_reports: [compatibilityReport],
            },
            llm_meta: {},
            execution_identity: {
              schema_version: "vc.job-execution-identity.v4",
              legacy_adapter: false,
              pack: {
                pack_id: "norman-2019-k562-golden",
                pack_version: "1.0.0",
                fingerprint: "c".repeat(64),
              },
              models: [
                {
                  name: "norman_additive_linear",
                  version: "1.0.0-research.1",
                  fingerprint: "a".repeat(64),
                  compatibility_fingerprint: "b".repeat(64),
                  executable: true,
                },
              ],
              execution_scope: "research_only",
              scientifically_validated: false,
              fingerprint: "d".repeat(64),
            },
          }
        : pathname.endsWith("/module-plan")
          ? { module_plan: {} }
          : {
              structured_report: structuredReport,
              narrative_report: null,
              trace_url: `/api/reports/${JOB_ID}/trace`,
              provenance_url: `/api/reports/${JOB_ID}/provenance`,
              markdown_url: `/api/reports/${JOB_ID}/markdown`,
              llm_used_for_prediction: false,
            };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(payload),
    });
  });

  await selectCell(page, "K562");
  await page.getByRole("button", { name: PREVIEW_LABEL, exact: true }).click();

  const preview = page.getByRole("region", {
    name: "Research task compatibility preview",
    exact: true,
  });
  await expect(preview).toBeVisible();
  await expect(preview.getByText("norman-2019-k562-golden@1.0.0")).toBeVisible();
  await expect(preview.getByText("norman_additive_linear@1.0.0-research.1")).toBeVisible();
  await expect(preview.getByText("true", { exact: true })).toBeVisible();
  expect(compatibilityRequests).toBe(1);
  expect(parseRequests).toBe(0);
  expect(executionBodies).toHaveLength(0);

  await preview
    .getByRole("button", {
      name: "Confirm compatibility and run direct-v2",
      exact: true,
    })
    .click();

  const result = page.getByRole("region", {
    name: `Results · job ${JOB_ID}`,
    exact: true,
  });
  await expect(result).toBeVisible();
  expect(parseRequests).toBe(0);
  expect(executionBodies).toEqual([
    { compatibility_fingerprint: COMPATIBILITY_FINGERPRINT },
  ]);
  expect(genericJobBodies).toEqual([]);
  const serializedBody = JSON.stringify(executionBodies[0]);
  expect(serializedBody).not.toContain("registration_root");
  expect(serializedBody).not.toContain("model_cache_root");
  expect(serializedBody).not.toContain("pack_root");
  expect(serializedBody).not.toContain("/Volumes/");

  await expect(result.getByText("research_only", { exact: true }).first()).toBeVisible();
  await expect(
    result.getByText("scientifically_validated=false", { exact: false }).first(),
  ).toBeVisible();
  await expect(result.getByText("norman_additive_linear", { exact: true }).first()).toBeVisible();
  const historyEntry = page.locator(".chat-history > .chat-history-item.active");
  await expect(historyEntry).toContainText(
    "Pack norman-2019-k562-golden@1.0.0",
  );
  await expect(historyEntry).toContainText(
    "research_only · science=false · norman_additive_linear",
  );

  await result.getByRole("tab", { name: "Predictions", exact: true }).click();
  await expect(result.getByText(/Full output contains 5,045 dimensions/)).toBeVisible();
  await expect(result.getByLabel("Predicted change Δ (top)")).toBeVisible();
  await expect(result.getByText("No predicted changes available", { exact: true })).toHaveCount(0);

  await result.getByRole("tab", { name: "Provenance", exact: true }).click();
  await expect(result.getByText("vc.direct-v2-execution.v1", { exact: true })).toBeVisible();
  await expect(result.getByText("research_only", { exact: true }).first()).toBeVisible();
  await expect(
    page.getByText("human · ENSG00000106546, ENSG00000105610", { exact: true }).first(),
  ).toBeVisible();
  expectNoBrowserFailures(failures);
});

test("registered task fails closed when compatibility is unavailable", async ({
  page,
}) => {
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  const jobBodies: unknown[] = [];
  let parseRequests = 0;
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("request", (request) => {
    if (isRequest(request, "POST", "/api/parse")) parseRequests += 1;
    if (isRequest(request, "POST", "/api/jobs")) {
      jobBodies.push(request.postDataJSON());
    }
    if (isRequest(request, "POST", /^\/api\/research-tasks\/[^/]+\/execute$/)) {
      jobBodies.push(request.postDataJSON());
    }
  });
  await page.route("**/api/research-tasks", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ tasks: [researchTask] }),
    });
  });
  await page.route("**/api/research-tasks/*/compatibility", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "direct_v2_factory_unconfigured" }),
    });
  });

  await selectCell(page, "K562");
  const responsePromise = page.waitForResponse((response) =>
    isRequest(
      response.request(),
      "POST",
      `/api/research-tasks/${researchTask.task_id}/compatibility`,
    ),
  );
  await page.getByRole("button", { name: PREVIEW_LABEL, exact: true }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(503);
  expect(await response.json()).toEqual({ detail: "direct_v2_factory_unconfigured" });
  expect(parseRequests).toBe(0);
  expect(jobBodies).toHaveLength(0);
  await expect(page.getByRole("alert")).toContainText(
    "A real research runtime is not configured",
  );
  await expect(page.getByRole("alert")).toContainText(
    "mock, legacy model, and parsing fallbacks are disabled",
  );
  await expect(
    page.getByRole("button", { name: PREVIEW_LABEL, exact: true }),
  ).toBeEnabled();
  await expect(
    page.getByRole("button", {
      name: "Confirm compatibility and run direct-v2",
      exact: true,
    }),
  ).toHaveCount(0);
  await expect(page.getByRole("region", { name: /Results · job/ })).toHaveCount(0);
  expect(pageErrors).toEqual([]);
  expect(
    consoleErrors.filter(
      (message) => !message.includes("503 (Service Unavailable)"),
    ),
  ).toEqual([]);
});

test("registered task rejects a stale confirmed preview without generic fallback", async ({
  page,
}) => {
  const forbiddenRequests: string[] = [];
  let executeBodies: unknown[] = [];
  page.on("request", (request) => {
    if (isRequest(request, "POST", "/api/parse") || isRequest(request, "POST", "/api/jobs")) {
      forbiddenRequests.push(request.url());
    }
  });
  await page.route("**/api/research-tasks", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ tasks: [researchTask] }),
    });
  });
  await page.route("**/api/research-tasks/*/compatibility", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        schema_version: "vc.research-task-compatibility.v1",
        task_id: researchTask.task_id,
        descriptor_fingerprint: DESCRIPTOR_FINGERPRINT,
        compatibility_fingerprint: COMPATIBILITY_FINGERPRINT,
        execution_plan: executionPlan,
      }),
    });
  });
  await page.route("**/api/research-tasks/*/execute", async (route) => {
    executeBodies = [...executeBodies, route.request().postDataJSON()];
    await route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({ detail: "research_task_compatibility_stale" }),
    });
  });

  await selectCell(page, "K562");
  await page.getByRole("button", { name: PREVIEW_LABEL, exact: true }).click();
  const preview = page.getByRole("region", {
    name: "Research task compatibility preview",
    exact: true,
  });
  await preview
    .getByRole("button", {
      name: "Confirm compatibility and run direct-v2",
      exact: true,
    })
    .click();

  await expect(page.getByRole("alert").last()).toContainText(
    "research_task_compatibility_stale",
  );
  expect(executeBodies).toEqual([
    { compatibility_fingerprint: COMPATIBILITY_FINGERPRINT },
  ]);
  expect(forbiddenRequests).toEqual([]);
  await expect(page.getByRole("region", { name: /Results · job/ })).toHaveCount(0);
});

test("unconfigured empty research catalog hides the registered entry", async ({
  page,
}) => {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (
      isRequest(request, "POST", "/api/parse") ||
      isRequest(request, "POST", "/api/jobs") ||
      isRequest(request, "POST", /^\/api\/research-tasks\/[^/]+\/(compatibility|execute)$/)
    ) {
      requests.push(request.url());
    }
  });
  await page.route("**/api/research-tasks", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ tasks: [] }),
    });
  });

  await selectCell(page, "K562");
  await expect(page.locator("button.registered-research")).toHaveCount(0);
  expect(requests).toEqual([]);
});
