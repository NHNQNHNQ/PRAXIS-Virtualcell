import { expect, test } from "@playwright/test";

const NAV_ITEMS = [
  "Dashboard",
  "Organisms",
  "Datasets",
  "VirtualCellPacks",
  "Virtual Cells",
  "Agent Runs",
];

test("默认 Dashboard 以现有后端目录展示平台真实边界", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Dashboard", exact: true }),
  ).toBeVisible();
  const navigation = page.getByRole("navigation", { name: "主导航" });
  for (const item of NAV_ITEMS) {
    await expect(
      navigation.getByRole("button", { name: item, exact: true }),
    ).toBeVisible();
  }

  await expect(page.getByText("4 个物种", { exact: true })).toBeVisible();
  await expect(page.getByText("4 个数据集", { exact: true })).toBeVisible();
  await expect(page.getByText("5 个文件", { exact: true })).toBeVisible();
  await expect(
    page.getByText("3 个 VirtualCellPack", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(/都不代表模型可执行或已经科学验证/),
  ).toBeVisible();

  await navigation.getByRole("button", { name: "Organisms" }).click();
  await expect(
    page.getByText(/不推导 VirtualCell readiness、模型兼容性或科学有效性/),
  ).toBeVisible();
  for (const species of [
    "Homo sapiens",
    "Mus musculus",
    "Saccharomyces cerevisiae",
    "Escherichia coli",
  ]) {
    await expect(page.getByText(species, { exact: true })).toBeVisible();
  }

  await navigation
    .getByRole("button", { name: "VirtualCellPacks" })
    .click();
  for (const pack of [
    "p8-human-tiny",
    "p8-mouse-tiny",
    "p8-bacteria-tiny",
  ]) {
    await expect(page.getByText(pack, { exact: true })).toBeVisible();
  }
});

test("虚拟细胞诚实空态且 Agent Runs 保留既有五阶段", async ({ page }) => {
  await page.goto("/");
  const navigation = page.getByRole("navigation", { name: "主导航" });

  await navigation.getByRole("button", { name: "Virtual Cells" }).click();
  await expect(page.getByText(/尚无.*虚拟细胞实例/)).toBeVisible();
  await expect(page.getByText(/未提供.*构建 API/)).toBeVisible();

  await navigation.getByRole("button", { name: "Agent Runs" }).click();
  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验" }),
  ).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "阶段进度" }).getByRole("button"),
  ).toHaveCount(5);
});

test("Agent Run 目录失败时不把未知状态冒充为零", async ({ page }) => {
  await page.route("**/api/jobs", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "jobs unavailable" }),
    });
  });

  await page.goto("/");

  await expect(page.getByText(/Agent Run 目录不可用/).first()).toBeVisible();
  await expect(page.getByText(/当前记录 0 个 Agent Run/)).toHaveCount(0);
});

test("平台目录失败时保持不可用状态且不显示伪造计数", async ({ page }) => {
  await page.route("**/api/data-catalog", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "catalog unavailable" }),
    });
  });

  await page.goto("/");

  await expect(page.getByText(/平台目录不可用/)).toBeVisible();
  await expect(page.getByText(/个物种$/)).toHaveCount(0);
  await expect(page.getByText(/个数据集$/)).toHaveCount(0);
  await expect(page.getByText(/个 VirtualCellPack$/)).toHaveCount(0);
});
