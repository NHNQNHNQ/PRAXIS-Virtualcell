# PRAXIS-VirtualCell 前端全面 Playwright E2E 测试计划

> **目标**：在真实网站(uvicorn 同源托管 dist + `/api/*`,offline 确定性)上,用 playwright 系统性验证 5 阶段流程 + 6 tab + 各扰动类型/物种 + abstain 边界 + 主题/历史/下载 + 错误/性能。比 D-B 的 3 个冒烟 spec 更全面,作为前端质量的持续回归基线。
>
> **选择器铁律(抗前端 WIP CSS,继承 D-B)**:只用 `getByRole('heading'|'button'|'tab')` / `getByLabel` / `getByText` / `waitForResponse`。**零 CSS class / data-testid / 像素 / `toHaveScreenshot` 断言**(前端 4 css 是 WIP,随时变)。固定 desktop 1280×720 规避 StepperRail 响应式降级(响应式单列一个专门 suite)。
>
> **诚实边界**:e2e 只断"阶段标题出现 / 按钮可点 / API 发生 / 面板 h2 或 EmptyState 文案出现 / 关键可观测值",**不断像素、不断内核数值正确性**(那是 `praxis_virtualcell/tests` pytest 的活)。断言的真值来自**实测**(每个 case 先真跑一次 dump,不照抄猜测)。

## 0. 环境与前置

**webServer**(playwright.config.ts,D-B 已建,复用):先 `npm run build` 出 dist,再 `cd .. && PRAXIS_VC_RUNS=$(mktemp -d) PYTHONPATH=$PWD .venv/bin/python -m uvicorn praxis_vc_api.main:app --host 127.0.0.1 --port 8000`,`baseURL=http://127.0.0.1:8000`,`url=/api/health`。
- **迭代前端 src 后必须让 webServer 重 build**:`reuseExistingServer:!CI` 会复用残留 uvicorn 对旧 dist 跑出误绿/误红 → 每轮前 `lsof -ti:8000 | xargs kill 2>/dev/null`。
- **offline 恒定**:`/api/health` 返 `llm_enabled:false`;所有断言以 offline 确定性行为为准。LLM 辅助模式(需 DEEPSEEK_API_KEY)单列 suite S10,无 key 时 `test.skip`。

**实测锚点(2026-07-17 勘察 + 亲验,选择器真值)**:
- 5 阶段 heading(h1,**results 是 h2**):`描述一次扰动实验` / `核对任务解读` / `预计涉及的功能模块` / `运行前确认` / `/^结果 · job/`。
- 推进按钮(全角箭头 `→`):`解读任务 →`(busy→`解读中…`)/ `确认并继续 →`(disabled 直到 species 非空)/ `下一步 →` / `开始运行 →`(running→`运行中…`)/ 各阶段 `← 返回`。
- Ask:`getByLabel('研究问题')` textarea(默认预填 `在 human 细胞敲 AHR`);示例 chips `基因扰动`/`药物响应`/`代谢应激`;运行方式 combobox(`离线(结果不经语言模型)` / `辅以语言模型改写文字`);`高级输入(可选)`折叠含物种 combobox(不指定/human/mouse/yeast)。
- Review:载入常用体系 combobox(K562/PBMC/A549/HEK293T/iPSC/mouse T cell/mouse Hematopoietic/mouse Fibroblast/yeast S.cerevisiae/yeast 碳源/E.coli iML1515/E.coli 抗生素)、物种 combobox(bacteria/human/mouse/yeast)、细胞类型 textbox、扰动类型 combobox(drug/gene/gene_combination/ligand/medium)、扰动对象 textbox(`例:AHR, TP53`)、字段状态标签(`已确认`/`可编辑`)。
- Route:amber 横幅 `这里是预期,不是实际结果。` + 模块目录卡片(M1-M8,engines 标注如 `donor_predictor`/`gem_fba, pathway_scoring`,状态 `主`/`预期`/`未启用`)。
- Run:`运行前确认` heading。
- Results:heading `/^结果 · job/`(h2);6 tab `报告`/`预测`/`模块路由`/`证据`/`运行轨迹`/`溯源`;顶部下载 `下载 report.json`/`下载 narrative.md`(offline 禁用)/`下载 report.md`、`复制报告`、`＋ 新建查询`;顶栏 `llm_used_for_prediction: false`。
- 6 tab 面板 h2:`概要` / `结果可靠性` / `路由摘要` / `证据与审计` / `运行轨迹` / `运行标识`。EmptyState:`本次未给出预测结论` / `未产生模块路由` / `暂无证据明细` / `暂无溯源信息`。
- 左侧栏:`＋ 新建查询`、`历史查询`(运行后出现 `human · AHR ...` 条目)、`收藏`(`暂无收藏`)、底栏 `后端 ok · 运行时 v0.3`。
- 主题:顶栏 `切换到深色主题` / `切换到浅色主题`;模式:`切换到「语言模型辅助」` / `切换到「本地模式」`。

**测试数据真值(来自 D-A 16 case 实测;前端经 /api/parse 解析文本,offline 解析只路由 gene→expression,故用 Review 阶段直接改字段构造非 gene/非 expression 请求)**:
| 场景 | 构造方式 | 预期 Results |
|---|---|---|
| gene AHR(in-vocab) | 默认 query | 非 abstain,概要 models_used MockLinear/CPA/GEARS,预测 delta [0.3] |
| gene FASN(OOV) | query「在 human 细胞敲 FASN」 | **abstain**,预测 tab EmptyState「本次未给出预测结论」 |
| mouse gene GATA1 | 高级输入选 mouse + query GATA1 | 非 abstain,delta [0.3],路由 caution(ortholog) |
| bacteria gene b0720 expression | Review 改 species=bacteria/type=gene/对象 b0720 | **abstain**,模块路由 EmptyState「未产生模块路由」 |
| bacteria gene b0720,b1136 growth | Review 改 species=bacteria + 需 output_modality growth(高级输入) | 非 abstain,delta [-1.0,-1.0](真 cobra) |
| human ligand IFNB1 state | Review 改 type=ligand/对象 IFNB1(高级 output state) | 非 abstain,delta [2.485] |

## 1. 测试套件矩阵

### S1 — 5 阶段 happy path(核心,gene AHR)
`smoke` + `happy-path`(D-B 已有)。断五跳 heading + waitForResponse POST /api/parse + /api/jobs。**新增**:每阶段 `← 返回` 可回退且状态保留(Review 改的字段返回 Ask 再进不丢)。

### S2 — 6 tab 全内容 + 下载/复制(gene AHR 非 abstain)
- 逐 tab 点击断 6 h2(D-B result-tabs 已有)。**新增**:①报告 tab 断概要字段(request_id 存在、`使用的模型` 含 MockLinear)、②预测 tab 断「已给出预测」+ delta 值文本出现、③模块路由 tab 断 primary 模块名(genetic_hub/Genetic Hub)、④证据 tab 断有规则/模型条目、⑤溯源 tab 断 request_id/hash 存在。
- 下载:点 `下载 report.json` / `下载 report.md` → `waitForEvent('download')` 断文件名/非空;`下载 narrative.md` 在 offline **应 disabled**(断 `toBeDisabled`)。
- `复制报告` 点击不报错(clipboard 权限授予)。

### S3 — abstain / EmptyState 场景(诚实负例,最重要)
- **gene FASN OOV**:query FASN → Results 预测 tab EmptyState `本次未给出预测结论`;报告 tab 应显式呈现 abstain 原因(断 `未给出预测` 或 abstain reason 文本可见)。**核心 UX 断言:用户能看到"为什么弃权"**。
- **bacteria gene b0720 expression 不可路由**:Review 改 species=bacteria → Results 模块路由 tab EmptyState `未产生模块路由` + 预测 EmptyState。
- 断这些负例下 `＋ 新建查询` 可回 Ask 重来。

### S4 — 各扰动类型 × 物种(Review 阶段构造)
gene / gene_combination / drug / ligand / medium × human / mouse / yeast / bacteria 的可达组合(照上表真值)。每组合走到 Results 断 abstain 与否 + 关键 h2/EmptyState。**用 Review 阶段直接改 combobox/textbox 构造**(因 offline parse 只出 gene→expression)。gene_combination 用「MYC, KRAS」。

### S5 — 预设体系下拉(Review 载入常用体系)
选 `K562 — human`、`E. coli — iML1515 GEM`、`S. cerevisiae — yeast GEM` 等预设 → 断物种/细胞类型字段被正确回填 → 走到 Results。覆盖预设的 12 个选项至少 4 个代表性的。

### S6 — 高级输入(structured JSON)
Ask 展开 `高级输入(可选)`,填结构化 JSON(如 `{"species":"human","perturbation_type":"gene","perturbation_targets":["AHR"],"output_modality":"delta_expression"}`)→ 解读任务 → 断 Review 字段与 JSON 一致 → Results。**边界**:畸形 JSON(缺字段/非法值)→ 断前端优雅降级不崩(不 500,给提示或落 clarify)。

### S7 — 主题切换(深色/浅色)
点 `切换到深色主题` → 断 heading 仍可见(role/text 不受主题影响)+ `切换到浅色主题` 按钮出现;来回切换 → 走完流程仍绿。**零像素断言**,只断结构不因主题崩。resize dark suite(colorScheme dark)复跑 happy-path。

### S8 — 历史查询 + 收藏
跑 2 个不同 query → 断左侧 `历史查询` 出现 2 条(含 query 摘要)→ 点历史条目断能回看该 job 的 Results → 收藏操作(若有收藏按钮)断 `收藏` 从 `暂无收藏` 变有条目。

### S9 — 阶段守卫 / 边界
- 空研究问题:清空 textarea → `解读任务 →` 应 disabled(断 `toBeDisabled`)。
- Review species 为空:清空物种 → `确认并继续 →` disabled。
- 超长/特殊字符 query(emoji、注入样 payload 如 `<script>`、`AHR;DROP TABLE`):断前端不崩、不执行、正常落 parse/clarify(**抗注入 UX 层**)。

### S10 — LLM 辅助模式(需 key,无 key skip)
`test.skip(!process.env.DEEPSEEK_API_KEY)`。切 `语言模型辅助` → 走流程 → Results 顶栏 `llm_used_for_prediction` 仍应 `false`(LLM 只改写 narrative 不改预测)+ narrative.md 下载可用。断**LLM 不改数值**(与 offline 同 query 的 delta 一致)。

### S11 — 确定性 / 可重复
同 query 连跑 3 次 → 断 3 次 Results 的关键可观测值(models_used / delta / primary)一致(前端层佐证 offline 确定性)。

### S12 — 响应式(单列降级)
resize mobile 375×812 / tablet 768×1024 → 断 5 阶段仍可推进(StepperRail 可能折叠成单列,但 heading/按钮 role 仍可达)。**只断可达性不断布局**。

### S13 — 性能 / 稳定性
- 大结果渲染:一个产出较多 trace/provenance 的 query → 断切 tab / 滚动不超时不卡(呼应评估中 scroll 超时,确认是否网站性能问题)。
- 连续操作:快速连点推进按钮 → 断无重复提交 / 无 race 崩溃。
- `read_console_messages` / `preview_logs` 每 suite 后断无未预期 JS error / 后端 500。

## 2. 变异证伪(防假绿,每 suite 至少一处)
- S1:改一个 heading name 为不存在 → 必 FAIL(证真在等阶段到达)。
- S2:改一个 tab→h2 配对 → 必 FAIL。
- S3:把 abstain case 的 EmptyState 断言改成断「已给出预测」→ 必 FAIL(证真断了弃权)。
- S9:把「空输入按钮 disabled」断言改成 enabled → 必 FAIL。

## 3. 落位与运行
- 文件:`praxis_vc_react/e2e/{happy-path,result-tabs,smoke}.spec.ts`(D-B 已有)+ 新增 `abstain-cases.spec.ts`(S3)/`perturbation-matrix.spec.ts`(S4/S5)/`advanced-input.spec.ts`(S6)/`theme-history.spec.ts`(S7/S8)/`guards-injection.spec.ts`(S9)/`determinism.spec.ts`(S11)/`responsive.spec.ts`(S12)。
- 跑:`cd praxis_vc_react && npm run e2e`(全);`npm run e2e -- <spec>`(单)。**报数标口径**(passed/failed + 是否含 skip 的 S10)。
- **红线**:只碰 `praxis_vc_react/e2e/*` + 可能的 `playwright.config.ts`;**绝不碰 src/**(尤其 4 WIP css)、不碰后端/内核。每个 case 真值先 dump 再断,不照抄。
- **诚实**:任一断言实测红 → 停报告真实页面文本/API 响应,不弱化选择器凑绿;abstain/EmptyState 是**预期正确行为**不是 bug。

## 4. 与后端 pytest 的分工(不重叠)
前端 e2e **只验 UI 可达性 + 阶段流转 + 可观测值呈现 + 诚实标注在场**;**不验**内核数值正确性/abstain 判据/provenance gate 逻辑(那是 `praxis_virtualcell/tests` 912 passed 包口径的活)。两层互补,不重复造轮子。

## 5. 配套 /loop 提示词(逐 suite 自节奏落地)

把下面整段作为 `/loop` 的输入(不带 interval,让模型自节奏,每轮落一个 suite):

```
按测试计划 docs/superpowers/plans/2026-07-17-frontend-full-e2e-test-plan.md 逐 suite 落地前端 playwright e2e,每轮只做一个 suite,直到全部有绿 spec:

1. 读该测试计划 + praxis_vc_react/e2e/ 现有 spec,选下一个未实现的 suite(优先级 S3 abstain/EmptyState → S9 守卫+注入 → S4 扰动×物种矩阵 → S6 高级输入 → S7/S8 主题+历史 → S11 确定性 → S5 预设体系 → S12 响应式 → S13 性能;S1/S2 已由 D-B 的 smoke/happy-path/result-tabs 覆盖;S10 LLM 无 DEEPSEEK_API_KEY 则 test.skip 标注)。若所有 suite 都已实现且 npm run e2e 全绿 → 停 loop。

2. lsof -ti:8000 | xargs kill 2>/dev/null;真跑一次选中 suite 的 case(webServer 会先 build 再启 uvicorn,或复用),走到相应阶段/Results,用 get_page_text / read_page / API 响应 dump 断言真值 —— 禁照抄猜测,以实测为准。

3. 写该 suite 的 spec 到 praxis_vc_react/e2e/<name>.spec.ts:全用 getByRole/getByLabel/getByText + waitForResponse 选择器,零 CSS class / data-testid / 像素 / toHaveScreenshot 断言(抗前端 WIP CSS);断言用步骤 2 的实测真值;固定 1280×720(响应式 suite 除外)。

4. cd praxis_vc_react && lsof -ti:8000|xargs kill 2>/dev/null; npm run e2e -- <name>.spec.ts 跑绿(报数标口径 passed/failed)。做一处变异证伪:改坏一个断言必 FAIL,再改回确认绿(不留残留)。

5. 提交:git add 只显式列该 spec 文件(禁 git add -A/. ;绝不 stage praxis_vc_react/src/ 的 4 个 WIP css、不碰 .claude/.playwright-mcp/string.jpeg、不碰后端/内核/根 tests);commit trailer 恒 Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>;不 push、不切分支、不 amend 别的 commit。

红线:只碰 praxis_vc_react/e2e/*(+ 必要时 playwright.config.ts);abstain / EmptyState / clarify 是预期正确行为不是 bug,别当红处理;若真跑中发现真 UI bug(页面崩溃 / API 500 / 注入 payload 被当基因执行 / 诚实标注缺失如 llm_used 显示错),立即停 loop 报告真实页面文本+API 响应,绝不弱化断言凑绿。每轮结束报该 suite 的 passed 口径 + 变异是否见红。
```

**说明**:这是 self-paced loop(无固定 interval),每轮闭环一个 suite(选→真跑取真值→写 spec→跑绿+变异→提交)。全部绿后自停。它复用 D-B 已建的 playwright 环境,不引入新依赖,严守"只碰 e2e/、不碰 src/ 与内核"的红线。
