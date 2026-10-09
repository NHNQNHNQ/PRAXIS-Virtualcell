import { expect, test } from "@playwright/test";
import {
  collectBrowserFailures,
  expectNoBrowserFailures,
} from "./chat-helpers";

test("Data Center 按物种和关键词筛选并选择后端 cell preset", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Data Center", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Choose a cell", exact: true }),
  ).toBeVisible();

  const cards = page.getByRole("article");
  await expect(cards).toHaveCount(10);
  const k562 = cards.filter({
    has: page.getByRole("heading", { name: "K562", level: 2, exact: true }),
  });
  await expect(k562).toContainText(
    "1 same-species dataset · 1 Pack record · not bound",
  );

  const filters = page.getByLabel("Species filter");
  await filters.getByRole("button", { name: "mouse", exact: true }).click();
  await expect(cards).toHaveCount(3);
  await expect(
    page.getByRole("heading", { name: "K562", level: 2, exact: true }),
  ).toHaveCount(0);

  await page.getByRole("searchbox", { name: "Search cells" }).fill("fibroblast");
  await expect(cards).toHaveCount(1);
  await expect(
    page.getByRole("heading", {
      name: "fibroblast",
      level: 2,
      exact: true,
    }),
  ).toBeVisible();
  await cards
    .getByRole("button", { name: "Select cell", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "fibroblast",
      level: 1,
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText("mouse · catalog preset", { exact: true })).toBeVisible();
  expectNoBrowserFailures(failures);
});

test("Data Center 无匹配项时显示诚实空态", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Data Center", exact: true }).click();
  await page.getByRole("searchbox", { name: "Search cells" }).fill("no-such-cell");
  await expect(page.getByText("No matching cell presets.", { exact: true })).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(0);
});

test("options 失败时不生成本地假 cell", async ({ page }) => {
  await page.route("**/api/options", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "options unavailable" }),
    });
  });

  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("细胞目录不可用");
  await expect(page.getByRole("article")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "K562", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", {
      name: "Browse all cells in Data Center",
      exact: true,
    }),
  ).toBeDisabled();

  await page.getByRole("button", { name: "Data Center", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("细胞目录不可用");
  await expect(page.getByRole("article")).toHaveCount(0);
  await expect(page.getByLabel("Message PRAXIS")).toHaveCount(0);
});
