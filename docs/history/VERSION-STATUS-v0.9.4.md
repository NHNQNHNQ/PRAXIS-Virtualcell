# PRAXIS-2 v0.9.4 · 版本现状

> **tag**: `v0.9.4` (commit `49aa0af`)
> **日期**: 2026-05-22
> **tarball**: `/tmp/praxis2-v0.9.4.tar.gz` (1.5 MB,git archive 干净打包)
> **里程碑代号**: skill-loop-real(智能体 → 真分析 闭环达成)

---

## 0. 一句话定位

智能体闭环 **首次真打通**:用户提问 → 模型在 system prompt 引导下选 skill 并发起 `SkillExec` 调用 → 通过 SSH 到 staging `.53` → conda 激活对应 env → 跑 `run.py` → JSON 回喂模型 → 模型用结构化结果生成专业级回答。

**真分析覆盖率**:1 / 52 全绿 skill 已经走 真 CLI(`vina_gnina_dock` → 真 gnina v1.3.2 cuda12.8);其余 51 个走 simulate 路径(合成数据,通路真,内容假)。

---

## 1. 闭环 7 步全绿(用 `vina_gnina_dock` 真 gnina 完整 demo 验证)

| # | 阶段 | 落点 | 实证 |
|---|---|---|---|
| 1 | 用户提问 → agent 路由 | `praxis2/agents/loader.py:resolve_agent` | `brain_slugs=["_common","dock"]` |
| 2 | 加载大脑 + retrieve_brain | `praxis2/brains/system_prompt.py:build_chat_system_prompt` | 32 KB system block + cache_control:ephemeral |
| 3 | host_env 过滤主路径 skill | 同上,读 `_audit/host_inventory.json` | cryo 自动剔除;52 个 green 入候选 |
| 4 | progressive_disclosure + query 相关度排序 | `praxis2/skills/loader.py` + `_score_skill` | "vina/gnina docking" query → vina_gnina_dock 排第 1 |
| 5 | 模型识别 + 发起 tool_use | `praxis2/tools/skill_exec.py:SkillExecTool` | DeepSeek API 真返 `SkillExec(name="vina_gnina_dock", inputs={...})` |
| 6 | 真 SSH 执行 | `SkillExecTool._exec_via_ssh` | ssh zkyd@.53 → conda activate praxis-dock → python run.py |
| 7 | tool_result 回喂 + 模型转述 | runtools.to_api_tool_result | 模型 601 token 综合报告 + cross-method divergence + Met318 hinge 引用 |

---

## 2. 真分析 demo(Imatinib × 1IEP / ABL kinase)

输入(用户给的):
```
受体: /tmp/praxis-test/dock/1iep.pdb
配体: Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc1nccc(-c2cccnc2)n1  (Imatinib)
num_modes=5, exhaustiveness=4, seed=42
```

run.py 真做的事:
- RDKit `EmbedMolecule` + `MMFFOptimizeMolecule` → 3D conformer SDF
- 自动 box:从 1iep.pdb 抽最大 HETATM 残基 = STI(Imatinib 晶体配体)→ obabel 转 SDF → `gnina --autobox_ligand`
- gnina v1.3.2 cuda12.8 跑 26.86 秒
- 解析 `docked.sdf.gz` 5 个 SDF 块,提取 `minimizedAffinity` / `CNNscore` / `CNNaffinity` / `CNN_VS`
- 按 CNNaffinity 排序

模型最终回的(摘要):

| Rank | Vina (kcal/mol) | GNINA CNN Score | GNINA CNN Affinity |
|---|---|---|---|
| **1** | **-7.69** | 0.453 | **6.82** |
| 2 | -5.30 | **0.587** ⭐ | 6.45 |
| 3 | -4.71 | 0.218 | 5.90 |
| 4 | -4.44 | 0.374 | 5.67 |
| 5 | -4.62 | 0.293 | 5.47 |

模型自己识别出的 insight(非脚本预设):
- Vina top-1 与 GNINA top-1 不一致 → **cross-method divergence**,建议 PoseBusters 复核
- 引用 1IEP 已知结合模式:Met318 hinge H-bond + 疏水口袋
- 推荐下一步 skill 链:`pose_buster_validate` → `redock_self_test` → 若 RMSD > 4Å fallback 到 `induced_fit_docking`

---

## 3. 数字总账(全旅程对照)

| 指标 | M9 起点 (v0.9) | v0.9.3 中段 | **v0.9.4 (本版)** |
|---|---|---|---|
| 测试通过 | 502 / 17s / 0F | 624 / 17s | **635 / 17s / 0F** |
| Staging conda envs | 43 | 43 | **44**(+praxis-pharma) |
| SKILL.md 数 | 132 | 145 | **152**(+13 stub) |
| 有 run.py 的 skill | 0 | 0 | **152** |
| 真 CLI 实现的 skill | 0 | 0 | **1**(vina_gnina_dock) |
| 主路径全绿 skill | 26 / 94 | 41 / 88 | **52 / 93** |
| 红 skill (any) | 67 | 47 | **41** |
| foldx 缺口 | 8 | 0 | **0**(全转 pyrosetta@antibody) |
| gnina 缺口 | 5 | 5 | **0**(GitHub v1.3.2 cuda12.8) |
| mmseqs2 缺口 | 1 | 1 | **0**(PRAXIS-Enzyme) |
| mkdssp/dssp 缺口 | 6 | 6 | **3**(praxis-protein) |
| system prompt 注入大小 | None | None | **24–32 KB** |
| 真 ssh E2E 跑通 skill | 0 | 0 | **8 simulate + 1 真 gnina** |
| 模型真 chat-stream 闭环 | 0 | 0 | **2 次**(simulate + 真) |

---

## 4. 12 个 brain 主路径全绿 skill 名单(v0.9.4 实时)

| brain | green skill 数 | 名单 |
|---|---|---|
| cell | 4 | 3d-organoid-segment、cellpose-segment、live-cell-track、spatial-proteomics-pipeline |
| crispr | 1 | crispr_crispor_design |
| dock | **9** | af3_complex_predict、covalent_docking、flexpepdock_peptide、induced_fit_docking、pose_buster_validate、protein_na_docking、**redock_benchmark**、snugdock_antibody、**vina_gnina_dock**(真 gnina) |
| drug | 4 | admet_multi、fep_relative_affinity、protac_ternary、vina_gnina_dock |
| enzyme | 2 | cazy-crawler、esm-mutation-scan |
| immuno | 4 | hla_typing_rnaseq、mhc_class_i_predict、tcr_pmhc_dock、tcr_seq_repertoire |
| microbiome | **11** | amplicon_minimal_real、cultured_isolate_wgs_real、da_compositional_real、humann_functional(+_real)、its_fungal_real、mag_assembly_real、scfa_butyrate_screen_real、shotgun_taxonomy(+_real)、strain_tracking_real |
| omics | 3 | multimodal_wnn、scrna_annotate、scrna_qc_pipeline |
| pharma | **4** | allometric_scale、pbpk_simulate、pkpd_emax、ppb_assess |
| protein | **10** | antibody_pipeline、binder_failure_postmortem、boltz_structure_predict、de_novo_binder_pipeline、esmfold_high_throughput、proteinmpnn_redesign、proteinmpnn_sequence、rfdiffusion_design、symmetric_design_pipeline、thermompnn_stability |
| **合计** | **52** | (cryo 11 个全部 not-deployed,_common nature_plot 不计入) |

---

## 5. 怎么用 v0.9.4(给后接手人)

### 5.1 解包

```bash
# 从 tag 拉
git fetch && git checkout v0.9.4
# 或从 tarball
cd /tmp && tar xzf praxis2-v0.9.4.tar.gz && cd praxis2-v0.9.4
```

### 5.2 跑测试

```bash
. .venv/bin/activate   # 已 M9 时建好的
pytest tests/          # 635 passed / 17 skipped / 0 failed
```

### 5.3 起服务(production)

```bash
# 部署 .53(backend) + .40(frontend) — 同 M9
bash deploy/push_backend.sh
bash deploy/push_frontend.sh
# 新加的环境变量(SkillExecTool 用):
export PRAXIS_SKILL_SSH_HOST=zkyd@10.102.106.53
export PRAXIS_SKILL_REMOTE_BRAINS=/home/zkyd/data1/mzy/praxis2-brains
export PRAXIS_SKILL_CONDA_INIT=/home/zkyd/software/miniconda3/etc/profile.d/conda.sh
```

### 5.4 真 E2E 单文件验证(绕开 server 直接验 query() 闭环)

```bash
PRAXIS_ANTHROPIC_API_KEY=<key> \
PRAXIS_ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic \
PRAXIS_MODEL=deepseek-chat \
PRAXIS_SKILL_SSH_HOST=zkyd@10.102.106.53 \
PRAXIS_SKILL_REMOTE_BRAINS=/home/zkyd/data1/mzy/praxis2-brains \
PRAXIS_SKILL_CONDA_INIT=/home/zkyd/software/miniconda3/etc/profile.d/conda.sh \
python3 /tmp/e2e_real_chat.py dock "你的问题"
```

测试器代码见会话历史(单文件 130 行,无依赖)。

### 5.5 重采 host inventory + 重跑对账(skill 装新工具后)

```bash
bash scripts/audit/refresh_all.sh run
# 自动:ssh .53 install P0 包 → 拉 host_raw.txt → parse → extract → parity → 刷 green_skills.json
```

### 5.6 给新 skill 加真 CLI 实现

```bash
# 参照 docs/SKILL-SIMULATE-TO-REAL-GUIDE.md
# 范本:brains/dock/skills/workflows/vina_gnina_dock/run.py
# 步骤:simulate() 不动 → real() stub 改 subprocess.run(cli) → 解析 → JSON
# 完成后:
rsync -a brains/<brain>/skills/workflows/<skill>/run.py \
  zkyd@.53:/home/zkyd/data1/mzy/praxis2-brains/<brain>/skills/workflows/<skill>/
```

---

## 6. 边界(本版没做)

| 项 | 状态 | 影响 |
|---|---|---|
| 51 / 52 green skill 的 real() 还是 stub | 待做 | 智能体能调,但拿合成数据;真分析价值 ≈ 0 |
| 真 chat-stream HTTP(SSE)端到端 | 未验 | 单文件验过 query() loop,server SSE 路径靠 624 测试;production 真请求未跑 |
| HPC bio000070 投递(M7 carry) | 未启 | 长 MD / 大模型预测走 sbatch 没接 |
| pyrosetta-stability-scan real 路径 | stub | simulate 模式 OK,真 cartesian_ddg 没接 |
| `praxis-drug-base` / `praxis-drug-vina` SKILL.md env 脱节 | 3 skill 仍红 | 改 frontmatter 即可解(SOFTWARE-GAP-REPORT §7) |
| gromacs / salmon / scvi 装包 | 留 P1 | 影响 omics 几个 skill |
| frontend 集成 SkillExec 可视化 | 未做 | 后端事件流原样;前端按 M9 老逻辑 |
| deploy/push_backend.sh 加 brains rsync | 未补 | 现 brains/ 是手工 rsync,真上线要 push 脚本自动化 |

---

## 7. v0.9.4 → v1.0 还差什么

| 优先级 | 工作 | 估时 |
|---|---|---|
| P0 | 真打一次 production `/chat/stream` SSE(SSH env 设好 + 真 key 起 gunicorn + curl 真验) | 30 min |
| P0 | 51 个 green skill 的 real() 实现按 SIMULATE-TO-REAL-GUIDE 推进 | **~21 小时**(平均 25 min/skill;P0 8 个先做完是 ~ 1 小时) |
| P0 | deploy/push_backend.sh 补 `rsync brains/` 一段 | 5 min |
| P1 | HPC bio000070 真投一次 sbatch + 接 ResourceGate | 2 小时 |
| P1 | frontend 加 SkillExec 调用可视化 | 半天 |
| P2 | gromacs / salmon / scvi 装包 + 重跑对账 | 1 小时 |
| P2 | cryo env 真起一遍(relion + cryosparc license),恢复 cryo 路由 | 1 天 |

**所有 P0 做完(~22 小时 dedicated)→ v1.0**(真正"科研版 Claude"上线条件齐)。

---

## 8. 文件总览(本版新增/重要)

```
brains/                                  # 152 SKILL.md + 152 run.py(151 模板 + 1 真)
  dock/skills/workflows/vina_gnina_dock/
    SKILL.md                             # frontmatter:status:green/host_env:praxis-dock
    run.py                               # 200 行 真 gnina 实现
  enzyme/skills/workflows/pyrosetta-stability-scan/  # foldx 重命名
    SKILL.md                             # ref15_cart + cartesian_ddg 重写
    run.py                               # simulate 路径手写
  cryo/skills/workflows/*/SKILL.md       # 11 个加 status:not-deployed
  (13 个新 stub skill)                    # boltz/chai/rfdiffusion/... 占位

praxis2/
  brains/system_prompt.py                # 新:build_chat_system_prompt 5 步
  tools/skill_exec.py                    # 新:SkillExecTool 子类 Tool
  server/chat_registry.py                # 改:register SkillExecTool
  server/app.py                          # 改:_chat_stream 真传 system
  agents/loader.py                       # 改:cryo 路由关键词置空

scripts/audit/                           # 新:5 个一次性脚本
  install_p0_packages.sh                 # ssh .53 装 gnina/dssp/mmseqs2/praxis-pharma
  refresh_all.sh                         # 一键:装包 → 重采 → 重跑对账
  generate_run_py.py                     # 152 run.py 模板生成器
  extract_brain_deps.py                  # 改:fetcher false-positive + import bug 修
  collect_host.sh / parse_host.py / parity.py  # 已有

tests/                                   # 新增 11 测试
  test_brains_system_prompt_wiring.py    # PLAN §11 接线保护
  test_tools_skill_exec.py               # 6 个 SkillExec 行为 + degradation
  test_server_chat_registry.py           # SkillExec 已注册到 chat-stream

_audit/                                  # 新:全套审计产物
  host_inventory.json                    # 44 envs / 1785 pkgs / 8×A100
  brains_deps_inventory.tsv              # 280 条依赖
  parity_matrix.tsv                      # 280 对账行
  parity_summary.json                    # 41 red / 208 green
  green_skills.json                      # 52 全绿 skill 名单(model 注入参考)
  skill_real_impl_inventory.csv          # 52 行:每 skill TODO/DONE 状态
  host_raw.txt                           # ssh 采集 raw

docs/
  SKILL-SIMULATE-TO-REAL-GUIDE.md        # 新:51 个 TODO 转换指南 + 分级

# 根级
PLAN-SOFTWARE-PARITY.md                  # 新:对账计划
SOFTWARE-GAP-REPORT.md                   # 新:gap 报告 v1→v2→v3
VERSION-STATUS-2026-05-22.md             # 新:历程文档(本版 +前两版的合并)
VERSION-STATUS-v0.9.4.md                 # 新:本文,锁定 v0.9.4
```

---

## 9. 测试一致性

```
$ pytest tests/ --tb=line
635 passed, 17 skipped in 7.40s
```

新增测试覆盖(从 502 → 635 = +133):
- M5 carry 范围:system prompt 接线、SkillExec 行为 + degradation
- 跨模块:host_env 过滤、query 相关度排序、Skill 注册 in chat_registry
- 兼容性:fake_query mock 加 **_kw 接受 system 参数(3 个旧测试)

---

## 10. 验收清单(v0.9.4 出货 = 都过)

- [x] 测试 635 passed / 0 failed
- [x] 152 SKILL.md 全有 run.py(`find brains -name run.py | wc -l` = 152)
- [x] foldx 在 brains/ 内 0 处残留(除 pyrosetta-stability-scan SKILL.md 的迁移注记)
- [x] cryo 11 skill 全部 `status: not-deployed`
- [x] system_prompt._host_envs() 读出 44 个 staging envs(含新建的 praxis-pharma)
- [x] vina_gnina_dock 在 .53 真跑(`gnina --version` v1.3.2 cuda12.8)
- [x] 真 chat-stream(via DeepSeek-Anthropic compat)2 次成功:1 simulate + 1 真 gnina
- [x] 8/8 学科代表 skill 真 ssh E2E 跑通
- [x] git tag `v0.9.4`(commit `49aa0af`)
- [x] tarball `/tmp/praxis2-v0.9.4.tar.gz`(1.5 MB)
- [x] VERSION-STATUS-v0.9.4.md(本文件)

---

> 下个里程碑:**v1.0** = §7 表里 P0 全做完(估 22 小时 dedicated)。
> 详细迁移指南 见 `docs/SKILL-SIMULATE-TO-REAL-GUIDE.md`。
> 真分析范本 见 `brains/dock/skills/workflows/vina_gnina_dock/run.py`。
