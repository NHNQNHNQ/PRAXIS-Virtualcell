# PRAXIS-virtualcell Bootstrap 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `/Volumes/T7/clade-learn/PRAXIS-2@b124d66` 精简复制为新仓 `/Volumes/T7/PRAXIS-virtualcell`,跑通原测试、改项目身份、用一个最小 `virtualcell` brain 替换 13 个学科脑,推到 `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git`。

**Architecture:** 这是 **ops/bootstrap 计划,不是 TDD feature**。每步 = 一个操作 + 一条具体验证命令 + 期望输出 + 适时 commit。"测试"指 PRAXIS-2 自带的 pytest 套件(214 个文件)作绿基线 gate,以及去脑后重新求绿。python 包名保持 `praxis2`(只改 project name);保留 SaaS python 层不删。

**Tech Stack:** Python 3.11、rsync、venv+pip、pytest(asyncio_mode=auto)、git/ssh。`praxis2` 依赖轻(httpx/mcp/pydantic/pyyaml/python-multipart/python-magic),无 torch。

**Spec:** [docs/superpowers/specs/2026-06-11-praxis-virtualcell-bootstrap-design.md](../specs/2026-06-11-praxis-virtualcell-bootstrap-design.md)

---

## 文件结构(本计划会动的)

**新仓内新建:**
- `BASELINE.md` — 两次基线报告(复制后 / 去脑补脑后)
- `PROVENANCE.md` — import 源 + commit + 排除/删除项
- `brains/virtualcell/`(由 `brains/cell` 模板改写):`metadata.yaml`、`PRAXIS-Virtualcell-AGENT-PROMPT.md`、`prompts/PRAXIS-Virtualcell-AGENT-PROMPT.md`、`memory/cases/vcell-001-bootstrap.md`、`memory/rules/_default_bootstrap.md`、`skills/workflows/.gitkeep`
- `brains/INDEX.md` — 重写为只列 virtualcell + _common

**新仓内修改:**
- `README.md` — 改项目身份
- `pyproject.toml` — `name`/`description`(`packages.find include=["praxis2*"]` 不动)
- `praxis2/brains/migrate.py` — `DISCIPLINE_SLUGS` 与 `_DISCIPLINE_HINTS` 两处
- `tests/*.py` — 去脑后按规则改/skip(执行时按实际红集枚举)

**新仓内删除:**
- `brains/{cell,crispr,cryo,dock,drug,enzyme,immuno,md,microbiome,omics,pharma,protein,synth}`

---

## Task 1: Phase 0 — 精简复制

**Files:** 仅文件系统操作,无代码文件。

- [ ] **Step 1: 确认目标目录不存在(防误覆盖)**

Run:
```bash
ls -ld /Volumes/T7/PRAXIS-virtualcell 2>&1
```
Expected: `No such file or directory`。若已存在 → 停下问用户,不要覆盖。

- [ ] **Step 2: rsync 精简复制**

Run:
```bash
rsync -a \
  --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
  --exclude='*.pyc' --exclude='.pytest_cache' --exclude='.ruff_cache' \
  --exclude='*.egg-info' --exclude='._*' --exclude='.DS_Store' \
  --exclude='.gstack' --exclude='frontend' --exclude='备案' \
  "/Volumes/T7/clade-learn/PRAXIS-2/" \
  "/Volumes/T7/PRAXIS-virtualcell/"
```
Expected: 无报错返回。

- [ ] **Step 3: 验证关键目录完整 copy 过来**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && \
ls praxis2/brains/migrate.py pyproject.toml README.md && \
ls -d brains/cell brains/_common tests && \
du -sh . && \
echo "frontend 应不存在:" && ls frontend 2>&1
```
Expected: 文件都在;`du` ~250M;`frontend` 报 `No such file or directory`。

> 本 Task 不 commit(尚未 `git init`,Phase 2 才初始化)。

---

## Task 2: Phase 1 — 绿基线(确认原码能跑)

**Files:** Create `BASELINE.md`(第一次基线)。

- [ ] **Step 1: 预检 libmagic(python-magic 的系统依赖)**

Run:
```bash
ls /opt/homebrew/lib/libmagic* /usr/local/lib/libmagic* /usr/lib/libmagic* 2>/dev/null || echo "MISSING"
```
若 `MISSING`:`brew install libmagic`(没有 brew 则记进 BASELINE 已知问题,相关 import 测试可能红)。

- [ ] **Step 2: 建 venv 并安装(含 dev)**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && \
python3.11 -m venv .venv && \
.venv/bin/python -m pip install -U pip -q && \
.venv/bin/python -m pip install -e ".[dev]" -q && \
echo "INSTALL_OK"
```
Expected: 末尾 `INSTALL_OK`,无 ERROR。(`python3.11` 不存在则用 `python3`,但需 ≥3.11。)

- [ ] **Step 3: 跑全套测试(integration 应自动 skip)**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && \
.venv/bin/pytest tests -q 2>&1 | tail -30
```
Expected: 末行类似 `N passed, M skipped`。
若大量 `error`(非 skip)且来自 integration(缺 PG/Redis):改跑 `.venv/bin/pytest tests -q -m "not integration" 2>&1 | tail -30` 作为基线口径,并在 BASELINE 注明。
若有**真红**(非环境/非 integration):进 `superpowers:systematic-debugging`,不带病进 Task 3。

- [ ] **Step 4: 写 BASELINE.md(第一次基线)**

Create `/Volumes/T7/PRAXIS-virtualcell/BASELINE.md`:
```markdown
# PRAXIS-virtualcell Baseline

## 基线 1 — 复制后(原 PRAXIS-2 代码)
- 日期:2026-06-11
- 源:/Volumes/T7/clade-learn/PRAXIS-2 @ b124d66
- 安装:python <ver>,pip install -e ".[dev]"
- 测试命令:<实际命令>
- 结果:<N passed, M skipped, K failed>
- 已知失败/skip 及原因:
  - integration(需 docker PG/Redis):自动 skip — 预期
  - <其它逐条列出>
- 结论:<原码可跑 / 有阻塞需处理>

## 基线 2 — 去脑补脑后
(Task 6 填)
```
把 Step 3 真实数字填进 `<...>`。

> 本 Task 不 commit(Phase 2 统一首个 commit)。

---

## Task 3: Phase 2 — 项目身份 + git init + tag

**Files:** Modify `README.md`、`pyproject.toml`;Create `PROVENANCE.md`。

- [ ] **Step 1: 改 pyproject 项目名/描述(不动包名)**

读 `pyproject.toml`,把第 2、4 行改为:
```toml
name = "praxis-virtualcell"
version = "0.0.0"
description = "PRAXIS-2-derived multi-agent framework for virtual-cell prediction"
```
**保持** `[tool.setuptools.packages.find] include = ["praxis2*"]` 不变(import 仍是 `praxis2`)。

- [ ] **Step 2: 验证改名后仍可装/可 import**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && \
.venv/bin/python -m pip install -e . -q && \
.venv/bin/python -c "import praxis2; print('import praxis2 OK')"
```
Expected: `import praxis2 OK`。

- [ ] **Step 3: 重写 README.md 头部身份段**

把 `README.md` 顶部替换为(保留原文其余技术内容于其下,或精简):
```markdown
# PRAXIS-virtualcell

PRAXIS-virtualcell is a PRAXIS-2-derived multi-agent framework for virtual-cell prediction.
It reuses the PRAXIS-2 agent runtime, long-term brain, validation rules and skill system,
and extends them with a virtual-cell brain, predictor registry, virtual-cell subagents and
biological benchmarks.

> 基于 PRAXIS-2(commit b124d66)复制改造的多智能体虚拟细胞框架。继承 PRAXIS-2 的智能体运行时、
> 长期大脑、规则系统与工具执行能力,扩展虚拟细胞大脑、预测模型注册表、生物预测 Subagent 与虚拟细胞 benchmark。
> Built on PRAXIS-2. python 包名保持 `praxis2`。

---
```

- [ ] **Step 4: 写 PROVENANCE.md**

Create `/Volumes/T7/PRAXIS-virtualcell/PROVENANCE.md`:
```markdown
# Provenance

- Imported from: /Volumes/T7/clade-learn/PRAXIS-2 @ commit b124d66
- Import date: 2026-06-11
- Method: rsync(精简),fresh `git init`(不保留 PRAXIS-2 历史)
- Excluded on copy: .git .venv frontend/ 备案/ __pycache__ caches *.egg-info ._* .gstack
- python package name kept as `praxis2`(project name = praxis-virtualcell)
- Discipline brains removed(见 brains/INDEX.md);added minimal `virtualcell` brain
- Tag: praxis2-import-b124d66
```

- [ ] **Step 5: git init + 首个 commit + tag**

先确认复制过来的 `.gitignore`(来自 PRAXIS-2)含关键忽略项,**不要覆盖它**(它已忽略 `.venv` / `.env` / `*.egg-info` / `._*`;覆盖会有提交 `.env` 泄密风险)。

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && \
grep -q '^\.venv/' .gitignore && grep -q '^\.env$' .gitignore && echo "gitignore OK" || echo "WARN check .gitignore" && \
git init -q && git add -A && \
echo "--- .venv 应未被 add(计数 0)---" && git status --short | grep -c '\.venv/' && \
git commit -q -m "bootstrap: import PRAXIS-2 as PRAXIS-virtualcell base (from b124d66)" && \
git tag praxis2-import-b124d66 && \
git log --oneline -1 && git tag
```
Expected: `gitignore OK`;`.venv` 计数为 `0`;bootstrap commit + `praxis2-import-b124d66` tag 显示。
若 `WARN`:先把 `.venv/`、`.env`、`*.egg-info/` 补进 `.gitignore` 再 `git add -A`。

---

## Task 4: Phase 3a — 建最小 virtualcell brain

**Files:** Create `brains/virtualcell/*`(由 `brains/cell` 模板改写)。

- [ ] **Step 1: 复制 cell 结构作模板**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && \
cp -r brains/cell brains/virtualcell && \
find brains/virtualcell -type f | head -50
```
Expected: 列出 virtualcell 下文件(此刻还是 cell 的内容,下一步清洗)。

- [ ] **Step 2: 清洗 cell 残留内容,保留结构**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell/brains/virtualcell && \
rm -f memory/cases/cell-*.md && rm -rf memory/cases/_neg && \
rm -f memory/rules/0*.md && \
rm -rf skills/workflows/* && \
rm -f PRAXIS-Cell-AGENT-PROMPT.md prompts/PRAXIS-Cell-AGENT-PROMPT.md && \
touch skills/workflows/.gitkeep && \
ls -R . | head -40
```
Expected: 只剩 `metadata.yaml`、空 `memory/cases`、`memory/rules`(可能留 `_default_bootstrap.md`,下一步覆盖)、`skills/workflows/.gitkeep`、`prompts/`。

- [ ] **Step 3: 写 virtualcell metadata.yaml(对齐 cell 格式,无 slug 字段)**

覆盖 `brains/virtualcell/metadata.yaml`:
```yaml
# virtualcell brain — 虚拟细胞多物种多任务预测。
# helps_with=场景痛点 · delivers=交付物 · examples=试试这样问。
helps_with:
  - "想预测基因扰动/敲除后单细胞转录组怎么变(Norman/Replogle 类)"
  - "想比较多个 perturbation predictor 并要可靠性(abstain)判断"
  - "想把哺乳动物的方法迁到细菌/酵母,但担心跨物种误迁移"
delivers:
  - "Coordinator 编排的 perturbation 预测 + 不确定性 + abstain 决策"
  - "跨物种适用性/负迁移告警(species-aware,Week 5 起)"
  - "公开 benchmark 同表对比(Norman/Replogle/Sciplex/E.coli/yeast)"
examples:
  - "Norman 双基因扰动,Coordinator+abstain 给可靠预测"
  - "这个 predictor 能用在 E. coli 上吗?"
```

- [ ] **Step 4: 写 AGENT-PROMPT 种子(top-level + prompts/ 两份,对齐 cell)**

Create `brains/virtualcell/PRAXIS-Virtualcell-AGENT-PROMPT.md`:
```markdown
# PRAXIS-Virtualcell Agent

你是虚拟细胞预测智能体。职责:接收 (VirtualCellContext, Perturbation),查 species-aware 经验,
路由到合适的 VirtualCell Subagent,用 PredictorRegistry 里的预测模型 ensemble,
经 ReliabilityAgent 判断 accept / abstain,返回带 provenance 的 Prediction。

硬约束:公开 benchmark 必同表对比 ≥3 baseline;不编数据;simulated 产物自标;
跨物种迁移先查 negative-transfer 经验。(完整能力随 Week 2-8 填充)
```
然后 `cp` 一份到 prompts/:
```bash
cd /Volumes/T7/PRAXIS-virtualcell/brains/virtualcell && \
cp PRAXIS-Virtualcell-AGENT-PROMPT.md prompts/PRAXIS-Virtualcell-AGENT-PROMPT.md
```

- [ ] **Step 5: 写一条种子 rule 和一条种子 case(满足"非空 brain"不变式)**

Create `brains/virtualcell/memory/rules/_default_bootstrap.md`:
```markdown
# rule: virtualcell bootstrap default
- 任何论文级 claim 至少在 1 个公开 benchmark 上 ≥3 baseline 同表对比。
- 跨物种迁移前必须查 negative-transfer 经验,缺则默认保守(倾向 abstain)。
- 预测/仿真产物标 `simulated`,不与实验数据混。
```
Create `brains/virtualcell/memory/cases/vcell-001-bootstrap.md`:
```markdown
# case vcell-001: bootstrap 占位
- 背景:PRAXIS-virtualcell 从 PRAXIS-2 复制改造,virtualcell brain 初始化。
- 经验:species 分库与真实 perturbation cases 自 Week 3/Week 5 起填充。
- 关联:[[Coordinator+abstain 统一路径]]、donor 项目 Virtual-cell 的 finding_015。
```

- [ ] **Step 6: 验证 brain 结构完整**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && find brains/virtualcell -type f | sort
```
Expected: 含 metadata.yaml、两份 AGENT-PROMPT、1 rule、1 case、skills/workflows/.gitkeep。

---

## Task 5: Phase 3b — 改 registry + 删 13 学科脑 + 重写 INDEX

**Files:** Modify `praxis2/brains/migrate.py`;Delete 13 个 `brains/<slug>`;Rewrite `brains/INDEX.md`。

- [ ] **Step 1: 改 DISCIPLINE_SLUGS(migrate.py:18-21)**

读 `praxis2/brains/migrate.py`,把:
```python
DISCIPLINE_SLUGS: list[str] = [
    "cell", "crispr", "cryo", "dock", "drug", "enzyme",
    "immuno", "md", "microbiome", "omics", "pharma", "protein", "synth",
]
```
改为:
```python
DISCIPLINE_SLUGS: list[str] = [
    "virtualcell",
]
```

- [ ] **Step 2: 改 _DISCIPLINE_HINTS(同文件,key 必须对齐 SLUGS)**

读同文件 `_DISCIPLINE_HINTS`(约 28-42 行,13 个 `"slug": "关键词"` 条目),把整个 dict 体替换为单条:
```python
    "virtualcell": "虚拟细胞 扰动 敲除 转录组 生长 必需基因 跨物种 abstain 预测",
```
(保留 dict 的变量名与 `{` `}` 包裹,仅替换条目。)

- [ ] **Step 3: 删 13 个学科脑(保留 _common 与 virtualcell)**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell/brains && \
rm -rf cell crispr cryo dock drug enzyme immuno md microbiome omics pharma protein synth && \
ls
```
Expected: 只剩 `_common`、`virtualcell`、`INDEX.md`。

- [ ] **Step 4: 重写 brains/INDEX.md**

覆盖 `brains/INDEX.md`:
```markdown
# PRAXIS-virtualcell — Agent Brains 索引

> 案例学习大脑:cases / rules / skills / prompts / memory。
> 从 PRAXIS-2(b124d66)复制改造:**已移除 13 个通用学科大脑**,改为单一虚拟细胞大脑。
> 物种分库(human/mouse/E.coli/yeast 等)自 Week 5 起填入 `virtualcell` brain。

| brain | 说明 |
|---|---|
| virtualcell | 虚拟细胞多物种多任务预测(perturbation / drug / growth / essentiality) |
| _common | 跨学科共享规则/技能(基础设施,保留) |
```

- [ ] **Step 5: 静态验证无残留硬引用导致 import 失败**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && \
.venv/bin/python -c "from praxis2.brains.migrate import DISCIPLINE_SLUGS, _DISCIPLINE_HINTS; print(DISCIPLINE_SLUGS); assert DISCIPLINE_SLUGS==['virtualcell']; assert set(_DISCIPLINE_HINTS)==set(DISCIPLINE_SLUGS), _DISCIPLINE_HINTS; print('SLUGS+HINTS OK')"
```
Expected: `['virtualcell']` 和 `SLUGS+HINTS OK`。失败说明 hints/ slugs 不一致 → 回 Step 2 修。

---

## Task 6: Phase 3c — 去脑后重新求绿 + 第二次基线 + commit

**Files:** Modify 若干 `tests/*.py`(按实际红集);Modify `BASELINE.md`。

- [ ] **Step 1: 跑测试,捕获红集**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && \
.venv/bin/pytest tests -q -m "not integration" 2>&1 | tail -40
```
记录所有 FAILED/ERROR 的用例路径。预期受影响(prior 侦察):
`test_correctness_slug_canonical`、`test_brains_profile`、`test_brains_store_migrate`、`test_migrate_brains`、`test_agents_loader`、`test_agents_agent_tool*`、`test_server_chat_registry`、`test_server_app_agent_mode`、`test_m5_invariants`、`test_m8_invariants`、`test_review_promote_hotreload`、`test_brains_system_prompt_wiring`、`test_tools_brain_query`、`test_tools_skill_exec`、`tests/skills/test_cell.py`。

- [ ] **Step 2: 按规则逐个处理红用例**

对每个红用例套用决策规则(改而非删优先):
- **(a) 断言 slug 集合/数量** 的:把期望从 13-list/`count==13`/`"cell"...` 改为 `["virtualcell"]` / `==1` / `"virtualcell"`。
- **(b) 用某学科作"通用 brain 行为"示例**(如拿 `"cell"` 测 brain_query/loader/skill_exec 通路)的:把示例 slug 换成 `"virtualcell"`,断言相应改写。
- **(c) 内在测某个已删学科的专属内容**(如 `tests/skills/test_cell.py` 测 cell 专属 workflow)的:`git rm` 删该测试文件,或 `@pytest.mark.skip(reason="discipline brain 'cell' removed by design; virtualcell brain seeded, species subdirs pending Week 5")`。删/skip 必须逐条记进 BASELINE。

每改一个文件就重跑该文件确认:`.venv/bin/pytest <file> -q`。

- [ ] **Step 3: 全套重新求绿**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && \
.venv/bin/pytest tests -q -m "not integration" 2>&1 | tail -20
```
Expected: `N passed, M skipped`(0 failed)。仍红且非"已删学科专属" → 进 `superpowers:systematic-debugging`。

- [ ] **Step 4: 验证运行时 brain 模块 import 干净 + slugs 一致**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && \
.venv/bin/python -c "import praxis2.brains.profile, praxis2.brains.migrate, praxis2.agents.loader; from praxis2.brains.migrate import DISCIPLINE_SLUGS; assert DISCIPLINE_SLUGS==['virtualcell']; print('runtime brain modules import + slugs OK')"
```
Expected: `runtime brain modules import + slugs OK`(import 这几个模块会触发其对 `brains/` 的读取逻辑;Step 3 的 profile/loader/brain_query 测试是更强的运行时验证)。

- [ ] **Step 5: 补写 BASELINE.md 第二次基线**

把 `BASELINE.md` 的「## 基线 2」段填上:日期、测试命令、结果数字、**所有 skip/删除的测试逐条 + 原因**、结论(去脑补脑后绿)。

- [ ] **Step 6: commit**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && \
git add -A && \
git commit -q -m "chore: replace 13 discipline brains with minimal virtualcell brain (DISCIPLINE_SLUGS={virtualcell})" && \
git log --oneline -3
```
Expected: 显示去脑补脑 commit 在最上。

---

## Task 7: Phase 4 — 推到新远端

**Files:** 无代码文件,git 远端操作。

- [ ] **Step 1: 加 remote + 重命名分支 + push**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && \
git remote add origin git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git && \
git branch -M main && \
git push -u origin main --tags
```
Expected: push 成功(空仓,fast-forward),tag 一并上传。

- [ ] **Step 2: 验证远端可见**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && git ls-remote origin
```
Expected: 看到 `refs/heads/main` 和 `refs/tags/praxis2-import-b124d66`。

- [ ] **Step 3: 终检 — donor 项目未被污染**

Run:
```bash
cd /Volumes/T7/Virtual-cell && git status --short
```
Expected: 只可能有 `docs/superpowers/` 下本 spec/plan 文档(若未提交),无其它改动。

---

## 验收(Definition of Done)
1. `/Volumes/T7/PRAXIS-virtualcell` 存在,`pytest tests -q -m "not integration"` 绿(去脑补脑后)。
2. `brains/` 下 13 学科目录已删;`_common` + `virtualcell` 在;`DISCIPLINE_SLUGS==["virtualcell"]` 且 `_DISCIPLINE_HINTS` key 对齐。
3. README/pyproject 身份已改(包名仍 `praxis2`);`PROVENANCE.md` 记录源 commit;`BASELINE.md` 两次基线齐全。
4. git 有 2 个 commit + `praxis2-import-b124d66` tag;已 push 到 `PRAXIS-Virtualcell` 远端 main。
5. donor 项目 `/Volumes/T7/Virtual-cell` 未被污染(除规划文档)。
