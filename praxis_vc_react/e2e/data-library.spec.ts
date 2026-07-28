import { expect, test } from "@playwright/test";

test("species data library filters datasets and quarantines an upload", async ({
  page,
}) => {
  await page.goto("/");

  await page.getByRole("button", { name: "数据资源" }).click();
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
  await page.getByRole("button", { name: "数据资源" }).click();

  const unavailable = page.getByRole("button", { name: "服务器文件未就绪" });
  await expect(unavailable.first()).toBeDisabled();
});
