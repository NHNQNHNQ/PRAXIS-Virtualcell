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
  test(`${responsiveCase.name} completes cell selection → direct report`, async ({ page }) => {
    const failures = collectBrowserFailures(page);
    await page.setViewportSize({
      width: responsiveCase.width,
      height: responsiveCase.height,
    });
    await selectCell(page, "K562");
    await expect(
      page.getByText(
        /Language assistance only parses and explains text; the deterministic backend handles data, simulation, numerical results, and final decisions./,
      ),
    ).toBeVisible();
    if (responsiveCase.width <= 760) {
      await expect(
        page.locator("details.chat-mobile-history > summary"),
      ).toHaveText("Reports");
    }

    const run = await runChat(page, "Knock down AHR");
    const result = page.getByRole("region", {
      name: `Results · job ${run.jobId}`,
      exact: true,
    });
    await expect(result).toBeVisible();
    await result.getByRole("tab", { name: "Data and execution identity", exact: true }).click();
    await expect(
      result.getByText("No VirtualCellPack bound", { exact: true }),
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
