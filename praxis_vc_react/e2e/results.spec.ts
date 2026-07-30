import { expect, test } from "@playwright/test";
import {
  collectBrowserFailures,
  expectNoBrowserFailures,
  runChat,
  selectCell,
} from "./chat-helpers";

const RESULT_TABS: Array<[string, string]> = [
  ["报告", "概要"],
  ["预测", "结果可靠性"],
  ["模块路由", "路由摘要"],
  ["数据与执行身份", "数据与执行身份"],
  ["证据", "证据与审计"],
  ["运行轨迹", "运行轨迹"],
  ["溯源", "运行标识"],
];

test("直接报告的 7 tabs、实际路由和 execution identity 均可审计", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  await selectCell(page, "K562");
  const run = await runChat(page, "敲低 AHR");
  const result = page.getByRole("region", {
    name: `结果 · job ${run.jobId}`,
    exact: true,
  });
  await expect(result.getByRole("tab")).toHaveCount(7);

  for (const [tab, heading] of RESULT_TABS) {
    await result.getByRole("tab", { name: tab, exact: true }).click();
    await expect(
      result.getByRole("heading", { name: heading, exact: true }).first(),
    ).toBeVisible();
  }

  const modulePlan = (await run.modulePlanResponse.json()) as {
    module_plan: Record<string, unknown>;
  };
  expect(modulePlan.module_plan).toMatchObject({
    primary: "genetic_hub",
    overall_verdict: "accept",
  });

  const provenance = (await run.provenanceResponse.json()) as {
    execution_identity: {
      schema_version?: string;
      legacy_adapter?: boolean;
      fingerprint?: string;
    };
  };
  expect(provenance.execution_identity).toMatchObject({
    schema_version: "vc.job-execution-identity.v1",
    legacy_adapter: true,
  });
  expect(provenance.execution_identity.fingerprint).toMatch(/^[a-f0-9]{64}$/);

  await result
    .getByRole("tab", { name: "数据与执行身份", exact: true })
    .click();
  await expect(
    result.getByText("未绑定 VirtualCellPack", { exact: true }),
  ).toBeVisible();
  await expect(
    result.getByText("未记录 dataset identity", { exact: true }),
  ).toBeVisible();
  await expect(
    result
      .getByText(provenance.execution_identity.fingerprint!, { exact: true })
      .first(),
  ).toBeVisible();
  expectNoBrowserFailures(failures);
});

test("不兼容请求直接报告 abstain 且不伪造预测", async ({ page }) => {
  const failures = collectBrowserFailures(page);
  await selectCell(page, "K562");
  const run = await runChat(page, "敲低 FASN");
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
    "learned_abstain_low_reliability",
  );

  const result = page.getByRole("region", {
    name: `结果 · job ${run.jobId}`,
    exact: true,
  });
  await expect(
    result.getByText("本次未给出预测结论", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    result.getByText("learned_abstain_low_reliability", { exact: true }),
  ).toBeVisible();
  await result.getByRole("tab", { name: "预测", exact: true }).click();
  await expect(
    result.getByText("可靠性判定与原因见「报告」。", { exact: true }),
  ).toBeVisible();
  expectNoBrowserFailures(failures);
});

test("Recent reports 可重新打开后端保存的历史报告", async ({ page }) => {
  const failures = collectBrowserFailures(page);
  await selectCell(page, "PBMC");
  const run = await runChat(page, "激活 STAT1");

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
      name: `结果 · job ${run.jobId}`,
      exact: true,
    }),
  ).toBeVisible();
  expectNoBrowserFailures(failures);
});
