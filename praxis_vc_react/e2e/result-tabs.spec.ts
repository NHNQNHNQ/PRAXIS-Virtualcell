import { test, expect, type Page } from "@playwright/test";

// 先走完 5 阶段到 Results,再逐个点 6 tab 断面板 h2(切 tab 纯前端不发请求)。
async function reachResults(page: Page): Promise<void> {
  await page.goto("/");
  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await page.getByRole("button", { name: "确认并继续 →" }).click();
  await page.getByRole("button", { name: "下一步 →" }).click();
  await page.getByRole("button", { name: "开始运行 →" }).click();
  await expect(page.getByRole("heading", { name: /^结果 · job/ })).toBeVisible();
}

const TABS: Array<[string, string]> = [
  ["报告", "概要"],
  ["预测", "结果可靠性"],
  ["模块路由", "路由摘要"],
  ["证据", "证据与审计"],
  ["运行轨迹", "运行轨迹"],
  ["溯源", "运行标识"],
];

test("Results 6 tab 逐个可达 + 面板 h2 出现", async ({ page }) => {
  await reachResults(page);
  for (const [tab, h2] of TABS) {
    await page.getByRole("tab", { name: tab }).click();
    await expect(page.getByRole("heading", { name: h2 })).toBeVisible();
  }
});

test("1280×720 Results 动作区不挤压标题或按钮", async ({ page }) => {
  await reachResults(page);

  const title = page.getByRole("heading", { name: /^结果 · job/ });
  const card = page.getByRole("region", { name: /^结果 · job/ });
  const actions = page.getByRole("group", { name: "结果操作" });
  const buttons = actions.getByRole("button");

  await expect(title).toBeVisible();
  await expect(card).toBeVisible();
  await expect(actions).toBeVisible();
  await expect(buttons).toHaveCount(5);

  const layout = await card.evaluate((element) => {
    const heading = element.querySelector("h2");
    const actionGroup = element.querySelector<HTMLElement>(".card-actions");
    const actionButtons = [...(actionGroup?.querySelectorAll("button") ?? [])];
    if (!(heading instanceof HTMLElement) || !actionGroup) {
      throw new Error("Results card header structure is missing");
    }

    const titleRect = heading.getBoundingClientRect();
    const actionRect = actionGroup.getBoundingClientRect();
    const separated =
      titleRect.right <= actionRect.left + 1 ||
      titleRect.bottom <= actionRect.top + 1 ||
      actionRect.bottom <= titleRect.top + 1;

    return {
      cardFits: element.scrollWidth <= element.clientWidth + 1,
      actionsFit: actionGroup.scrollWidth <= actionGroup.clientWidth + 1,
      titleAndActionsSeparated: separated,
      buttons: actionButtons.map((button) => {
        const rect = button.getBoundingClientRect();
        return {
          horizontal: rect.width > rect.height,
          contentFits:
            button.scrollWidth <= button.clientWidth + 1 &&
            button.scrollHeight <= button.clientHeight + 1,
          whiteSpace: getComputedStyle(button).whiteSpace,
        };
      }),
    };
  });

  expect(layout.cardFits).toBe(true);
  expect(layout.actionsFit).toBe(true);
  expect(layout.titleAndActionsSeparated).toBe(true);
  expect(layout.buttons).toHaveLength(5);
  for (const button of layout.buttons) {
    expect(button.horizontal).toBe(true);
    expect(button.contentFits).toBe(true);
    expect(button.whiteSpace).toBe("nowrap");
  }
});
