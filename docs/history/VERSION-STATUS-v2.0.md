# v2.0 现状(13 brain × 152 skill 全量 real-uplift 收尾)

> 锁定:2026-05-23 · base:`v0.9.4`(9f797a1)→ HEAD `fb6eeea`
> 关联文档:`VERSION-STATUS-v1.0-uplift.md`(基础 152 simulate+real 骨架)、`VERSION-STATUS-v1.1.md`(hotfix)
> 子版本 tag:v1.0-uplift / v1.1 / v1.2-dock / v1.3-drug / v1.4-protein / v1.5-microbiome / v1.6-omics / v1.7-enzyme / v1.8-cell / v1.9-crispr / v1.10-cryo / v1.11-immuno / v1.12-pharma / v1.13-md

## 1. 数字一览

| 桶 | 数 | 占比 |
|---|---|---|
| GREEN real CLI(可在 .53 真跑) | **109** | 71.7% |
| N/A(license / web / composite / 工具缺 / prompt-only) | **41** | 27.0% |
| Hand-written DONE_real(v0.9.4 沿用) | **2** | 1.3% |
| **合计** | **152** | 100% |

pytest:`tests/skills/` **929 passed / 4 skipped / 0 failed**(skipped = 2 hand-written × 2 schema-match copies)。

## 2. Hand-written DONE_real(2)

| brain/skill | 行数 | 说明 |
|---|---|---|
| `dock/vina_gnina_dock` | 317 | v0.9.4 已 done;vina+gnina CNN scoring + RDKit + autobox |
| `enzyme/pyrosetta-stability-scan` | 143 | hand-written `simulate_scan` / `real_scan`,基于 pyrosetta cartesian_ddg |

## 3. N/A 清单(41,按原因分桶)

### 3.1 License / 商业受限(5)

| brain/skill | 缺什么 |
|---|---|
| `dock/induced_fit_docking` | Schrödinger IFD 商业 license |
| `dock/haddock_pp_with_air` | HADDOCK3 license / 重装 |
| `cryo/phenix_validation` | Phenix academic license + install |
| `cryo/model_angelo_build` | ModelAngelo install + 预训练 checkpoint (~4 GB) |
| `immuno/mhc_class_ii_predict` | netMHCIIpan license(mhcflurry 默认仅 class I) |

### 3.2 Web server / 无本地 CLI(2)

| brain/skill | 工具 |
|---|---|
| `dock/cluspro_blind_pp` | ClusPro web server,需 REST wrapper |
| `protein/consurf_conservation` | ConSurf web server(consurf.tau.ac.il) |

### 3.3 Composite pipeline(需多工具串联,非单一 tool)(4)

| brain/skill | 说明 |
|---|---|
| `protein/antibody_pipeline` | IgFold/AbodyBuilder + RFdiffusion + ProteinMPNN + snugdock + esm |
| `protein/binder_failure_postmortem` | DSF/SPR + AF binding + esm logit + foldseek 回顾分析 |
| `pharma/gpcr_agent_screen` | docking + selectivity panel + cAMP/β-arrestin assay |
| `cryo/af_cryoem_hybrid` | AlphaFold + cryoSPARC fit + ModelAngelo + Coot 复合 |

### 3.4 Host 工具栈缺(可后续 conda install / git clone)(20)

| brain | skills | 缺什么 |
|---|---|---|
| `cryo` | 9 个:`motion_correct_ctf` / `particle_pick_consensus` / `2d_3d_classify` / `focused_refine` / `multibody_refine` / `subtomogram_avg` / `preferred_orientation_diag` / `environment_setup` | RELION 4 / cryoSPARC / Warp+M / Dynamo / crYOLO / Topaz / cryoEF |
| `omics` | 4 个:`multiqc_aggregate` / `salmon_quant` / `scatac_archr_pipeline` / `cnv_inference_dual` | multiqc / salmon / ArchR (R) / inferCNV |
| `microbiome` | 4 个:`mag_assembly_pipeline` / `mag_assembly_real` / `meta_hi_c_binning` / `meta_hi_c_real` | megahit + metabat2/maxbin2/concoct + MetaCC/bin3C |
| `cell` | 3 个:`imc-pipeline` / `spatial-proteomics-pipeline` / `vcell_simulate` | steinbock / squidpy 完整栈 / tellurium 或 COPASI SBML simulator |
| `enzyme` | 1 个:`pocket-tunnel-analyzer` | fpocket / CAVER / DoGSite |
| `drug` | 1 个:`pocket2mol_sbdd` | Pocket2Mol git clone + checkpoint |
| `drug` | 1 个:`protac_ternary` | PRosettaC 或 商业 PROTAC modeling tool |

### 3.5 Composite/dataset 依赖(2)

| brain/skill | 说明 |
|---|---|
| `protein/conformation_ensemble` | conformation repo 只 training,无 standalone inference 入口 |
| `microbiome/multiomics_integration` / `_real` | mixOmics/iCluster/MOFA 等多组学集成工具未明确装(2 项) |

### 3.6 Prompt-only / agent-guidance skill(非 tool)(5)

| brain/skill | 说明 |
|---|---|
| `md/code-review` | 指导 agent 审查分析脚本 |
| `md/pdb-literature-report` | PDB+文献+报告 agent workflow |
| `md/research` | 调研工作流指南 |
| `enzyme/environment-setup` | host env probe helper(SkillExecTool 已自动 conda activate) |
| `cryo/environment_setup` | 同上 |

### 3.7 N/A 合计校验

5 license + 2 web + 4 composite + 20 host-tool-missing + 2 composite/data + 5 prompt-only + 3 cell(在 3.4) = 41 ✓

## 4. GREEN real CLI 速览(109)

按 brain × 主要工具栈:

| brain | green | 主要工具 |
|---|---|---|
| `_common` | 1 | matplotlib (nature_plot) |
| `cell` | 8 | cellpose + skimage + scanpy + scipy |
| `crispr` | 11 | crispor + cas-offinder + mageck + Bio + primer3 |
| `cryo` | 0 | (全 N/A) |
| `dock` | 8 + 1 hand-written | vina + gnina + boltz + chai + pyrosetta(via DL-masif) + posebusters |
| `drug` | 10 | admet-ai + aizynthfinder + reinvent + openfe + rdkit + vina |
| `enzyme` | 8 + 1 hand-written | esm + BioPython + REST (RCSB/UniProt/PDBe-KB) |
| `immuno` | 10 | mhcflurry + arcasHLA + optitype + ANARCI + boltz |
| `md` | 5 | gmx (新装 praxis-md env) + vina + nohup |
| `microbiome` | 16 | kraken2 + bracken + humann + strainphlan + dada2 + ANCOMBC + Maaslin2 + scipy |
| `omics` | 9 | scanpy + muon + cooler + mofapy2 + cell2location + scrublet + harmonypy |
| `pharma` | 10 | scipy 数学(NCA / Emax / PBPK ODE / Bayesian TDM)+ openFDA REST + RDKit |
| `protein` | 13 | esm + boltz + chai + foldseek + rfdiffusion + ProteinMPNN + ThermoMPNN |
| **合计** | **109** | |

## 5. 关键 host 端变更

### 新装 conda env(本次 uplift 期间)

```bash
# 在 .53 上跑过
conda create -n praxis-md -c bioconda gromacs -y
# gmx 2021.3 装在 /home/zkyd/software/miniconda3/envs/praxis-md/bin.AVX2_256/gmx
```

### 已 rsync 到 .53 的 brains/ 各 brain

每个 brain 闭环 commit 后立即 `rsync -avz --delete brains/<brain>/ zkyd@10.102.106.53:/home/zkyd/data1/mzy/praxis2-brains/<brain>/`。

## 6. commit 列表(v1.1 → v2.0,本次扩展)

| tag | HEAD commit | brain | 真 | N/A |
|---|---|---|---|---|
| v1.2-dock | 119f0e4 | dock | 8 + 1 HW | 4 |
| v1.3-drug | 36d4c9f | drug | 10 | 2 |
| v1.4-protein | 76c22aa | protein | 13 | 4 |
| v1.5-microbiome | be7e2d2 | microbiome | 16 | 6 |
| v1.6-omics | f3513ae | omics | 9 | 4 |
| v1.7-enzyme | af469ef | enzyme | 8 + 1 HW | 2 |
| v1.8-cell | de4701c | cell | 8 | 3 |
| v1.9-crispr | bf010ff | crispr | 11 | 0 |
| v1.10-cryo | 2d772f0 | cryo | 0 | 11 |
| v1.11-immuno | dfaf8e7 | immuno | 10 | 1 |
| v1.12-pharma | 66b371b | pharma | 10 | 1 |
| v1.13-md | fb6eeea | md | 5 | 3 |
| **v2.0** | (本 doc commit) | **+ _common** | **109 + 2 HW** | **41** |

## 7. v2.0 之后建议路线

| # | 工作 | 估时 |
|---|---|---|
| 1 | host 端装 cryoSPARC / RELION 4(unlock 8 cryo skill) | 1-2 day(license + GPU 配置) |
| 2 | conda install multiqc + salmon(praxis-omics)(unlock 2 omics) | 30 min |
| 3 | conda install -c bioconda r-archr + r-signac(unlock 1 omics)  | 1 h |
| 4 | git clone Pocket2Mol + checkpoint(unlock 1 drug) | 30 min |
| 5 | git clone PRosettaC(unlock 1 drug protac_ternary) | 1 h |
| 6 | conda install fpocket / CAVER(unlock 1 enzyme) | 30 min |
| 7 | conda install megahit + metabat2(unlock 4 microbiome) | 1 h |
| 8 | mhcflurry-class2 训练 model(unlock 1 immuno) | 4-8 h GPU |
| 9 | Schrödinger / HADDOCK 商业 license 决策(unlock 2 dock) | 业务决策 |
| 10 | composite skill orchestrator(antibody/binder/gpcr/af-hybrid)单独搭 | 大项目 |
| 11 | 5 prompt-only skill 移到 `docs/skills/prompts/` 不算 real() | 1 h cleanup |
| 12 | 真 .53 E2E 跑一遍 dock/cellpose/esmfold/kraken/humann smoke 各 1 case | 半天 |

P0(#1 / #12)做完即 v2.1 候选。

## 8. 验收命令

```bash
# 本地全量 pytest
pytest tests/skills/ -q
# Expected: 929 passed, 4 skipped

# .53 上跑一个真 GREEN skill(已在 v1.0-uplift Step 20.4 验证过 cellpose-segment)
export PRAXIS_SKILL_SSH_HOST=zkyd@10.102.106.53 \
       PRAXIS_SKILL_REMOTE_BRAINS=/home/zkyd/data1/mzy/praxis2-brains \
       PRAXIS_SKILL_CONDA_INIT=/home/zkyd/software/miniconda3/etc/profile.d/conda.sh
# 任选 109 个 GREEN 之一 + 合法 inputs 跑

# 重做 fresh parity 矩阵
python3 -m scripts.uplift.parity_per_brain
# Expected: 141 GREEN + 11 N_A(cryo,基于 host_env 维度)

# 跑 N/A 全量扫(本文 §3 数据来源)
python3 -c "
import re
from pathlib import Path
from collections import defaultdict
NA = defaultdict(list)
for rp in sorted(Path('brains').rglob('run.py')):
    if rp.name.startswith('._'): continue
    txt = rp.read_text(errors='replace')
    if 'N/A —' in txt and 'auto-generated by regen_simulate' in txt:
        m = re.search(r'\"N/A — ([^\"]+)\"', txt)
        NA[rp.parts[1]].append((rp.parent.name, m.group(1) if m else '?'))
for b, lst in sorted(NA.items()):
    print(f'{b}: {len(lst)}')
"
```

## 9. 参考

- v1.0-uplift 设计:`docs/superpowers/specs/2026-05-22-skills-real-uplift-design.md`
- v1.0-uplift plan:`docs/superpowers/plans/2026-05-22-skills-real-uplift.md`
- fresh parity 数据:`_audit/parity_v1_per_brain.json`
- host inventory:`_audit/host_inventory.json`(含本次新增 praxis-md env)
- 历史归档:`docs/history/HANDOFF-HOTFIX-v0.9.5.md` / `docs/history/进度与下一步.md`
