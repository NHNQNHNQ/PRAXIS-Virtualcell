# v1.0-uplift 现状

> 锁定:2026-05-23 · base:v0.9.4(9f797a1)→ HEAD ccaaac5 · 26 commits

## 1. 数字一览

| 指标 | 值 |
|---|---|
| skill 总数 | 152(13 brain) |
| simulate 路径 OK | **152 / 152**(`tests/skills/test_run_py_smoke.py` 全绿) |
| simulate ↔ SKILL.md outputs MATCH | **151 / 152**(唯 1 skip 是 hand-written `vina_gnina_dock`) |
| real() 实现状态 — DONE_real(hand-written) | 1(`dock/vina_gnina_dock`,317 行,跳过本次重写) |
| real() 实现状态 — GREEN placeholder | **141**(echo placeholder,待人工接真 CLI) |
| real() 实现状态 — N/A | **11**(`cryo` 全部 — host 无通用 cryo conda env) |
| pytest tests/skills/ | **931 passed / 2 skipped / 0 failed**(27s) |
| 远端 `.53` E2E | ✓ cellpose-segment 经 SkillExecTool 跑通(simulate + dry-real) |

### 按 brain × bucket

| brain | total | GREEN | N_A |
|---|---|---|---|
| _common | 1 | 1 | 0 |
| cell | 11 | 11 | 0 |
| crispr | 11 | 11 | 0 |
| cryo | 11 | 0 | 11 |
| dock | 13 | 13 | 0 |
| drug | 12 | 12 | 0 |
| enzyme | 11 | 11 | 0 |
| immuno | 11 | 11 | 0 |
| md | 8 | 8 | 0 |
| microbiome | 22 | 22 | 0 |
| omics | 13 | 13 | 0 |
| pharma | 11 | 11 | 0 |
| protein | 17 | 17 | 0 |
| **合计** | **152** | **141** | **11** |

## 2. commit 列表(v0.9.4 → HEAD,26 个)

**Phase 0(design + plan):**
- `9dd5f6a` docs(spec) 152 skill real-uplift 设计稿(§7 SkillExecTool 修正)
- `6f4df10` docs(plan) 152 skill real-uplift 实施计划
- `9261c5b` docs(spec) initial(brainstorm 产物)

**Phase A(6 个通用工具 + pytest 框架):**
- `2adbd6a` feat(uplift) run_tool subprocess helper + PRAXIS_SKILL_DRY_HOST mock
- `4d97331` feat(uplift) SKILL.md outputs 解析器(容忍 trailing-comma/comment)
- `ef268b7` feat(uplift) SKILL.md outputs 修复器(archetype defaults)
- `710e18a` feat(uplift) simulate() 重写器(>200 行 hand-written 保护)
- `e74dc4c` feat(uplift) fresh parity 分桶 + brain-default host_env fallback
- `c64029e` feat(uplift) real() 骨架生成器(GREEN echo / N_A 兜底)
- `b4fb49d` test(skills) conftest + smoke + schema-match parametrize

**Phase B(13 brain 闭环):**
- `611c632` feat(_common) 1 skill
- `d84e9ed` feat(md) 8 skills
- `1f3f3a9` fix(uplift) cleaner 补 `[...]/{...}/bare-ellipsis` placeholder
- `1059050` feat(dock) 13 skills
- `7080b72` feat(drug) 12 skills
- `e426b2f` fix(uplift) still-broken SKILL.md 用 archetype default 替换
- `663103d` feat(pharma) 11 skills
- `572e817` feat(crispr) 11 skills
- `c2969ff` feat(cell) 11 skills
- `1975a76` feat(enzyme) 11 skills
- `a19f808` feat(immuno) 11 skills
- `3937b5c` feat(cryo) 11 skills(全 N_A)
- `5a12fdf` feat(omics) 13 skills
- `70704ea` feat(protein) 17 skills
- `0a76e04` feat(microbiome) 22 skills

**Phase C(验收):**
- `ccaaac5` test(skills) 全量 schema-match 也跳过 hand-written

## 3. 本版已做的事(对比 v0.9.4)

- 引入 `brains/_common/lib/run_tool.py` — 本地 subprocess wrapper,run.py 内 real() 可一致调用;`PRAXIS_SKILL_DRY_HOST=1` 时返 mock(本地 pytest 不依赖 .53)
- 引入 `scripts/uplift/` 6 个生成器(`parse_skill_outputs / fix_skill_outputs / regen_simulate / regen_real / parity_per_brain / _skills`)
- 152 个 `SKILL.md` 的 `## 输出契约` 段全部规整,parser 容忍 trailing-comma / `// comment` / `[...]` / `{...}` / bare `...` placeholder
- 151 个 `run.py` 的 `simulate()` 重写,产出严格 match SKILL.md outputs 的合成数据;1 个 hand-written(`vina_gnina_dock`)保留不动
- 141 个 `run.py` 的 `real()` 替换为 GREEN echo placeholder(import `run_tool`,跑无害 echo,留 TODO 让人工后续接真 CLI)
- 11 个 cryo skill 的 `real()` 标 N/A,fallback 返合理 dummy(host 无通用 cryo env)
- 新增 `tests/skills/` 完整覆盖:6 + 4×3(单元) + 304(全量 smoke) + 152(schema-match) + 13×~33(per-brain) ≈ 931 项
- 同步 `brains/` 到 `.53:/home/zkyd/data1/mzy/praxis2-brains/`
- `.53` E2E 验证:`SkillExecTool` → ssh → conda activate PRAXIS-Cell → python run.py 跑通 simulate + real(dry-host)

## 4. 已知 TODO(下个 milestone)

按优先级:

| # | 任务 | 估时 | 备注 |
|---|---|---|---|
| 1 | **141 个 GREEN real() 把 echo placeholder 换成对应真实 CLI** | 70-140h | 每个 15-60 min;按 SKILL.md SOP 接对应工具(autodock-vina / cellpose / scanpy / cryosparc / …) |
| 2 | host 端为 11 个 cryo skill 装通用 env(cryosparc/relion4)或个别明确装 | 5-15h | 装不上的真就 N/A |
| 3 | production `/chat/stream` 真打一发 HTTP | 30 min | `VERSION-STATUS-v0.9.4.md §7 第 2 项` |
| 4 | `deploy/push_backend.sh` 加 `rsync brains/` | 5 min | `§7 第 3 项` |
| 5 | 给 `vina_gnina_dock` 的 hand-written simulate 补齐 SKILL.md outputs 缺的 7 个 keys | 30 min | 唯一的 schema-match skip,逻辑上应该补 |

P0(#1)全做完才是真正"全量 real"。本版做的是"所有 skill 都有 real() 函数能跑、骨架就位、N/A 已标明",还差最后一公里的 CLI 接入。

## 5. 验收命令

```bash
# 单元测试(无需 .53)
pytest tests/skills/ -q
# Expected: 931 passed, 2 skipped, 0 failed

# 真打 .53 一发(需环境变量 + ssh key)
export PRAXIS_SKILL_SSH_HOST=zkyd@10.102.106.53 \
       PRAXIS_SKILL_REMOTE_BRAINS=/home/zkyd/data1/mzy/praxis2-brains \
       PRAXIS_SKILL_CONDA_INIT=/home/zkyd/software/miniconda3/etc/profile.d/conda.sh
python3 -c "
import asyncio
from praxis2.tools.skill_exec import SkillExecTool
t = SkillExecTool()
r = asyncio.run(t.run({'name': 'cellpose-segment', 'brain': 'cell', 'inputs': {'simulate': True}}))
print(r.ok, sorted(r.value['result'].keys()))
"
# Expected: True, ['border_cells_filtered', 'diagnostics', 'iou_vs_manual', 'mask_path', 'n_cells',
#                  'overlay_png', 'passed_sanity', 'per_cell_features_csv']
```

## 6. 参考

- 设计稿:`docs/superpowers/specs/2026-05-22-skills-real-uplift-design.md`
- 实施 plan:`docs/superpowers/plans/2026-05-22-skills-real-uplift.md`
- fresh parity 数据:`_audit/parity_v1_per_brain.json`
- 上一版现状:`VERSION-STATUS-v0.9.4.md`
