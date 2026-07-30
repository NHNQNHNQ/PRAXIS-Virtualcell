import { expect, test } from "@playwright/test";

const NAV_ITEMS = [
  "Virtual Cells",
  "Agent Workspace",
  "Reports",
  "Data Center",
  "My Cells",
  "Settings",
];

test("默认首页以 Virtual Cell-first 叙事展示真实底座", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", {
      name: "A trustworthy foundation for virtual-cell research.",
      exact: true,
    }),
  ).toBeVisible();

  const navigation = page.getByRole("navigation", { name: "主导航" });
  for (const item of NAV_ITEMS) {
    await expect(
      navigation.getByRole("button", { name: item, exact: true }),
    ).toBeVisible();
  }

  await expect(page.getByText("4 datasets · 5 files", { exact: true })).toBeVisible();
  await expect(page.getByText("实例目录尚未提供", { exact: true })).toBeVisible();
  await expect(page.getByText(/不会被前端自动冒充为 Virtual Cell/)).toBeVisible();
  await expect(page.getByText("Ready for analysis", { exact: true })).toHaveCount(0);
});

test("首页问题进入未绑定的受控 Agent Workspace", async ({ page }) => {
  await page.goto("/");
  const query = "在 human 细胞敲低 AHR 后，哪些表达模块可能发生变化？";

  await page.getByLabel("Describe a scientific task").fill(query);
  await page
    .getByRole("button", { name: "Open unbound Agent Workspace" })
    .click();

  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验" }),
  ).toBeVisible();
  await expect(page.getByLabel("研究问题")).toHaveValue(query);
  await expect(page.getByText("Not bound", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: /结果 · job/ })).toHaveCount(0);
});

test("Virtual Cells 保持诚实空态且 Agent Workspace 保留五阶段", async ({
  page,
}) => {
  await page.goto("/");
  const navigation = page.getByRole("navigation", { name: "主导航" });

  await navigation.getByRole("button", { name: "Virtual Cells" }).click();
  await expect(
    page.getByRole("heading", { name: "Virtual Cells", exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/尚未提供 Virtual Cell registry/)).toBeVisible();
  await expect(page.getByText(/不会自动生成可查询的细胞实例/)).toBeVisible();
  await expect(page.getByRole("button", { name: /Build/ })).toHaveCount(0);

  await navigation
    .getByRole("button", { name: "Agent Workspace" })
    .click();
  await expect(
    page.getByRole("heading", { name: "描述一次扰动实验" }),
  ).toBeVisible();
  await expect(page.getByText("Not bound", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "阶段进度" }).getByRole("button"),
  ).toHaveCount(5);
});

test("Data Center 收拢真实物种、数据和 Pack 入口", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Data Center", exact: true }).click();

  await expect(page.getByRole("main")).toBeFocused();
  await expect(
    page.getByRole("heading", { name: "Data Center", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("4 catalogued taxa", { exact: true })).toBeVisible();
  await expect(page.getByText("4 datasets · 5 files", { exact: true })).toBeVisible();
  await expect(page.getByText("3 Pack records", { exact: true })).toBeVisible();
  await expect(
    page.getByText(/不代表 Virtual Cell 已构建、模型可执行或已经科学验证/),
  ).toBeVisible();

  await page.getByRole("button", { name: /Inspect organisms/ }).click();
  for (const species of [
    "Homo sapiens",
    "Mus musculus",
    "Saccharomyces cerevisiae",
    "Escherichia coli",
  ]) {
    await expect(page.getByText(species, { exact: true })).toBeVisible();
  }
  await expect(
    page.getByText(/不推导 Virtual Cell readiness、模型兼容性或科学有效性/),
  ).toBeVisible();
});

test("Reports 目录失败时不把未知状态冒充为空态", async ({ page }) => {
  await page.route("**/api/jobs", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "jobs unavailable" }),
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Reports", exact: true }).click();

  await expect(page.getByText(/Agent Run 目录不可用/).first()).toBeVisible();
  await expect(page.getByText(/还没有可审计的运行记录/)).toHaveCount(0);
});

test("Reports 在自身上下文中打开后端保存的结果", async ({ page }) => {
  const jobResponse = await page.request.post("/api/jobs", {
    data: {
      request: {
        request_id: "p11-reports-index",
        species: "human",
        cell_type: "K562",
        perturbation_type: "gene",
        perturbation_targets: ["AHR"],
        input_modality: "scRNA",
        output_modality: "delta_expression",
        task_type: "predict_delta_expression",
      },
      mode: "offline",
      enable_llm_report: false,
    },
  });
  expect(jobResponse.status()).toBe(200);
  const { job_id: jobId } = (await jobResponse.json()) as { job_id: string };

  await page.goto("/");
  const navigation = page.getByRole("navigation", { name: "主导航" });
  await navigation.getByRole("button", { name: "Reports", exact: true }).click();
  const report = page.getByRole("article").filter({ hasText: jobId });
  await report.getByRole("button", { name: "Open report" }).click();

  await expect(
    navigation.getByRole("button", { name: "Reports", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await expect(
    page.getByRole("heading", { name: "Report", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", {
      name: `结果 · job ${jobId}`,
      exact: true,
    }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Back to Reports" }).click();
  await expect(
    page.getByRole("heading", { name: "Reports", exact: true }),
  ).toBeVisible();
});

test("Data Center 目录失败时不显示伪造计数", async ({ page }) => {
  await page.route("**/api/data-catalog", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "catalog unavailable" }),
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Data Center", exact: true }).click();

  await expect(page.getByText(/数据底座不可用/)).toBeVisible();
  await expect(page.getByText("4 catalogued taxa", { exact: true })).toHaveCount(0);
  await expect(page.getByText("4 datasets · 5 files", { exact: true })).toHaveCount(0);
});

test("后续目录失败时 Data Center 不保留首页的旧计数", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("4 datasets · 5 files", { exact: true })).toBeVisible();

  await page.route("**/api/data-catalog", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "catalog became unavailable" }),
    });
  });
  await page.getByRole("button", { name: "Data Center", exact: true }).click();

  await expect(page.getByText(/数据底座不可用/)).toBeVisible();
  await expect(page.getByText("4 catalogued taxa", { exact: true })).toHaveCount(0);
  await expect(page.getByText("4 datasets · 5 files", { exact: true })).toHaveCount(0);
});

test("My Cells 与 Settings 不伪造未实现的持久化能力", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "My Cells", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "My Cells", exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/尚未提供用户级 Virtual Cell 存储/)).toBeVisible();
  await expect(page.getByText(/隔离区上传不会自动出现在 My Cells/)).toBeVisible();

  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Settings", exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/本页不会保存密钥/)).toBeVisible();
  await expect(
    page.getByText(/语言模型仅用于解析与解释，不参与数据真相/),
  ).toBeVisible();
});
