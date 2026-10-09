# PRAXIS-2 版本现状 · 2026-05-22

> 标签建议: **v0.9.3-skill-loop-closed**(pre-1.0, M5 carry 真闭环)
> 上一里程碑: `v0.9`(M9 邮箱认证落地)→ 本版核心交付:**「用户问 → 智能体路由 → 调 skill → 真在 .53 跑 → 结果回喂」端到端闭环**

---

## 0. 一句话现状

智能体路径**首次端到端闭环**:8 个学科各抽 1 个 skill,从 Mac 发起 → SkillExecTool → ssh .53 → conda activate → python run.py → JSON 回喂,**8/8 跑通**。

> 真实分析(非合成)还差最后一公里:152 个 run.py 当前只有 simulate 模式(返回合成数据,通路真,内容假);真 cartesian_ddg / vina / cellpose / kraken 等还需逐个把 simulate 替换为真工具 CLI 调用。

---

## 1. 闭环 7 步达成度

| 步 | 含义 | 状态 | 证据 |
|---|---|---|---|
| 1 | 用户提问 → resolve_agent | ✅ | `praxis2/agents/loader.py` |
| 2 | 加载大脑 + retrieve_brain | ✅ | `praxis2/brains/system_prompt.py` |
| 3 | 主路径过滤(host_env ∈ staging) | ✅ | 152 SKILL.md, 52 全绿 |
| 4 | progressive_disclosure 入 system | ✅ | 24 KB system block + cache_control:ephemeral |
| 5 | 模型识别 + 发起 SkillExec 调用 | ✅ | `praxis2/tools/skill_exec.py:SkillExecTool` |
| 6 | **真 ssh+conda 执行** | ✅ | 8/8 E2E demo 全绿 |
| 7 | tool_result(JSON) 回喂 query loop | ✅ | 走 runtools.to_api_tool_result 现成路径 |

---

## 2. 本版关键改动(按 PR 颗粒度)

### 2.1 大脑层

| PR | 影响 |
|---|---|
| **foldx → pyrosetta 全替换** | 49 文件(brains 全 brain 范围);`enzyme/skills/workflows/foldx-stability-scan/` → `pyrosetta-stability-scan/`,SKILL.md 改写为 ref15_cart + cartesian_ddg(antibody env);env install 节重写为 graylab conda channel(不再下载 rotabase) |
| **cryo 临时下线** | `_SLUG_KEYWORDS["cryo"] = set()`(保 key 维持 12 项不变式);11 个 cryo SKILL.md 加 `status: not-deployed` |
| **13 个新 stub SKILL.md** | boltz / chai / rfdiffusion / proteinmpnn / thermompnn / consurf / arcas-hla / hic / DL-masif / gpcr-agents / vcell / conformation / crispor — 每个 env 写一份占位 skill,智能体能看见 .53 已装但此前未引用的能力 |
| **42 个主路径 skill frontmatter 回写** | `status: green` + `host_env: <真实 env>`;手工修 4 处错位(pharma 错指 kraken / DL-masif、dock 错指 DL-masif、immuno 错指 PRAXIS-CRISPR-bins) |
| **152 个 run.py(本版新增)** | archetype 模板生成器,按 brain+skill 名+描述识别为 13 类(docking/omics_scrna/microbiome_pipeline/mutation_scan/...),每个 run.py 接 stdin JSON / 出 stdout JSON,默认 simulate 模式产合成数据。手写 1 个(pyrosetta-stability-scan)架构验证用 |

### 2.2 内核层

| PR | 影响 |
|---|---|
| **system prompt 真接通**(PLAN §11) | `praxis2/brains/system_prompt.py:build_chat_system_prompt` 5 步(加载→检索→host_env 过滤→assemble→to_api_system);`server/app.py:_chat_stream` 现在真传 `system=...` 给 query() |
| **SkillExecTool**(本版新增) | `praxis2/tools/skill_exec.py:SkillExecTool` 子类 Tool;chat_registry 所有模式注册;支持 ssh 真跑(env var 三件套配置)/ 降级返 SOP+命令模板 |
| **query 相关度排序** | skill_summary 按 user_query 词重叠度排序,关键 skill 不被字母序顶掉(vina/gnina query → vina_gnina_dock 排第一) |
| **budget 修正** | skill_budget_chars 默认 5e6 → cap 50 KB 足够全披露 52 green skill |
| **mock test 兼容** | 3 个旧测试的 fake_query 加 **_kw 接 system 参数 |

### 2.3 .53 staging 真实改动

| 改动 | 命令 / 路径 | 影响 |
|---|---|---|
| `gnina` 真二进制 | `~/software/miniconda3/envs/praxis-dock/bin/gnina` (v1.3.2 cuda12.8, 2 GB) | dock 真 PL docking 可用 |
| `cudnn 9.10` | `praxis-dock` env | gnina runtime 依赖 |
| activate hook | `praxis-dock/etc/conda/activate.d/zz_ld_library_path.sh` | 自动 export LD_LIBRARY_PATH |
| `mkdssp` | `praxis-protein` env | RSA / 二级结构 |
| `dssp` symlink → mkdssp | `praxis-protein/bin/dssp` | 老命名兼容 |
| `mmseqs2` | `PRAXIS-Enzyme` env | conservation MSA |
| `praxis-pharma` env 新建 | python3.11 + numpy + scipy + pandas + lifelines + openpyxl + matplotlib + sklearn | PBPK / PKPD |
| **`brains/` rsync 到 .53** | `/home/zkyd/data1/mzy/praxis2-brains/` (152 SKILL.md + 152 run.py) | SkillExecTool 可调任何 skill |

### 2.4 审计工具

| 文件 | 干啥 |
|---|---|
| `scripts/audit/install_p0_packages.sh` | 一键 .53 装 P0 包(gnina/dssp/mmseqs2/praxis-pharma) |
| `scripts/audit/refresh_all.sh` | 闭环:ssh 装 → 重采 inventory → 本地重跑对账 → 刷 green_skills.json |
| `scripts/audit/generate_run_py.py` | 152 个 run.py archetype 模板生成器 |
| `scripts/audit/extract_brain_deps.py` | 加 body_has_data_access_signal()(修 PDB 假阳性);修 `from X import Y` 双匹配 bug |
| `scripts/audit/install_p0_packages.sh` | 改 `set -uo`(单节失败不阻塞)+ conda 显式 source |

---

## 3. 数字对照

| 指标 | M9 (v0.9) | v2(本会话中段) | **v3(本版,2026-05-22)** |
|---|---|---|---|
| 测试通过 | 502 / 17s / 0F | 624 / 17s | **635 / 17s / 0F** |
| Staging conda envs | 43 | 43 | **44**(+praxis-pharma) |
| SKILL.md 数 | 132 | 145 | **152**(+13 stub) |
| **有 run.py 的 skill** | 0 | 0 | **152**(151 模板 + 1 手写) |
| 主路径全绿 skill | 26 / 94 | 41 / 88 | **52 / 93** (+100%) |
| 红 skill (any) | 67 | 47 | **41** |
| foldx 缺口 | 8 | 0 | 0 |
| gnina 缺口 | 5 | 5 | **0** |
| mmseqs2 缺口 | 1 | 1 | **0** |
| dssp/mkdssp 缺口 | 6 | 6 | **3** |
| system prompt 大小 | None | None | **24 KB / cache_control:ephemeral** |
| 真 E2E 跑通的 skill | 0 | 0 | **8**(各学科代表) |

---

## 4. archetype 分布(本版生成的 run.py)

| archetype | 数量 | simulate 输出含义 |
|---|---|---|
| omics_scrna | 25 | 细胞数 / 聚类数 / marker 基因表 |
| microbiome_pipeline | 22 | 样本×物种丰度矩阵 / Shannon α 多样性 |
| docking | 15 | 9 pose 表 + binding affinity + redock self-test |
| drug | 12 | LogP / TPSA / QED / pIC50 表 |
| crispr | 11 | sgRNA 表 + on/off-target 分数 |
| cryo | 11 | 分辨率 / FSC / 粒子数(实际未部署,纯合成) |
| pharma | 11 | PK 参数 + 时间-浓度曲线 |
| mhc_epitope | 10 | 肽段表 + affinity + binder flag |
| structure_predict | 9 | pLDDT / pTM / 每残基置信度 |
| mutation_scan | 9 | (pos, wt, mut, ΔΔG, std, filter) 表 |
| msa_conservation | 6 | conservation 0-9 分数 / 高保守位点 |
| generic | 7 | echo inputs + simulated:true |
| fetcher | 3 | local_path + bytes + simulated:true |

---

## 5. 8 个 E2E demo(真在 .53 跑出来的 JSON 摘要)

| 学科 | skill | host_env | 关键产出 |
|---|---|---|---|
| dock | vina_gnina_dock | praxis-dock | best_affinity=-8.05 kcal/mol, 9 pose 表 |
| omics | scrna_qc_pipeline | praxis-omics | 5 clusters, marker 基因表 |
| microbiome | shotgun_taxonomy | praxis-microbiome-kraken | 3 sample × 10 taxa, Shannon α |
| immuno | hla_typing_rnaseq | praxis-immuno | HLA-A*02:01, 30 peptide 表 |
| pharma | pbpk_simulate | praxis-pharma | t_half=3.26 h, Cmax=15.17 ng/mL, 25 时间点曲线 |
| protein | rfdiffusion_design | rfdiffusion | ranking_confidence=56.47, plddt 表 |
| crispr | sgrna_design_score | PRAXIS-CRISPR | TP53 2 guide,on/off score |
| enzyme | pyrosetta-stability-scan | antibody | 38 突变 ΔΔG,最佳 H196W=-1.521(passes filter) |

---

## 6. 已知边界 & 下一版 carry

### 6.1 真分析 vs simulate

**当前所有 152 个 run.py 默认 simulate 模式**,产合成数据。真分析路径:

| skill 类别 | 当前 simulate 路径 | 真实现要补的事 |
|---|---|---|
| `pyrosetta-stability-scan` | 高斯随机 ΔΔG | `pyrosetta.init()` + `cartesian_ddg.xml` 协议(antibody env 已装,直接接) |
| `vina_gnina_dock` | 9 random pose | `subprocess` 调 `vina` + `gnina --score_only` rescore(praxis-dock 已装) |
| `cellpose-segment` | n_cells 假数 | `cellpose.io.imread` + `model.eval()`(PRAXIS-Cell 已装) |
| `boltz_structure_predict` | random plddt | `boltz predict ...`(boltz env 已装) |
| `chai_complex_predict` | random pTM | `chai-lab fold ...`(chai env 已装) |
| ... | ... | 每个 5–30 行,模板化工作 |

### 6.2 其他 carry

- **gromacs**:3 个 protein/dock skill 引用,装包大 ~30 min,留 P1
- **salmon / scvi**:omics 3 + 2 skill 引用,留 P1
- **真打一次 chat-stream 到 Anthropic API**:本版只跑了 unit + ssh E2E,**没用真 API key 验证 system prompt 真到达模型 + 模型真发起 SkillExec**。需 `PRAXIS_ANTHROPIC_API_KEY=... python -m praxis2.server` 起 server 真请求 `/chat/stream`
- **praxis-drug-base / praxis-drug-vina**:3 个 SKILL.md 写了不存在的 env 名;改 frontmatter 为 praxis-drug / praxis-dock(已在 SOFTWARE-GAP-REPORT §7 提)
- **HPC bio000070 carry**(M7):大模型预测 / 长 MD 等重 GPU 任务还未走 sbatch
- **deploy/push_backend.sh 加 brains rsync**:目前 brains/ 是手工 rsync,部署脚本要补这一步

### 6.3 archetype 误判已知

- `pyrosetta-stability-scan` archetype=? 因 SKIP(手写),diagnostics 没自动加;非问题但显示空
- enzyme/protein 中"非 mutation 类"skill(catalytic-site-annotator / pocket-tunnel-analyzer 等)被分到 msa_conservation 兜底,输出更合理但不完美

---

## 7. 怎么用本版(给接手人)

```bash
# 1. 本地把 brains/ 同步到 .53(已在 refresh_all.sh 里;独立脚本待补)
rsync -a --delete --exclude '._*' --exclude '__pycache__' \
  brains/ zkyd@10.102.106.53:/home/zkyd/data1/mzy/praxis2-brains/

# 2. 跑后端时设三件套环境变量,SkillExecTool 才真 ssh:
export PRAXIS_SKILL_SSH_HOST=zkyd@10.102.106.53
export PRAXIS_SKILL_REMOTE_BRAINS=/home/zkyd/data1/mzy/praxis2-brains
export PRAXIS_SKILL_CONDA_INIT=/home/zkyd/software/miniconda3/etc/profile.d/conda.sh

# 3. 起服务(后端 + 前端同 M9):
python -m praxis2.server   # 后端
# 前端按 deploy/push_frontend.sh

# 4. 验证(任何学科都能调):
python3 -c "
import asyncio, json, os
from praxis2.tools.skill_exec import SkillExecTool
t = SkillExecTool()
r = asyncio.run(t.run({'name':'vina_gnina_dock','brain':'dock','inputs':{'seed':1}}))
print(json.dumps(r.value['result'], indent=2, ensure_ascii=False))
"

# 5. 没设 PRAXIS_SKILL_SSH_HOST 时,SkillExec 自动降级返 SOP + 预填命令,
#    模型可以把命令念给用户人工跑(适合 staging 联通失败的兜底)。
```

---

## 8. 测试覆盖

- 全套 `pytest tests/` = **635 passed / 17 skipped / 0 failed**(M5 carry 完结)
- 关键新单测:
  - `tests/test_brains_system_prompt_wiring.py`(PLAN §11 接线保护)
  - `tests/test_tools_skill_exec.py`(SkillExec 工具行为 + degradation 路径)
- 端到端真 ssh 跑通的 skill 名单见 §5

---

## 9. 与上游设计文档的对齐

- 设计总纲 §3 step2.5 ✅ retrieve-first → 注入 system
- 设计总纲 §7.1 ✅ query() 真接收 system
- 设计总纲 §7.3.1 ✅ SkillExecTool 实现 Tool 契约 + rmcp_op="execute"
- 设计总纲 §7.5.0 ✅ skill 选择不产生第二条代码路径(SkillExecTool 是单一路径)
- 设计总纲 §7.5.4 ✅ discipline 模式禁 AgentTool 但允许 SkillExec(本学科子工具,不递归)
- PLAN-SOFTWARE-PARITY.md §11 ✅ 5 步接线全部实现并打测试网
- PLAN-SOFTWARE-PARITY.md §12 ✅ 「先零报错路径」原则:host_env 过滤把 cryo 等下线 skill 从 turn-1 system 移除

---

## 10. 还要做这两件事才真完整(给后接手人的 P0)

1. **真打一次 chat-stream + 真 API key**:本版上线前必跑。预期看到模型在 system prompt 引导下发起 `SkillExec(name="...")` 调用,并把回喂的 simulated JSON 转述给用户,验证整条 turn 1→2→3 闭环。

2. **把一个真分析跑通**:挑 vina_gnina_dock 把 simulate 替换为真 vina + gnina 调用(gnina 已装),输入真 receptor.pdb + ligand.sdf,产 9 个真 pose + 真 affinity。这一条真打通之后,其余 51 个 green skill 按同样模板批量替换。

完成 §10 这两步,**v0.9.3 → v1.0**(真正"科研版 Claude"上线条件齐)。

---

## 11. v0.9.4 增量(2026-05-22 当晚)

§10 的两件事**都做了**:

### 11.1 真 chat-stream E2E(§10.1 done)

- gateway: DeepSeek Anthropic-compat (`https://api.deepseek.com/anthropic`, model `deepseek-chat` → `deepseek-v4-flash`)
- 测试器: `/tmp/e2e_real_chat.py`(单文件,绕开 server / Redis / SSE 直接验 query() 闭环)
- 真闭环 2 次:
  - **第 1 次**:用户问 "vina+gnina docking SMILES=CCO" → 模型 `tool_use: SkillExec(name="vina_gnina_dock", ...)` → SkillExecTool ssh → simulated JSON → 模型出 506 token 中文综合报告
  - **第 2 次**:用户问 "1iep + Imatinib SMILES" → 同上但 run.py 已是真 gnina → **真 gnina 跑 26.86 秒** → 真 vina/-7.69 + CNN affinity=6.82 → 模型识别 cross-method divergence + 引用 1IEP/Met318 hinge + 推荐下一步 skill (pose_buster_validate / redock / induced_fit)
- 完整 turn 1→2→3:user → model+tool_use → tool_result(真 JSON)→ model 转述 → end

### 11.2 vina_gnina_dock 真实现(§10.2 done)

- `brains/dock/skills/workflows/vina_gnina_dock/run.py` 重写 200 行
- 入口:`receptor_pdb` + `ligand_smiles | ligand_sdf` → RDKit 3D conformer → gnina --autobox_ligand → sdf.gz → 解析 5 个 SDF property (minimizedAffinity / CNNscore / CNNaffinity / CNN_VS) → JSON
- autobox 三档选择:用户 box / receptor crystal HETATM(non-water 最大) / ligand 本身
- gnina cmd: `--cnn_scoring rescore`(CPU-friendly,GPU 也通)
- 失败必返 `{"ok": false, "error": ...}` 不抛 traceback
- 实测:1iep + Imatinib → 26.86 秒 / 5 poses / autobox 用 STI crystal / Vina best -7.69 / CNN affinity 6.82

### 11.3 51 个 TODO skill 转换(§10.2 后续)

- **诚实评估**:不是"批量复制粘贴" — 每个 skill 真实现是不同 CLI 的包装,但**模式可复用**
- 产出物:
  - `docs/SKILL-SIMULATE-TO-REAL-GUIDE.md`(范式 + archetype CLI 速查 + 单 skill 转换步骤 + P0/P1/P2/P3 分级清单)
  - `_audit/skill_real_impl_inventory.csv`(52 个 green skill × status)
  - 估时:51 个 × 平均 25 分钟 = ~ 21 小时(假设 1 人 dedicated)
- P0 候选 8 个(纯 in-process python,5–15 分钟/个,共 ~ 1 小时):admet_multi / allometric_scale / pbpk_simulate / pkpd_emax / ppb_assess / cazy-crawler / mhc_class_i_predict / sgrna_design_score
- P1 候选 11 个(单步 subprocess,15–30 分钟/个,共 4–6 小时):cellpose-segment / boltz / chai / esmfold / rfdiffusion / proteinmpnn / hla_typing / tcr_seq / covalent_docking / redock_benchmark / ...

---

## 12. 最终现状(v0.9.4 真闭环 + 1 真实现)

| 指标 | v0.9.3 | **v0.9.4(本版)** |
|---|---|---|
| 测试通过 | 635 / 0 failed | **635 / 0 failed**(保持) |
| 真 ssh E2E skill | 8(simulate) | **9**(8 simulate + 1 **真 CLI**) |
| Anthropic API 真打通 | ❌ | ✅ **deepseek-anthropic-compat 验证** |
| 智能体 turn 1→2→3 真转述 | ❌ | ✅ **2 次,1 simulate + 1 真 gnina** |
| 51 个 TODO 迁移路径 | 暧昧 | ✅ **范式 + 分级清单 + estim** |

### 13. 距 v1.0 真上线还差

- 51 × ~25 分钟 = 21 小时(P0+P1+P2)真分析实现工作(已有指南,没新设计)
- HPC bio000070 投递路径(M7 carry,长 MD / 大模型预测)
- 真打一发到 `_chat/stream` SSE(本版绕开了 server 直接 query;server SSE 已有 624 测试覆盖,但 production 还要起 gunicorn + redis 真请一回)
- frontend 集成新 `SkillExec` 工具的可视化(目前是后端事件流原样)
