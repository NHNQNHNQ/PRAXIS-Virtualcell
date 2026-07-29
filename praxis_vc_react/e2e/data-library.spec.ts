import { expect, test } from "@playwright/test";

test("species data library filters datasets and quarantines an upload", async ({
  page,
}) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Datasets", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "物种组学数据资源" }),
  ).toBeVisible();
  await expect(page.getByText("10x PBMC 1k", { exact: false })).toBeVisible();
  await expect(
    page.getByText("10x E18 Mouse Brain 1k", { exact: false }),
  ).toBeVisible();

  await page.getByLabel("筛选物种").selectOption("mouse");
  await expect(page.getByText("10x PBMC 1k", { exact: false })).toHaveCount(0);
  await expect(
    page.getByText("10x E18 Mouse Brain 1k", { exact: false }),
  ).toBeVisible();

  await page.getByLabel("筛选物种").selectOption("human");
  await page.getByLabel("上传物种").selectOption("human");
  await page.getByLabel("上传令牌").fill(
    "p7-playwright-upload-token-is-at-least-32-bytes",
  );
  await page.getByLabel("组学数据文件").setInputFiles({
    name: "my-cells.h5ad",
    mimeType: "application/octet-stream",
    buffer: Buffer.from("tiny-user-omics"),
  });
  await page.getByRole("button", { name: "上传到隔离区" }).click();

  await expect(page.getByText("已进入隔离区")).toBeVisible();
  await expect(page.getByText("my-cells.h5ad", { exact: false })).toBeVisible();
  await expect(page.getByText("不会自动参与预测")).toBeVisible();
});

test("data library keeps unavailable public files fail-closed", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Datasets", exact: true }).click();

  const unavailable = page.getByRole("button", { name: "服务器文件未就绪" });
  await expect(unavailable.first()).toBeDisabled();
});

test("data library renders backend Pack validation and capability records", async ({
  page,
}) => {
  const compatibilityCalls: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/packs/compatibility")) {
      compatibilityCalls.push(request.url());
    }
  });

  await page.goto("/");
  await page
    .getByRole("button", { name: "VirtualCellPacks", exact: true })
    .click();

  const packs = page.getByRole("region", {
    name: "VirtualCellPack 能力与验证",
  });
  await expect(packs).toBeVisible();
  await expect(packs.getByText("p8-human-tiny", { exact: true })).toBeVisible();
  await expect(packs.getByText("p8-mouse-tiny", { exact: true })).toBeVisible();
  await expect(
    packs.getByText("p8-bacteria-tiny", { exact: true }),
  ).toBeVisible();
  await expect(packs.getByText("EnsemblGene", { exact: true }).first()).toBeVisible();
  await expect(packs.getByText("NCBIGene", { exact: true })).toBeVisible();
  await expect(
    packs.getByText("Pack 校验通过", { exact: true }),
  ).toHaveCount(3);
  await expect(
    packs.getByText("模型兼容：未按请求评估", { exact: true }),
  ).toHaveCount(3);
  await expect(
    packs.getByRole("heading", { name: "模型能力（后端声明）" }),
  ).toBeVisible();
  expect(compatibilityCalls).toEqual([]);
});
