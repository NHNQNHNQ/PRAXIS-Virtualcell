import { expect, test } from "@playwright/test";

import {
  collectBrowserFailures,
  expectNoBrowserFailures,
} from "./chat-helpers";

test("pack library exposes the factory lifecycle and registered catalog", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  let compatibilityRequests = 0;

  page.on("request", (request) => {
    if (
      request.method() === "POST" &&
      new URL(request.url()).pathname === "/api/packs/compatibility"
    ) {
      compatibilityRequests += 1;
    }
  });

  await page.route("**/api/data-catalog", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        schema_version: "vc.data-catalog.v1",
        species: [],
        datasets: [],
        upload: {
          enabled: false,
          quarantine_only: true,
          max_file_bytes: 1024,
          total_quota_bytes: 4096,
          accepted_extensions: [".h5ad"],
        },
      }),
    });
  });
  await page.route("**/api/packs", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        schema_version: "vc.pack-catalog.v1",
        packs: [
          {
            schema_version: "vc.pack-record.v1",
            pack_id: "reviewed-human-pack",
            pack_version: "1.0.0",
            pack_fingerprint: "a".repeat(64),
            manifest_schema_version: "vc.pack.v0.3",
            taxon: {
              ontology_id: "NCBITaxon:9606",
              scientific_name: "Homo sapiens",
            },
            assembly: null,
            modalities: [{ name: "scRNA", ontology_id: "EFO:0008913" }],
            feature_namespaces: [
              {
                name: "EnsemblGene",
                version: "GRCh38",
                id_format: "ensembl_gene",
              },
            ],
            asset_count: 1,
            source: "registered",
            validation_status: "valid",
            pack_valid: true,
            model_compatible: null,
            scientifically_validated: false,
            reasons: [],
          },
        ],
        model_capabilities: [
          {
            name: "research_model",
            version: "1.0.0-research.1",
            fingerprint: "b".repeat(64),
            status: "available",
            species: ["human"],
            taxon: ["NCBITaxon:9606"],
            modalities: [{ name: "scRNA", ontology_id: "EFO:0008913" }],
            cell_domain: {},
            task: "predict_delta_expression",
            outputs: ["delta_expression"],
            feature_namespaces: [
              {
                name: "EnsemblGene",
                version: "GRCh38",
                id_format: "ensembl_gene",
              },
            ],
            scientifically_validated: false,
          },
        ],
        scientifically_validated: false,
      }),
    });
  });
  await page.route("**/api/pack-factory", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        schema_version: "vc.pack-factory-catalog.v1",
        configured: true,
        receipts: [
          {
            receipt_fingerprint: "c".repeat(64),
            status: "quarantined",
            pack_valid: null,
            factory_registered: false,
            model_compatible: null,
            executable: false,
          },
        ],
        candidates: [
          {
            candidate_fingerprint: "d".repeat(64),
            status: "candidate_unvalidated",
            reviewed: true,
            validation_passed: false,
            factory_registered: false,
            pack_valid: null,
            model_compatible: null,
            executable: false,
            scientifically_validated: false,
            production_promoted: false,
          },
        ],
        reviews: [],
        validations: [],
        decisions: [],
        registrations: [],
        supersessions: [],
        review_count: 0,
        validation_count: 0,
        operator_decision_count: 0,
        registration_count: 0,
        supersession_count: 0,
        write_api_enabled: false,
      }),
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Pack library", exact: true }).click();

  await expect(
    page.getByRole("heading", { name: "VirtualCellPacks", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Pack Factory lifecycle", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Pack Factory five-stage status")).toContainText(
    "1 · Quarantine",
  );
  await expect(page.getByLabel("Pack Factory five-stage status")).toContainText(
    "5 · Executable",
  );
  await expect(
    page.getByRole("heading", {
      name: "VirtualCellPack capabilities and validation",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "reviewed-human-pack", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("research_model", { exact: true })).toBeVisible();
  expect(compatibilityRequests).toBe(0);
  expectNoBrowserFailures(failures);
});
