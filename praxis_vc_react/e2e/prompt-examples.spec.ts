import { expect, test, type Request } from "@playwright/test";
import {
  collectBrowserFailures,
  expectNoBrowserFailures,
  isRequest,
  selectCell,
} from "./chat-helpers";

test("backend preset examples fill the composer and preserve an explicit drug overlay", async ({
  page,
}) => {
  const failures = collectBrowserFailures(page);
  const optionsResponsePromise = page.waitForResponse((response) =>
    isRequest(response.request(), "GET", "/api/options"),
  );

  await selectCell(page, "K562");
  const options = (await (await optionsResponsePromise).json()) as {
    cell_presets: Array<{
      cell_type: string;
      example_perturbation_type?: string;
      example_targets?: string[];
    }>;
  };
  expect(
    options.cell_presets.find((preset) => preset.cell_type === "K562"),
  ).toMatchObject({
    example_perturbation_type: "gene",
    example_targets: expect.arrayContaining(["AHR"]),
  });

  const k562Example = page
    .getByLabel("Example questions")
    .getByRole("button", {
      name: "敲低 AHR 后表达如何变化？",
      exact: true,
    });
  await expect(k562Example).toBeVisible();
  await k562Example.click();
  await expect(page.getByLabel("Message PRAXIS")).toHaveValue(
    "敲低 AHR 后表达如何变化？",
  );

  await page.getByRole("button", { name: "Change cell", exact: true }).click();
  await selectCell(page, "A549", { openPage: false });
  const drugExample = page
    .getByLabel("Example questions")
    .getByRole("button", {
      name: "vorinostat 药物处理后表达如何变化？",
      exact: true,
    });
  await drugExample.click();
  await expect(page.getByLabel("Message PRAXIS")).toHaveValue(
    "vorinostat 药物处理后表达如何变化？",
  );

  const jobs: Request[] = [];
  page.on("request", (request) => {
    if (isRequest(request, "POST", "/api/jobs")) jobs.push(request);
  });
  const parseResponsePromise = page.waitForResponse((response) =>
    isRequest(response.request(), "POST", "/api/parse"),
  );
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  const parseResponse = await parseResponsePromise;
  expect(parseResponse.status()).toBe(200);

  const parseBody = parseResponse.request().postDataJSON() as {
    text: string;
    mode: string;
  };
  const [question, overlay] = parseBody.text.split("\n结构化描述:");
  expect(question).toBe("vorinostat 药物处理后表达如何变化？");
  expect(parseBody.mode).toBe("llm_assisted");
  expect(JSON.parse(overlay)).toEqual({
    species: "human",
    cell_type: "A549",
    perturbation_type: "drug",
    perturbation_targets: ["vorinostat"],
  });

  const parsed = (await parseResponse.json()) as {
    candidate_request: Record<string, unknown>;
  };
  expect(parsed.candidate_request).toMatchObject({
    species: "human",
    cell_type: "A549",
    perturbation_type: "drug",
    perturbation_targets: ["vorinostat"],
  });
  await expect(
    page.getByText("Please confirm this interpretation.", { exact: true }),
  ).toBeVisible();
  await page.waitForLoadState("networkidle");
  expect(jobs).toHaveLength(0);
  expectNoBrowserFailures(failures);
});
