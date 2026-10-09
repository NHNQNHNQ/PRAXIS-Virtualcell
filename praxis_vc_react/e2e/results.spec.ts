import { expect, test } from "@playwright/test";
import {
  collectBrowserFailures,
  expectNoBrowserFailures,
  runChat,
  selectCell,
} from "./chat-helpers";

const RESULT_TABS: Array<[string, string]> = [
  ["Report", "Summary"],
  ["Predictions", "No prediction was produced"],
  ["Module routing", "No module routing produced"],
  ["Data and execution identity", "Data and execution identity"],
  ["Evidence", "Evidence and audit"],
  ["Execution trace", "Execution trace"],
  ["Provenance", "Run identity"],
];

test("An unbound request explicitly abstains across seven tabs and preserves execution identity", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  await selectCell(page, "K562");
  const run = await runChat(page, "Knock down AHR");
  const result = page.getByRole("region", {
    name: `Results · job ${run.jobId}`,
    exact: true,
  });
  await expect(result.getByRole("tab")).toHaveCount(7);

  for (const [tab, heading] of RESULT_TABS) {
    await result.getByRole("tab", { name: tab, exact: true }).click();
    const expected = ["Predictions", "Module routing"].includes(tab)
      ? result.getByText(heading, { exact: true }).first()
      : result.getByRole("heading", { name: heading, exact: true }).first();
    await expect(expected).toBeVisible();
  }

  const modulePlan = (await run.modulePlanResponse.json()) as {
    module_plan: Record<string, unknown>;
  };
  expect(modulePlan.module_plan).toEqual({});

  const provenance = (await run.provenanceResponse.json()) as {
    execution_identity: {
      schema_version?: string;
      legacy_adapter?: boolean;
      fingerprint?: string;
    };
  };
  expect(provenance.execution_identity).toMatchObject({
    schema_version: "vc.job-execution-identity.v2",
    legacy_adapter: false,
  });
  expect(provenance.execution_identity.fingerprint).toMatch(/^[a-f0-9]{64}$/);

  await result
    .getByRole("tab", { name: "Data and execution identity", exact: true })
    .click();
  await expect(
    result.getByText("No VirtualCellPack bound", { exact: true }),
  ).toBeVisible();
  await expect(
    result.getByText("No dataset identity recorded", { exact: true }),
  ).toBeVisible();
  await expect(
    result
      .getByText(provenance.execution_identity.fingerprint!, { exact: true })
      .first(),
  ).toBeVisible();
  expectNoBrowserFailures(failures);
});

test("An incompatible request reports abstention without inventing predictions", async ({ page }) => {
  const failures = collectBrowserFailures(page);
  await selectCell(page, "K562");
  const run = await runChat(page, "Knock down FASN");
  const payload = (await run.reportResponse.json()) as {
    structured_report: {
      abstain: boolean;
      abstain_reasons: string[];
      prediction: unknown;
    };
  };
  expect(payload.structured_report.abstain).toBe(true);
  expect(payload.structured_report.prediction).toBeNull();
  expect(payload.structured_report.abstain_reasons).toContain(
    "pack_unregistered",
  );

  const result = page.getByRole("region", {
    name: `Results · job ${run.jobId}`,
    exact: true,
  });
  await expect(
    result.getByText("No prediction was produced", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    result.getByText("pack_unregistered", { exact: true }),
  ).toBeVisible();
  await result.getByRole("tab", { name: "Predictions", exact: true }).click();
  await expect(
    result.getByText("See Report for the reliability decision and reasons.", { exact: true }),
  ).toBeVisible();
  expectNoBrowserFailures(failures);
});

test("Recent reports reopens reports saved by the backend", async ({ page }) => {
  const failures = collectBrowserFailures(page);
  await selectCell(page, "PBMC");
  const run = await runChat(page, "Activate STAT1");

  const historyEntry = page
    .locator(".chat-history > .chat-history-item.active")
    .filter({ hasText: "human · STAT1" });
  await expect(historyEntry).toHaveCount(1);
  await historyEntry.click();

  const savedReport = page.getByRole("region", {
    name: "Saved report",
    exact: true,
  });
  await expect(
    savedReport.getByRole("heading", { name: "Run report", exact: true }),
  ).toBeVisible();
  await expect(
    savedReport.getByRole("region", {
      name: `Results · job ${run.jobId}`,
      exact: true,
    }),
  ).toBeVisible();
  expectNoBrowserFailures(failures);
});
