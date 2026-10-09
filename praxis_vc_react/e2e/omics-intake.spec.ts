import { expect, test } from "@playwright/test";

const uploadId = "11111111-1111-4111-8111-111111111111";

test("omics intake returns a quarantined upload identity and manual next step", async ({
  page,
}) => {
  await page.route("**/api/data-catalog", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        schema_version: "vc.data-catalog.v1",
        species: [
          {
            id: "human",
            taxon_id: "NCBITaxon:9606",
            scientific_name: "Homo sapiens",
          },
        ],
        datasets: [],
        upload: {
          enabled: true,
          quarantine_only: true,
          max_file_bytes: 1024,
          total_quota_bytes: 4096,
          accepted_extensions: [".h5ad"],
        },
      }),
    });
  });
  await page.route("**/api/data-uploads", async (route) => {
    expect(route.request().headers().authorization).toBe("Bearer operator-token");
    expect(route.request().postData() ?? "").toContain("cells.h5ad");
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        schema_version: "vc.upload-receipt.v1",
        upload_id: uploadId,
        status: "quarantined",
        species: "human",
        filename: "cells.h5ad",
        size_bytes: 10,
        sha256: "a".repeat(64),
        declared_content_type: "application/octet-stream",
        created_at: "2026-08-13T00:00:00Z",
      }),
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Omics intake", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "物种组学数据资源", exact: true }),
  ).toBeVisible();

  await page.getByLabel("上传物种").selectOption("human");
  await page.getByLabel("上传令牌").fill("operator-token");
  await page.getByLabel("组学数据文件").setInputFiles({
    name: "cells.h5ad",
    mimeType: "application/octet-stream",
    buffer: Buffer.from("tiny-omics"),
  });
  await page.getByRole("button", { name: "上传到隔离区", exact: true }).click();

  const receipt = page.getByRole("status");
  await expect(receipt).toContainText(`Upload ID ${uploadId}`);
  await expect(receipt).toContainText(
    `praxis-vc pack factory-init --data-root /ABSOLUTE/DATA-ROOT --upload-id ${uploadId} --store /ABSOLUTE/NEW-FACTORY-STORE`,
  );
  await expect(receipt).toContainText(
    "该命令不解析数据、不生成 candidate，也不注册 Pack",
  );
});
