# 152 skill 全量 real() 升级 + simulate schema 修复 — Design

> 起草:2026-05-22 · 作者:Claude (Opus 4.7) · 状态:Draft for user review
> 关联文档:`docs/SKILL-SIMULATE-TO-REAL-GUIDE.md`、`_audit/parity_matrix.tsv`、`VERSION-STATUS-v0.9.4.md` §7

## 1. 背景与触发

v0.9.4 锁定时,152 个 `brains/*/skills/workflows/*/run.py` 中只有 1 个(`dock/vina_gnina_dock`)是真实现,其余 151 个是 89 行同质 simulate 模板。

本次工作开局 smoke 测试发现两个独立事实:

1. **simulate 路径 152/152 全绿**(stdin JSON → stdout JSON,exit 0,无 traceback)
2. **simulate 输出 vs `SKILL.md` 输出契约只有 1/152 MATCH** — 模板吐的是 archetype 通用 schema(`cluster_sizes / marker_genes_per_cluster` 之类),不是各 skill 实际声明的 schema(`mask_3d_tif / ec50 / hits_csv` …)。具体分布:1 MATCH / 14 DRIFT / 19 SKILL.md json 解析失败 / 118 SKILL.md 无规整 outputs 段。

由此,仅升级 real() 不够 — 即使 real 成功,simulate fallback 路径产出的数据格式与 real 不一致,下游智能体 prompt / SkillExecTool 消费会混乱。**两件事必须配套做完**。

## 2. 目标(本对话内全量完成)

- 152 个 skill 全部满足:
  - `SKILL.md` 有规整的"## 输出契约" json 段,可机器解析
  - `simulate(payload)` 产出的合成数据 top-level keys 与契约一致(MATCH)
  - `real(payload)` 实现并在 `.53` 验证可跑;无法实现的明确标 `N/A` 保留 simulate(在 SKILL.md 写明原因)
  - 至少 1 个 pytest 覆盖该 skill 的 simulate 路径;real 桶额外加 1 个标 `@pytest.mark.host` 的 E2E
- 单 commit per brain(逐 brain 闭环 commit,你可随时打断撤回)

## 3. 非目标

- 不在 .53 上装新 license 的商业软件
- 不重写 SKILL.md 的语义内容(只补/规整 outputs json 段)
- 不动 backend / frontend / chat 框架代码
- 不优化 simulate 的科学逼真度(只对齐 schema + 给合理 dummy 数据)

## 4. 范围分桶

按 brain 分 13 批,每批独立闭环:

| brain | skills | host conda env | 预计 real 桶 (★) |
|---|---|---|---|
| _common | 1 | base | 1 (nature_plot 已 green) |
| cell | 11 | PRAXIS-Cell | ~5 |
| crispr | 11 | PRAXIS-CRISPR* (3 env) | ~5 |
| cryo | 11 | (relion/cryolo/cryosparc 未必齐) | ~3 (大坑) |
| dock | 13 | praxis-dock + af2 + boltz/chai | ~10 (1 已 DONE_real) |
| drug | 12 | praxis-drug* (4 env) | ~10 |
| enzyme | 11 | PRAXIS-Enzyme | ~7 |
| immuno | 11 | praxis-immuno + arcas-hla + antibody | ~7 |
| md | 8 | (openmm/gromacs/amber via base?) | ~5 |
| microbiome | 22 | praxis-microbiome* (7 env) | ~15 |
| omics | 13 | praxis-omics | ~8 |
| pharma | 11 | praxis-pharma | ~8 |
| protein | 17 | af2 + esmfold + boltz + chai + rfdiffusion + proteinmpnn + thermompnn | ~12 |
| **合计** | **152** | 44 conda env / 4× A100 | **~96 real + ~56 N/A** (估) |

★ "预计 real 桶"是基于 host inventory 已知 env 的乐观估计,实际按每 brain fresh parity 重定。

## 5. 单 brain 闭环流程

每个 brain 走相同 5 步,完成后即 commit:

```
brain 进入 →
  Step 1: fresh parity 分类
    - 对该 brain 所有 skill,解析 SKILL.md 的 host_env / dependencies
    - 对照 _audit/host_inventory.json + 今天抓的 /tmp/host_raw_fresh.txt
    - 输出 3 桶:GREEN(host 工具齐) / RED-EASY(缺工具但可装) / N/A(license/data 受限)
  Step 2: SKILL.md outputs 规整
    - 修 19 个 json 解析失败的(trailing comma / 注释)
    - 给 118 个无 outputs 段的补一个简洁的 "## 输出契约" json
    - 风格参考 dock/vina_gnina_dock/SKILL.md
  Step 3: simulate() 重写
    - 用 SKILL.md 声明的 outputs json 当 schema,产 dummy 数据
    - 保留 archetype 的合成数据生成逻辑作为 helper,但顶层 keys 必须 SKILL 一致
    - diagnostics.simulated = True 保留
  Step 4: real() 实现 或 N/A
    - GREEN 桶:按 SKILL-SIMULATE-TO-REAL-GUIDE 范式,subprocess + parse + JSON
    - RED-EASY 桶:同上,先约定 host 端工具路径(用 conda env activate)
    - N/A 桶:real() 直接返 {"ok": false, "error": "N/A — <原因>", "fallback": "use simulate=true"}
    - 真 host 调用用 SSH 走 .53(SkillExecTool 模式),不假设本地有工具
  Step 5: pytest
    - tests/skills/test_<brain>.py 用 parametrize 跑该 brain 所有 skill 的 simulate
    - 标 @pytest.mark.host 的 real E2E:抽 1-3 个 GREEN skill 在 .53 真跑一遍
  → git add brains/<brain>/ tests/skills/test_<brain>.py
  → git commit -m "feat(<brain>): N skills real-uplift + simulate schema fix"
```

## 6. 工作分发策略

13 个 brain **互不依赖、目录隔离、SKILL.md schema 独立**,可在一个对话内 sequential 推进,也可 dispatching-parallel-agents 分批并行(每批 3-4 个 brain)。

**默认串行(因为 commit 顺序清晰、单一线程审核)**;若中途 token 紧张,切并行子代理。决策由实施时按当时进度判断。

## 7. host 调用约定(修正:SkillExecTool 已处理 SSH)

**架构现实**:`praxis2/tools/skill_exec.py` 的 `SkillExecTool._exec_via_ssh` 已经做了 `ssh .53 → source conda → conda activate <host_env from frontmatter> → cd remote_brains → python run.py < stdin JSON`。所以 **run.py 内部 `real()` 就在 .53 conda env 里作为本地 Python 进程跑,subprocess 直接调工具二进制即可**,不需要再封一层 SSH。

引入一个轻量 **本地** subprocess helper(不是 SSH wrapper):

```python
# brains/_common/lib/run_tool.py(新增)
def run_tool(
    cmd: list[str], *, timeout: int = 600, cwd: str | None = None, env: dict | None = None,
    stdin: bytes | None = None,
) -> dict:
    """subprocess.run 包装:超时/非 0 退出/异常都返结构化 dict,不抛。
    返回 {"ok": bool, "stdout": str, "stderr": str, "returncode": int, "wall_sec": float, "cmd": str, "error"?: str}
    """
```

每个 real() 用:`r = run_tool(["vina", "--receptor", rec, ...])` — 5-30 行清晰 real()。SSH 调度归 SkillExecTool 单点管。

**本地测试模式**:`PRAXIS_SKILL_DRY_HOST=1` 时,`run_tool` 不真跑而是返 mock 成功 dict。让本地 pytest 不依赖 .53 也能验证 real() 路径不崩。

## 8. 验收

- `git log --oneline` 应有 13 个 brain feat commit + 1 个 design + 1 个 helper(`host_exec.py`)
- `pytest tests/skills/ -q`:152 个 simulate 全绿
- `pytest tests/skills/ -q -m host`:跑得通的 real E2E 全绿(数量取决于 GREEN 桶实际大小)
- `python3 /tmp/schema_diff.py` 重跑:152/152 MATCH 或 NO_DECLARED 全消
- `VERSION-STATUS-v1.0.md` 文档:汇总 real / N/A 统计、commit 列表、SHA

## 9. 风险

- **token / 对话长度**:152 skill × 平均 10 个工具调用 = 千级 tool call。中途如果 context 压缩失序,需 checkpoint 文件(每 brain commit 后写 `/tmp/uplift_progress.json`)
- **host 工具实际不齐**:fresh inventory 可能与现实差(env 损坏 / data 路径动了)— Step 1 出 N/A 多了就如实标
- **SKILL.md outputs 现状混乱**:118 个无 outputs 段,需要"凭 archetype + skill 名推合理 outputs"。这一步主观,接受我先填一版你后续微调
- **SSH 抖动**:host_run 加 1 次重试 + 明确超时,不静默卡死

## 10. 不在本对话范围

- production /chat/stream 真打 HTTP(VERSION-STATUS §7 第 2 项)
- `deploy/push_backend.sh` 补 `rsync brains/`(§7 第 3 项)
- 性能优化、并发 host_run 池、GPU 调度
