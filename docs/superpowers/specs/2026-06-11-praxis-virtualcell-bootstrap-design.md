# PRAXIS-virtualcell Bootstrap(Week 1)设计 spec

- 日期:2026-06-11
- 作者:zhenyu ma + Claude
- 状态:待用户复核
- 上游计划:用户提供的《PRAXIS-virtualcell:基于 PRAXIS-2 复制改造的新项目计划》Week 1
- 源项目:`/Volumes/T7/clade-learn/PRAXIS-2` @ commit `b124d66`
- 目标新仓:`/Volumes/T7/PRAXIS-virtualcell` → 远端 `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git`

---

## 1. 目标与范围

**只做 Week 1 bootstrap。** Week 2-8(迁移 ML 核心 / Coordinator+abstain 统一 / species brain / predictor registry / 外部模型 / 细菌酵母 case / 论文图)各自再走独立 spec→plan→execute 循环。

本 spec 交付:一个**能跑、已 tag、已改项目身份、已去学科大脑、已推到新远端**的新仓 `/Volumes/T7/PRAXIS-virtualcell`,外加 baseline 报告。

**明确不做(本期):**
- 不动当前 `/Volumes/T7/Virtual-cell`(它是后续 ML 迁移的 donor,保持原样)。
- 不迁移任何 predictor / coordinator / abstain 代码(那是 Week 3+)。
- 不重命名 python 包 `praxis2`(改名会炸全部 import,上游计划 §3.1 也主张先保留)。
- 不删 SaaS python 层(auth/server/accounting/admin/scheduler/migrations)——本期保留以不破坏绿基线,后续 week 按需裁。
- 不建 species 物种分库(human/mouse/ecoli/yeast,Week 5);但**补建一个最小 `virtualcell` brain 骨架**(见 Phase 3),让 agent-OS 有真脑可载。

## 2. 关键事实(勘探所得,直接影响设计)

1. **`praxis2` 包依赖很轻**:httpx / mcp / pydantic / pydantic-settings / python-multipart / python-magic / PyYAML,**无 torch**。`pip install -e ".[dev]"` 便宜快速。
2. **frontend 800M 几乎全是 node_modules**(792M,已被 `.gitignore`);源码仅 ~6M。整个 `frontend/` 本期不 copy(web UI,与虚拟细胞研究无关)。
3. **运行时与顶层 `brains/` 强耦合**:`praxis2/brains/{migrate,retrieve,store,inject,...}`、`praxis2/agents/loader.py`、`praxis2/server/app.py`、`praxis2/tools/{brain_query,skill_exec,file_read,rmcp_write}.py`、`praxis2/memory/review.py` 都按一份 `DISCIPLINE_SLUGS`(13 学科,含 synth)读 `brains/<slug>/`。
   - **推论**:"去掉学科大脑" ≠ 单纯 `rm -rf brains/*`。必须同时把 `DISCIPLINE_SLUGS` 改为只含新建的 `virtualcell` brain + 修/skip 断言原 13 学科脑存在的测试,否则 baseline 测试会红。
4. **`brains/_common` 是共享基础设施**(非学科,含 skills/lib/memory),**保留**。13 个待删学科目录:`cell crispr cryo dock drug enzyme immuno md microbiome omics pharma protein synth`。
5. **`gh` CLI 未登录**;用户给的是 SSH URL。GitHub 不会在 push 时自动建仓 → push 前远端仓必须已存在(见 Phase 4 前置条件)。

## 3. 方案:4 个 phase,每个带验证 gate

### Phase 0 — 忠实精简复制
`rsync -a` 把 `/Volumes/T7/clade-learn/PRAXIS-2/` → `/Volumes/T7/PRAXIS-virtualcell/`,排除:
```
.git/  .venv/  __pycache__/  *.pyc  .pytest_cache/  .ruff_cache/
*.egg-info/  ._*  .DS_Store  .gstack/  frontend/  备案/
```
**本 phase 先保留学科大脑**(`brains/` 全留),先求绿基线再动它。预计结果 ~250M(主要是 brains 167M + tests + praxis2)。
**Gate**:目录存在、`praxis2/` 与 `tests/` 完整 copy 过来。

### Phase 1 — 绿基线(确认原码能跑)
1. 在新仓建 venv:`python3.11 -m venv .venv && source .venv/bin/activate`
2. `pip install -e ".[dev]"`
3. `pytest tests -q`(`integration` marker 需 docker PG/Redis,无则自动 skip)
4. 写 `BASELINE.md`:日期 / 源 commit `b124d66` / pytest 汇总(passed/failed/skipped)/ known failures 及原因。
**Gate**:单元测试绿,或所有失败都已逐条解释(区分"环境缺失自动 skip" vs "真红")。真红且非环境问题 → 进 systematic-debugging,不带病进 Phase 2。

### Phase 2 — 项目身份(不改包名)
1. 改 `README.md`:PRAXIS-virtualcell 定位(中英),说明 "PRAXIS-2-derived multi-agent framework for virtual-cell prediction",标注 built-on PRAXIS-2@b124d66。
2. 改 `pyproject.toml`:`name = "praxis-virtualcell"`、更新 `description`。**`[tool.setuptools.packages.find] include = ["praxis2*"]` 不动,python 包仍叫 `praxis2`。**
3. 加 `PROVENANCE.md`:记录 import 源(路径 + commit b124d66 + 日期)、已排除项、已删项(Phase 3 后补)。
4. `git init`;`git add -A`;首个 commit `bootstrap: import PRAXIS-2 as PRAXIS-virtualcell base`;打 tag `praxis2-import-b124d66`。
**Gate**:`git log` 有 bootstrap commit + tag;`pip install -e .` 仍可装(包名改了不影响 import)。

### Phase 3 — 去学科大脑 + 补 virtualcell 最小脑 + 重新求绿
1. **补建最小 virtualcell brain**:以 `brains/cell/`(删前)为结构模板 `cp -r brains/cell brains/virtualcell`,再清空其学科内容,重写为虚拟细胞:
   - `brains/virtualcell/metadata.yaml`:`slug: virtualcell`、name/description 面向虚拟细胞多物种多任务预测。
   - `brains/virtualcell/PRAXIS-Virtualcell-AGENT-PROMPT.md`:virtual-cell agent 种子 prompt。
   - 标准子目录 `memory/cases/`、`memory/rules/`、`skills/`、`prompts/`(先放 `.gitkeep` 或一两条占位 rule,内容 Week 5 再填)。
2. 定位 `DISCIPLINE_SLUGS`(`praxis2/brains/migrate.py` 或 `agents/loader.py`,执行时 grep 确认单一真源),**置为 `["virtualcell"]`**(替换原 13 学科)。
3. 删 `brains/{cell,crispr,cryo,dock,drug,enzyme,immuno,md,microbiome,omics,pharma,protein,synth}`;**保留 `brains/_common`** 与新建的 `brains/virtualcell`;重建 `brains/INDEX.md`(只列 virtualcell + _common)。
4. 跑测试,定位因"学科脑消失"而红的用例:断言学科 slug 列表的 → 改成断言 `{virtualcell}`;纯学科 fixture 测试 → `skip`(reason="discipline brains removed; virtualcell brain seeded, species subdirs pending Week 5")。
5. 重跑 `pytest tests -q` → 新绿基线,追加进 `BASELINE.md`(第二次基线:去脑+补脑后)。
6. commit `chore: replace discipline brains with minimal virtualcell brain (DISCIPLINE_SLUGS={virtualcell})`。
**Gate**:pytest 仍绿(或失败都已解释);运行时能 load `virtualcell` brain;`brains/virtualcell/` 结构被 brain loader 接受;`grep -rn "brains/cell\|brains/synth" praxis2` 无导致运行时错误的残留硬引用。

### Phase 4 — 推到新远端
**前置条件(已满足 2026-06-11)**:远端 `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git` 已由用户建好;`git ls-remote` 验证 SSH 通、**空仓无 refs**(push 不会 non-fast-forward)。
```
git remote add origin git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git
git branch -M main
git push -u origin main --tags
```
**Gate**:`git ls-remote origin` 能看到 `main` + `praxis2-import-b124d66` tag;远端可见。

## 4. 交付物
- `/Volumes/T7/PRAXIS-virtualcell/`:新 git 仓,含 bootstrap commit + `praxis2-import-b124d66` tag + 去脑补脑 commit。
- `BASELINE.md`:两次基线(复制后 / 去脑补脑后)。
- `brains/virtualcell/`:最小虚拟细胞 brain 骨架(metadata + AGENT-PROMPT + 标准子目录);`DISCIPLINE_SLUGS=["virtualcell"]`。
- `README.md`(改名)+ `pyproject.toml`(name=praxis-virtualcell)+ `PROVENANCE.md`。
- 远端 `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git` 已 push。
- 当前 `/Volumes/T7/Virtual-cell` 零改动(除本 spec 文档)。

## 5. 风险与处置
| 风险 | 处置 |
|---|---|
| 去脑炸测试 | 先绿基线(Phase 1)再去脑(Phase 3);去脑后红测试逐条改/skip;必要时 systematic-debugging。 |
| `pip install` 网络/依赖问题 | 依赖轻、无 torch,风险小;真卡了单独排查。 |
| 误删 `_common` 等非学科基础设施 | Phase 3 只删 13 个明确学科目录,`_common` 白名单保留。 |
| virtualcell brain 结构不合 loader 规范 | 以 `brains/cell` 为模板 `cp` 后改写,字段齐全;Phase 3 gate 验证可载入。 |
| 远端覆盖 | 全新独立仓 `PRAXIS-Virtualcell`,与 `Virtual-cell.git` 无关,不存在覆盖。 |
| gh 未登录无法建仓 | Phase 4 降级为"用户建空仓 + SSH push"。 |

## 6. 验收(Definition of Done)
1. `/Volumes/T7/PRAXIS-virtualcell` 存在,`pytest tests -q` 绿(去脑后)。
2. `brains/` 下 13 学科目录已删;`_common` 在;新增 `brains/virtualcell/` 结构完整且可被运行时载入;`DISCIPLINE_SLUGS=["virtualcell"]`。
3. README/pyproject 身份已改;PROVENANCE 记录源 commit。
4. git 有两个 commit + import tag;已 push 到新远端。
5. 当前 Virtual-cell 仓未被污染。

## 7. 后续(不属本期,仅占位)
Week 2 新增 `praxis_virtualcell/` 应用层 → Week 3 迁 mammalian predictor pool + ExperienceQuery + EvalAgent → Week 4 Coordinator+abstain 统一(`run_abstain_virtualcell.py --predictor coordinator`,复现 Norman~0.70/Replogle~0.57/Sciplex~0.48)→ Week 5 往 virtualcell brain 填 species 物种分库 → Week 6 predictor registry → Week 7 外部模型 → Week 8 细菌/酵母 case + 论文图。
