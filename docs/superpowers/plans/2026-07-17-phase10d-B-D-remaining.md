# P10.D-B(前端 playwright e2e)+ D-D(.53 远端亲验 + 完成闸门)实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: D-B 用 superpowers:subagent-driven-development(fresh subagent/task + 两阶段审查);D-D **控制器亲自执行**(远端 SSH + 诚实核验,不派 subagent)。Steps 用 checkbox(`- [ ]`)。

**Goal:** 补齐 Phase 10 D 余下两块 —— D-B 前端 5 阶段 happy path + 6 tab playwright e2e(支撑门槛 #13 UI e2e),D-D 控制器 SSH .53 亲验 6 远端项 + 出 `PHASE10_GATE.md` 13 指标诚实对账表(完成闸门)。

**Architecture:** D-B 走 role/text 选择器(抗前端 WIP CSS,零像素/CSS 断言),uvicorn 单进程同源托管 `/api/*` + dist,playwright `webServer` 先 build 再启 uvicorn。D-D 复用 M2 Task5 的 .53 亲验模式(rsync 分支不 push、跑完恢复干净、生产 :8000 零扰动),GATE.md 照 spec §2.3 原表逐条列但状态列诚实标(收窄/支撑不到项**绝不打绿**)。

**Tech Stack:** `@playwright/test`(仅前端 devDep,用户 D2 已拍板)+ chromium;pytest `-m remote`/`-m integration`(现有栈);SSH/rsync。

**Spec:** `docs/superpowers/specs/2026-07-16-phase10d-delivery-completion-gate-design.md`(§4.B D-B / §4.D D-D / §2.3 门槛表 / §2.6 远端项,用户已批 `9a2c6c6`)

**基线:** main = HEAD = `efb3f4c`(D-A/D-C 本地部分收官),分支 `feat/v0.9-phase0-module-core`。稳定基线 `-m "not llm"` = **912 / 40 / 9 deselected / 0**(praxis_virtualcell 包口径)。

---

## 勘察确立的真值地基(2026-07-17 只读勘察 + 实测,写进本计划)

**前端实际锚点(实测,非 spec 假设)**:
- 宿主 = `praxis_vc_react/src/components/layout/AppShell.tsx`(spec 写 `src/AppShell.tsx` 是**错的**,实际在 `components/layout/`;不影响 playwright 走 DOM,仅路径订正)。**全 `src/` 零 `data-testid`** → 只能 role/text/label。
- 5 阶段 heading(全 `<h1>`,**除 results 是 `<h2>`**):`描述一次扰动实验` / `核对任务解读` / `预计涉及的功能模块` / `运行前确认` / `结果 · job {id}`(中点 U+00B7)。
- 推进按钮(原生 `<button>`,含全角箭头 `→` U+2192):`解读任务 →`(busy→`解读中…`)/ `确认并继续 →`(disabled 直到 species 非空)/ `下一步 →` / `开始运行 →`(running→`运行中…`)。
- Ask 输入:`<label htmlFor="ask-input">研究问题</label>`,`getByLabel('研究问题')` 命中 textarea,**默认已预填 `在 human 细胞敲 AHR`**。
- Route amber 横幅:`这里是预期,不是实际结果。`
- 6 tab(`role="tab"`,顺序):`报告 / 预测 / 模块路由 / 证据 / 运行轨迹 / 溯源`。
- 6 tab 面板 h2(`Card title`→`<h2>`):`概要`(恒有)/ `结果可靠性`(非 abstain+有预测)/ `路由摘要`(module_plan 非空)/ `证据与审计`(有规则/模型/治理字段/证据等级)/ `运行轨迹`(恒有)/ `运行标识`(provenance 非空,外层 Card 是 `溯源`,内层 h2 是 `运行标识`)。
- **实测默认 query「在 human 细胞敲 AHR」≈ S2**:`abstain=False`、prediction `{'delta':[0.3]}`、module_plan primary=genetic_hub、provenance 含 rules_hit/rules_referenced/models_used/evidence_level、trace len=32 → **6 tab 全渲染完整内容,4 个条件 h2 全满足**(故可稳妥断 6 个 h2;Task 1 前置验证用真实后端最终确认)。

**前端环境(实测)**:
- `praxis_vc_react/package.json`:`build="tsc -b && vite build"`→`dist/`(已 gitignore、当前已存在);**无 @playwright/test、无 e2e script、无 engines.node**;vite 8/TS 6/React 19.2。
- 后端 = `praxis_vc_api.main:app`,**dist 挂载是 import 时 `if _REACT_DIST.is_dir()`** → **webServer 必须先 build 再启 uvicorn**,否则 `/` 404。`PRAXIS_VC_RUNS` env 隔离 job 产物(默认 `runs/`)。CORS 只放行 :5173,playwright 打 :8000 同源无需 CORS。
- 本机 node v25.8.2 / npm 11.11.1(可装 playwright + build)。**无 e2e/ 无 playwright.config.ts**(从零建)。
- Route 阶段额外发 `GET /api/options`(spec 表只列 /api/modules)。API 全集:`GET /api/health`、`POST /api/parse`、`GET /api/options`、`GET /api/modules`、`POST /api/jobs`、`GET /api/reports/{id}`(+`/trace` `/provenance` `/module-plan` `/markdown`)。

**远端项(实测,6 文件齐,mark 与 spec §2.6 一致)**:
| 文件 | mark 现状 | .53 门控 |
|---|---|---|
| `test_public_models_remote.py` | `pytestmark = pytest.mark.remote`(3 test 全 remote) | torch+GPU + `SCGPT_CKPT_STEM`/`GEARS_CKPT` |
| `test_norman_mean_baseline_gated.py` | ⚠️ 模块级是**失效变量** `pytestmark_remote`(拼错);仅 **2 个 `@pytest.mark.remote`**,另 5 个本地跑 | torch + `P7_MEAN_DELTA_CKPT` |
| `test_linux_docker_smoke.py` | `@pytest.mark.integration`(10)+ `skipif(_NO_LINUX_DOCKER)` | Linux + docker |
| `test_t10_4_provenance_gates.py` | **零 mark 零 skipif**(30 本地跑,torch-free stub) | 无;".53 验 Gate A 不误伤真 ML" 是**独立远端 e2e 动作**非该文件标记测试 |
| `test_ml_workflow_e2e.py` | `pytestmark = pytest.mark.remote`(2) | torch + `W4B_CKPT_DIR` |
| `test_t10_2_module_contracts.py` | `@pytest.mark.skipif(_HAS_TORCH)`×1(fail-closed 那条,有 torch 则 skip) | 无;.53 有 torch 时那条 skip(设计如此) |
- conftest(`praxis_virtualcell/tests/conftest.py`)`addinivalue_line` 注册 `llm`/`remote` marker + 无 torch(Mac)自动 skip remote。pyproject 只注册 `integration`、无 `--strict-markers`。

---

## 全局约束(每 task 适用,不可破)

1. **测试口径显式**:`PYTHONPATH=$PWD .venv/bin/python -m pytest <路径> -p no:cacheprovider`,绝不裸跑 pytest,报数标口径。稳定基线 `-m "not llm"`。
2. **红线零触碰**:核心内核(`core/message.py`/`bus.py`/`agent.py`)+ 根 `tests/` + `agents/reliability.py`/`critic.py` 裁决零改。**D-B 只碰 `praxis_vc_react/package.json`(加 devDep+script)+ 新建 `praxis_vc_react/e2e/*.spec.ts` + `playwright.config.ts`,绝不碰 `src/`(尤其 4 个 WIP css)**。
3. **前端 WIP + untracked 全程隔离**:`praxis_vc_react/src/styles/{base,fonts,themes,tokens}.css`(M)+ `.claude/`/`.playwright-mcp/`/`string.jpeg`(??)绝不 stage/touch/revert。**`git add` 只显式列本 task 文件,禁 `git add -A`/`.`**。macOS 外置盘 `._*` AppleDouble 别 stage。
4. **诚实不伪造**:D-B e2e 只断"阶段标题出现/按钮可点/API 发生/tab 面板 h2 出现",零像素/CSS/视觉断言。断言实测为红→停报告不弱化。D-D GATE.md 收窄项(#10 conflict detection / #11 LLM unsupported claim / #12 injection / #3 provenance / #7 多模块 / #5 8/8)**绝不打绿**,照 spec §8 措辞标偏差。
5. **git**:不切分支、不 push;绝不 `--amend` 不属于本 task 的 commit;trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
6. **.53 亲验红线(D-D,同 M2 Task5)**:rsync 分支**不 push origin**,跑完 `git checkout/rm` 恢复 .53 干净,生产 :8000 零扰动。`@playwright/test` **不上 .53**(node v12 build 不了 + e2e 仅本地)。

---

## File Structure

| 文件 | 责任 | 动作 | Task |
|---|---|---|---|
| `praxis_vc_react/package.json` | 加 `@playwright/test` devDep + `e2e` script | Modify | B1 |
| `praxis_vc_react/playwright.config.ts` | testDir/baseURL/viewport/webServer(先 build 再 uvicorn) | Create | B1 |
| `praxis_vc_react/e2e/happy-path.spec.ts` | 5 阶段 happy path 主 spec | Create | B2 |
| `praxis_vc_react/e2e/result-tabs.spec.ts` | 6 tab 断言 spec | Create | B3 |
| `reports/phase10/PHASE10_GATE.md` | 13 指标对账 + .53 远端段(诚实标偏差) | Create | D-D(控制器) |
| `reports/phase10/PHASE10_UI_E2E.md` | UI e2e 结果 + 截图引用(交付物⑥) | Create | B3/收官 |

**不碰 `src/`**;`.gitignore` 加 `praxis_vc_react/test-results/` + `playwright-report/`(playwright 生成物)。

---

# Part D-B:前端 playwright e2e(subagent-driven)

## Task B1:playwright 环境 + webServer + 冒烟 + 前置验证

**Files:** Modify `praxis_vc_react/package.json`;Create `praxis_vc_react/playwright.config.ts`、`praxis_vc_react/e2e/smoke.spec.ts`;Modify `.gitignore`

- [ ] **Step 1: 确认 HEAD** = `efb3f4c`(`git log --oneline -3`)。

- [ ] **Step 2: 装 @playwright/test + chromium**
```bash
cd /Volumes/T7/PRAXIS-virtualcell/praxis_vc_react
npm i -D @playwright/test
npx playwright install chromium
```
Expected: package.json devDependencies 出现 `@playwright/test`;chromium 下载完成。

- [ ] **Step 3: package.json 加 e2e script**

在 `praxis_vc_react/package.json` 的 `scripts` 加:
```json
"e2e": "playwright test",
"e2e:ui": "playwright test --ui"
```

- [ ] **Step 4: 创建 `praxis_vc_react/playwright.config.ts`**

```ts
import { defineConfig } from "@playwright/test";

// D-B 前端 e2e:role/text 选择器抗 WIP CSS;webServer 先 build 出 dist 再启 uvicorn
// (dist 挂载是 uvicorn import 时判断,顺序不能反)。固定 1280×720 规避 StepperRail 响应式降级。
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:8000",
    viewport: { width: 1280, height: 720 },
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: {
    // cwd 默认 = 本 config 所在目录(praxis_vc_react/);先 build,再回 repo root 启 uvicorn
    command:
      'npm run build && cd .. && PRAXIS_VC_RUNS="$(mktemp -d)" PYTHONPATH="$PWD" .venv/bin/python -m uvicorn praxis_vc_api.main:app --host 127.0.0.1 --port 8000',
    url: "http://127.0.0.1:8000/api/health",
    reuseExistingServer: !process.env.CI,
    timeout: 180000,
  },
});
```

- [ ] **Step 5: 冒烟 spec `praxis_vc_react/e2e/smoke.spec.ts`(先证 webServer + 首屏可达)**

```ts
import { test, expect } from "@playwright/test";

test("首屏到达 Ask 阶段", async ({ page }) => {
  await page.goto("/");
  // Ask 阶段 heading(h1)
  await expect(page.getByRole("heading", { name: "描述一次扰动实验" })).toBeVisible();
  // 研究问题输入存在且已预填默认 query
  await expect(page.getByLabel("研究问题")).toBeVisible();
  // 推进按钮可点
  await expect(page.getByRole("button", { name: "解读任务 →" })).toBeEnabled();
});
```

- [ ] **Step 6: 跑冒烟,确认 webServer 起得来 + 首屏绿**
```bash
cd /Volumes/T7/PRAXIS-virtualcell/praxis_vc_react
npm run e2e -- smoke.spec.ts 2>&1 | tail -20
```
Expected: `1 passed`。**若 webServer 启动失败**(build 报错 / uvicorn 端口占用 / dist 404)→ 停,报告实际错误(调 command 路径/端口),别硬凑。

- [ ] **Step 7: 前置验证默认 query 产出完整 6 tab(D-B 核心风险点)**

冒烟通过后,手动跑一次完整 happy path 确认 4 个条件 h2 真渲染(临时加进 smoke 或用 e2e:ui)。核验点:走完 ask→review→route→run→results 后,依次点 6 tab,确认 `概要`/`结果可靠性`/`路由摘要`/`证据与审计`/`运行轨迹`/`运行标识` 六个 h2 **都出现**(非 EmptyState 文案「本次未给出预测结论」「未产生模块路由」「暂无证据明细」「暂无溯源信息」)。
```bash
# 用 headed 或 --debug 观察一次;或临时在 smoke 里走完流程 dump 每个 tab 面板文本
```
Expected: 6 h2 全出现(实测 S2 应满足)。**若某 tab 落 EmptyState** → 停,报告是哪个 tab + 实际文案,控制器据实调整 Task B3 的断言(改断 EmptyState 或放宽为"面板可达")。**这一步定死 B3 的断言真值。**

- [ ] **Step 8: .gitignore 加 playwright 生成物 + Commit**
```bash
cd /Volumes/T7/PRAXIS-virtualcell
grep -q "playwright-report" .gitignore || printf '\n# D-B playwright 生成物\npraxis_vc_react/test-results/\npraxis_vc_react/playwright-report/\n' >> .gitignore
git add praxis_vc_react/package.json praxis_vc_react/package-lock.json praxis_vc_react/playwright.config.ts praxis_vc_react/e2e/smoke.spec.ts .gitignore
git status --short   # 确认无 src/ WIP css、无 ._、无 node_modules 误 stage(node_modules 应已 gitignore)
git commit -F - <<'EOF'
test(phase10d): Task B1 playwright 环境 + webServer + 冒烟 e2e

@playwright/test devDep(用户 D2 拍板,仅前端不上 .53)+ playwright.config.ts(role/text
选择器抗 WIP、webServer 先 build 再 uvicorn 同源托管、固定 1280×720)+ smoke spec 证首屏
到达 Ask。前置验证默认 query「在 human 细胞敲 AHR」6 tab 全渲染完整内容。不碰 src/。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD ; git status --short
```
Expected: 只 package.json/package-lock.json/playwright.config.ts/smoke.spec.ts/.gitignore 入 commit;`src/` 4 css 仍未 stage;node_modules 未入库。

---

## Task B2:5 阶段 happy path 主 spec

**Files:** Create `praxis_vc_react/e2e/happy-path.spec.ts`

- [ ] **Step 1: 确认 HEAD** = Task B1 commit。

- [ ] **Step 2: 写 `praxis_vc_react/e2e/happy-path.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

// 5 阶段 happy path:ask→review→route→run→results 五跳全绿。
// 选择器全走 role/text/label(抗前端 WIP CSS);API 调用是阶段推进的硬证据(waitForResponse)。
test("5 阶段 happy path 五跳到达 Results", async ({ page }) => {
  await page.goto("/");

  // ── 阶段 1:Ask ──(heading + 预填输入 + 点解读任务 → POST /api/parse)
  await expect(page.getByRole("heading", { name: "描述一次扰动实验" })).toBeVisible();
  await page.getByLabel("研究问题").fill("在 human 细胞敲 AHR");
  const parseResp = page.waitForResponse(
    (r) => r.url().includes("/api/parse") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "解读任务 →" }).click();
  await parseResp;

  // ── 阶段 2:Review ──(heading 出现 → species 已回填 → 点确认并继续)
  await expect(page.getByRole("heading", { name: "核对任务解读" })).toBeVisible();
  const reviewNext = page.getByRole("button", { name: "确认并继续 →" });
  await expect(reviewNext).toBeEnabled();
  await reviewNext.click();

  // ── 阶段 3:Route ──(heading + amber 横幅"这里是预期,不是实际结果。"→ 点下一步)
  await expect(page.getByRole("heading", { name: "预计涉及的功能模块" })).toBeVisible();
  await expect(page.getByText("这里是预期,不是实际结果。")).toBeVisible();
  await page.getByRole("button", { name: "下一步 →" }).click();

  // ── 阶段 4:Run ──(heading → 点开始运行 → POST /api/jobs 同步拿 job_id)
  await expect(page.getByRole("heading", { name: "运行前确认" })).toBeVisible();
  const jobsResp = page.waitForResponse(
    (r) => r.url().includes("/api/jobs") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "开始运行 →" }).click();
  await jobsResp;

  // ── 阶段 5:Results ──(heading /^结果 · job/ 出现 = 五跳到达)
  await expect(page.getByRole("heading", { name: /^结果 · job/ })).toBeVisible();
});
```

- [ ] **Step 3: 跑 happy-path,确认五跳绿**
```bash
cd /Volumes/T7/PRAXIS-virtualcell/praxis_vc_react
npm run e2e -- happy-path.spec.ts 2>&1 | tail -20
```
Expected: `1 passed`。红 → 停报告哪一跳断(dump 该阶段 page 文本),别弱化选择器。

- [ ] **Step 4: 变异证伪(选择器有牙)**
临时把阶段 4 的 `运行前确认` heading name 改成 `不存在的标题XYZ` → 必须 **FAIL**(证明真在等 Run 阶段到达)。改回,重跑绿。

- [ ] **Step 5: Commit**
```bash
cd /Volumes/T7/PRAXIS-virtualcell
git add praxis_vc_react/e2e/happy-path.spec.ts
git commit -F - <<'EOF'
test(phase10d): Task B2 前端 5 阶段 happy path e2e —— 五跳 role/text 选择器

ask→review→route→run→results 五跳:heading 锚阶段、getByLabel 填研究问题、waitForResponse
断 POST /api/parse + /api/jobs 硬证据、amber 横幅"这里是预期"。零像素/CSS 断言抗 WIP。
变异证伪 Run 阶段 heading 有牙。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD ; git status --short
```

---

## Task B3:6 tab 断言 spec + 抗 WIP 复跑 + UI e2e 交付物

**Files:** Create `praxis_vc_react/e2e/result-tabs.spec.ts`;Create `reports/phase10/PHASE10_UI_E2E.md`

- [ ] **Step 1: 确认 HEAD** = Task B2 commit。

- [ ] **Step 2: 写 `praxis_vc_react/e2e/result-tabs.spec.ts`**(断言真值 = Task B1 Step 7 前置验证坐实的 6 h2)

```ts
import { test, expect } from "@playwright/test";

// 先走完 5 阶段到 Results,再逐个点 6 tab 断面板 h2。切 tab 是纯前端不发请求。
async function reachResults(page) {
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
```
> ⚠️ 若 Task B1 Step 7 前置验证发现某 tab 落 EmptyState(非上表 h2),此处对应行改为断该 tab 的 EmptyState 文案(如 `暂无证据明细`),**据实测真值**,不硬写不存在的 h2。

- [ ] **Step 3: 跑 result-tabs,确认 6 tab 绿**
```bash
cd /Volumes/T7/PRAXIS-virtualcell/praxis_vc_react
npm run e2e -- result-tabs.spec.ts 2>&1 | tail -20
```
Expected: `1 passed`。红 → 停报告哪个 tab 断(dump 面板文本核实真实 h2/EmptyState),据实测订正。

- [ ] **Step 4: 全 e2e 复跑 + 抗 WIP 验证(spec §5.3,控制器关注点)**
```bash
cd /Volumes/T7/PRAXIS-virtualcell
git status --short | grep "styles/" && echo "前端 WIP CSS 仍是 M(未提交)——下面复跑证明 e2e 在 WIP 状态下仍绿"
cd praxis_vc_react && npm run e2e 2>&1 | tail -15
```
Expected: 全部 spec passed(smoke + happy-path + result-tabs)。**在当前 4 个 WIP CSS 未提交状态下全绿 = 证明 role/text 选择器真抗 WIP**(spec §5.3 前置验证)。

- [ ] **Step 5: 截图 + UI e2e 交付物**
```bash
cd /Volumes/T7/PRAXIS-virtualcell/praxis_vc_react
# 用 playwright 截 Results 页(6 tab 之一)存证
npx playwright test --project=chromium result-tabs.spec.ts --reporter=list
# 截图落 reports/phase10/(若 playwright trace/screenshot 有产物,择一存;或补一个 screenshot spec)
```
写 `reports/phase10/PHASE10_UI_E2E.md`(交付物⑥):
```markdown
# PHASE 10 — UI E2E(前端 playwright)

> D-B 前端 e2e:5 阶段 happy path 五跳 + 6 tab 面板可达。选择器全 role/text/label(抗前端 WIP CSS,零像素/CSS 断言)。webServer 先 build 再 uvicorn 同源托管。

## 覆盖(诚实边界)
- ✅ 5 阶段推进:ask→review→route→run→results,waitForResponse 断 POST /api/parse + /api/jobs 硬证据。
- ✅ 6 tab 可达 + 面板 h2:概要/结果可靠性/路由摘要/证据与审计/运行轨迹/运行标识(默认 query「在 human 细胞敲 AHR」产出完整结果)。
- ❌ **不覆盖** abstain/failed 深层数值(那是内核 pytest 的活);不覆盖像素/CSS/视觉。
- 门槛 #13「UI 5 阶段 e2e 全通过」= 五跳全绿 + 6 tab 面板 h2 出现。

## 实跑结果
（填入 `npm run e2e` 的 passed 汇总 + 口径）
```

- [ ] **Step 6: Commit**
```bash
cd /Volumes/T7/PRAXIS-virtualcell
git add praxis_vc_react/e2e/result-tabs.spec.ts reports/phase10/PHASE10_UI_E2E.md
git commit -F - <<'EOF'
test(phase10d): Task B3 前端 6 tab e2e + UI e2e 交付物⑥

Results 6 tab 逐个点击断面板 h2(概要/结果可靠性/路由摘要/证据与审计/运行轨迹/运行标识)。
全 e2e 在前端 WIP CSS 未提交状态复跑全绿 = role/text 选择器真抗 WIP(spec §5.3)。
PHASE10_UI_E2E.md 诚实标覆盖边界(不覆盖 abstain 深层/像素)。门槛 #13 UI e2e 支撑。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD ; git status --short
```

---

# Part D-D:.53 远端亲验 + 完成闸门 GATE.md(控制器亲自执行,不派 subagent)

> **为何控制器亲自**:.53 远端交互(SSH/rsync/env/GPU)+ GATE.md 诚实核验(13 指标 met/narrowed/unsupported 判定)需要项目全局判断,同 M2 Task5 模式。**不写成 subagent 逐 task**,控制器按下列清单执行,每步实测记录。

## D-D.1:.53 远端亲验 6 项(控制器 SSH,同 M2 Task5)

- [ ] **前置**:读 memory `remote-server.md`(坐标 `zkyd@10.102.106.53`,项目 `/home/zkyd/data1/mzy/PRAXIS-virtualcell`)。确认 .53 可 SSH、有 GPU+torch、GEARS_CKPT/SCGPT_CKPT_STEM/P7_MEAN_DELTA_CKPT/W4B_CKPT_DIR 就位(不就位则该项标 pending+backlog,不阻塞)。
- [ ] **同步分支到 .53**:`git checkout feat/v0.9-phase0-module-core` 的当前 HEAD **rsync 到 .53**(不 push origin;同 M2 Task5:`rsync` 传文件或 .53 上 `git fetch` 本地 remote)。记录 .53 同步前的 HEAD(跑完恢复用)。
- [ ] **跑 6 远端项**(逐一,标口径):
  - `PYTHONPATH=$PWD python -m pytest praxis_virtualcell/tests/test_public_models_remote.py -p no:cacheprovider -m remote`(M2 GEARS 真 delta 非 mock、scGPT==donor atol 1e-6)
  - `... test_norman_mean_baseline_gated.py -m remote`(仅 2 条 remote:ΔPearson pin 0.4615 复算、SelfTrained run_prediction)
  - `... test_ml_workflow_e2e.py -m remote`(donor ML 真 e2e、norman score、abstain_gain)
  - `... test_linux_docker_smoke.py -m integration`(docker build+run、/api/health、offline demo <60s)—— 需 Linux+docker
  - **独立远端 e2e 动作**:.53 上跑真 donor ML 经 run_query,亲验 **Gate A(per-call hash 完整性)不 fail-closed 误伤真 ML**(C2 §5 风险2 预言实例;test_t10_4 本地零 mark,此为端到端验证)
  - `... test_t10_2_module_contracts.py`(核实有 torch 时 fail-closed 那条 skip、真推理由 test_public_models_remote 承担)
- [ ] **恢复 .53 干净**:跑完 `git checkout .`/`git checkout <原HEAD>`/`git clean` 恢复,**生产 :8000 uvicorn 零扰动**(生产无 GEARS_CKPT→fail-closed mock,不受影响)。核实 .53 `git status` 干净。
- [ ] **每项结果记入 GATE.md 远端段**(真值:delta 范围/负值数/atol/passed 数/ΔPearson pin;.53 不可用的项标 pending+backlog,不伪造)。

## D-D.2:PHASE10_GATE.md 13 指标对账表(控制器诚实核验)

- [ ] **写 `reports/phase10/PHASE10_GATE.md`**:照 spec §2.3 的 13 指标**原表逐条列**(审计锚点),但**状态列诚实标** met/narrowed/unsupported/needs_new + 偏差列。**收窄/支撑不到项绝不打绿勾**:
  - #1 offline runtime 100% ✅ met(D-A 全量 912/0);#2 schema 100% ✅ met;#4 trace replay ✅ met(同请求重跑字节等价);#8 wrong accept ≤5% ✅ met(实测 0)。
  - #3 provenance = ⚠️ narrowed(present-check + 防御断言,**非缺失率/非跨版本防篡改**);#5 8/8 = ✅ met(带限定)**不打"8/8 真实模型"**(引擎级仅 M2*/M3/M4/M7,M1/M5/M8 advisory,M6 limitation);#7 多模块 = 重定义为 module_plan 多 entry 路由+advisory(**非多预测器 fan-out**,C1 证伪),D-A 8 跨模块 case 全绿达该重定义;#9 unsupported abstain = ⚠️ narrowed(绝对断言无测得率);#12 injection = ⚠️ narrowed(结构性防御推论非测得 bypass 率)。
  - #6 单模块正例率 = 🔨 needs_new → 诚实收窄为"4 真实引擎 e2e 全绿 + 路由 golden 全绿"(不编百分比);#13 UI e2e = ✅(D-B 补,五跳+6 tab 全绿)。
  - **#10 conflict detection ≥90% = ❌ unsupported(最大收窄)**:实为 module_plan 内部一致性 gate、罕触发、无 20 条 conflict_cases,**paper 须明标非独立结果冲突检测,绝不打绿**;**#11 LLM unsupported claim=0 = ❌ unsupported**:narrative gate 仅 abstain+仅浮点+hedge 词可绕,**不得声称覆盖 §128,绝不打绿**。
  - G2 五类:①fallback ✅ ②schema adapter ✅ ③routing golden ⚠️(confidence 字段未实现)④per-call hash ✅ ⑤critic 分层 ⚠️(markdown 近似非严格 4 路字段)。
- [ ] **前置验证(D-D opus final review 重点,spec §5.1)**:GATE.md 每条 met 声明须有实测测试支撑;narrowed/unsupported 照 §8 措辞;**照原表打绿勾 = 把 C4 抓 11 次的过度声称搬进验收表**——控制器逐条核对不打假绿。
- [ ] **Commit GATE.md + UI_E2E**(若 B3 未提交 UI_E2E 则一并)。

## D-D 收官(控制器)

- [ ] **opus final review**(fresh 只读):重点 GATE.md 无假绿(收窄项照 §8)、D-B e2e 抗 WIP 真绿、.53 亲验真值非伪造、红线全清。
- [ ] **勾账**:UPGRADE-PROGRESS.md + memory + MEMORY.md 记 D-B/D-D 收官(标口径,记 .53 不可用项 pending 若有)。
- [ ] **AskUserQuestion**:是否 FF 合并 main;Phase 10 是否整体收官打里程碑 tag。

---

## Self-Review

**1. Spec 覆盖**(本计划 = D-B + D-D):
- spec §4.B D-B(5 阶段 + 6 tab,role/text,uvicorn webServer)→ Task B1(环境+webServer+前置验证)/B2(5 阶段)/B3(6 tab+抗 WIP+UI 交付物)。✅ 选择器基于**实测锚点**非 spec 假设。
- spec §4.D D-D(13 指标 GATE + .53 6 远端项)→ D-D.1(.53 亲验)/D-D.2(GATE.md)。✅ 收窄项照 §8 不打绿。
- spec §2.6 6 远端项 → D-D.1 逐一(mark 现状已实测,test_norman 仅 2 条 remote、test_t10_4 是独立 e2e 动作已标注)。
- 交付物⑥ UI 截图 → B3 Step 5;GATE.md → D-D.2。

**2. 占位符扫描**:B1-B3 有完整 config/spec 代码 + 命令 + 预期。**唯一"据实测调整"点 = B3 断言依赖 B1 Step 7 前置验证**(已实测 S2 应满足 6 h2,兜底"落 EmptyState 则停报告"),非 placeholder 而是诚实兜底。D-D 是控制器亲自清单(远端命令据 .53 实况,标 pending 不伪造)。

**3. 类型一致性**:playwright 选择器全用实测锚点(heading/button/tab/label 文案逐字);webServer command 的 build→uvicorn 顺序与"dist import 时挂载"事实一致;6 tab 名/h2 与勘察表一致。

**4. 变异要求**:B2(Run heading 变异)、B3(EmptyState 兜底)证选择器有牙,防"页面加载了就算过"的假绿。

**5. 红线**:D-B 只碰 package.json + e2e/ + config,**绝不碰 src/**(4 WIP css 隔离);.53 rsync 不 push、跑完恢复干净。
