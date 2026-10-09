import { expect, test } from "@playwright/test";
import {
  collectBrowserFailures,
  expectNoBrowserFailures,
  runChat,
  selectCell,
} from "./chat-helpers";

const CASES = [
  { name: "mobile", width: 375, height: 812 },
  { name: "tablet", width: 768, height: 1024 },
];

for (const responsiveCase of CASES) {
  test(`${responsiveCase.name} 可完成选 cell → 直接报告`, async ({ page }) => {
    const failures = collectBrowserFailures(page);
    await page.setViewportSize({
      width: responsiveCase.width,
      height: responsiveCase.height,
    });
    await selectCell(page, "K562");
    await expect(
      page.getByText(
        /语言辅助只解析与解释文字；数据、模拟、数值与最终裁决由确定性后端完成。/,
      ),
    ).toBeVisible();
    if (responsiveCase.width <= 760) {
      await expect(
        page.locator("details.chat-mobile-history > summary"),
      ).toHaveText("Reports");
    }

    const run = await runChat(page, "敲低 AHR");
    const result = page.getByRole("region", {
      name: `结果 · job ${run.jobId}`,
      exact: true,
    });
    await expect(result).toBeVisible();
    await result.getByRole("tab", { name: "数据与执行身份", exact: true }).click();
    await expect(
      result.getByText("未绑定 VirtualCellPack", { exact: true }),
    ).toBeVisible();
    if (responsiveCase.width <= 760) {
      const mobileHistory = page.locator("details.chat-mobile-history");
      await mobileHistory.locator("summary").click();
      const reportEntry = mobileHistory
        .locator(".chat-history-item")
        .filter({ hasText: "human · AHR" })
        .first();
      await expect(reportEntry).toBeVisible();
      await reportEntry.click();
      await expect(
        page.getByRole("region", { name: "Saved report", exact: true }),
      ).toBeVisible();
    }
    expectNoBrowserFailures(failures);
  });
}
