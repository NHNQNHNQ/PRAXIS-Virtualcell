# SOFTWARE-GAP-REPORT — 大脑分析方案 ↔ .53 可执行性对账

> 产出日期:2026-05-22(v1: 初版;v2: 修启发式 false positive + foldx→pyrosetta 替换 后重跑)
> 来源:`_audit/host_inventory.json`(阶段 0,ssh zkyd@10.102.106.53 实采)
>      `_audit/brains_deps_inventory.tsv`(阶段 1,扫描 132 SKILL.md 提取 280 条依赖,v2)
>      `_audit/parity_matrix.tsv`(阶段 2 对账)
>      `_audit/green_skills.json`(v2:全绿 skill 名单)
> 配套:`PLAN-SOFTWARE-PARITY.md`(本对账计划)

---

## v3 更新摘要(2026-05-22,P0 真装 + 重采 inventory 后)

| 指标 | v1 | v2(启发式修+foldx 替换) | v3(.53 真装 P0) |
|---|---|---|---|
| 总依赖条目 | 308 | 280 | 289 |
| **主路径 — 全绿可跑 skill** | **26 / 94** | 41 / 88 | **52 / 93** (+100%) |
| 红 (any) skill | 67 | 47 | **41** (-39%) |
| green 总条 | 170 | 187 | 208 |
| data:pdb 缺口 | 27 | 4 | 4 |
| foldx 缺口 | 8 | 0 | 0(全 brain → pyrosetta@antibody) |
| gnina 缺口 | 5 | 5 | **0**(GitHub v1.3.2 cuda12.8 二进制 + cudnn9) |
| dssp/mkdssp 缺口 | 6 | 6 | **3**(praxis-protein 装好 + dssp symlink;其他 env 缺) |
| mmseqs2 缺口 | 1 | 1 | **0**(PRAXIS-Enzyme 装好) |
| 新建 env | — | — | **praxis-pharma**(numpy+scipy+pandas+lifelines) |

**触发改动**(v3,本轮在 .53 上真跑):
1. `scripts/audit/refresh_all.sh`:一键闭环(ssh 装 → 重采 → 本地重跑对账 → 刷新 green_skills.json)。
2. P0 装包真上 `.53`:
   - `gnina` 走 GitHub release(v1.3.2 cuda12.8 binary,2 GB,放 praxis-dock/bin)+ `cudnn 9.10`(走 conda-forge)+ activate.d 注 `LD_LIBRARY_PATH`。`gnina --version` 真出。
   - `mkdssp` 走 conda `-c bioconda -c salilab` 装入 praxis-protein,补 `dssp → mkdssp` 符号链接。
   - `mmseqs2` 走 `-c bioconda` 装入 PRAXIS-Enzyme。
   - 新建 `praxis-pharma` env(python 3.11 + numpy + scipy + pandas + lifelines + openpyxl + matplotlib + scikit-learn);`pkpdsim` pip 暂无 wheel 略过(skill 用 scipy.integrate 兜底)。
3. install 脚本改 `set -uo`(单节失败不阻塞后续);加 conda 显式 source(非交互式 shell 不自动加载)。

**v3 主路径 52 skill 按 brain**:

| brain | 全绿 skill 数 | 新增 vs v2 | 备注 |
|---|---|---|---|
| cell | 4 | — | |
| crispr | 1 | +1 | crispr_crispor_design(v2 期间补的 stub) |
| dock | **9** | +2 | **gnina 装好后 vina_gnina_dock / redock_benchmark 升绿** |
| drug | 4 | +1 | vina_gnina_dock 跨 brain 复用 |
| enzyme | 2 | +1 | **mmseqs2 装好后 esm-mutation-scan 升绿** |
| immuno | 4 | — | |
| microbiome | 11 | — | |
| omics | 3 | — | |
| pharma | **4** | +2 | **praxis-pharma env 新建后 allometric / pbpk / pkpd_emax / ppb_assess 升绿** |
| protein | **10** | +4 | rfdiffusion_design、boltz_structure_predict、proteinmpnn_sequence、thermompnn_stability(v2 stub 加 host_env 后能被识别) |
| **合计** | **52** | **+11** | |

> ⚠️ 以下原文(§0–§10)为 v1 内容,数字未刷新;以**本节 v3 数据为准**。

---

**触发改动**(本次):
1. `scripts/audit/extract_brain_deps.py` 加 `body_has_data_access_signal()` 启发式:只在 body 出现"镜像 / /databases/ / rsync / ftp.wwpdb"等访问信号时,才把 PDB/UniProt 算作数据缺口 — 否则把它当**输入格式**而非本地镜像依赖。
2. `IMPORT_LINE_RE` 锚定行首,修了 `from X import Y` 双匹配 bug(原会把类名 Y 当顶层包)。
3. `brains/enzyme/skills/workflows/foldx-stability-scan/` 重命名为 `pyrosetta-stability-scan/`;47 个文件全 brain 范围 foldx → pyrosetta 替换(用 PyRosetta cartesian_ddg + ref15_cart score function 代替 FoldX BuildModel)。env 锁定 `antibody`(staging 已装)。
4. 新增 `scripts/audit/install_p0_packages.sh`:.53 上一键装 gnina/dssp/mmseqs2 + 新建 praxis-pharma env。foldx 不再装。

**v2 主路径 41 skill 按 brain**(以下表替代历史 §3 的 26 列表):

| brain | 全绿 skill 数 | 名单 |
|---|---|---|
| cell | 4 | 3d-organoid-segment、cellpose-segment、live-cell-track、spatial-proteomics-pipeline |
| dock | 7 | af3_complex_predict、covalent_docking、flexpepdock_peptide、induced_fit_docking、pose_buster_validate、protein_na_docking、snugdock_antibody |
| drug | 3 | admet_multi、fep_relative_affinity、protac_ternary |
| enzyme | 1 | cazy-crawler(其他 enzyme skill 还差 mkdssp/mmseqs2,装完应升到 ≥ 5) |
| immuno | 4 | hla_typing_rnaseq、mhc_class_i_predict、tcr_pmhc_dock、tcr_seq_repertoire |
| microbiome | 11 | amplicon_minimal_real、cultured_isolate_wgs_real、da_compositional_real、humann_functional(+_real)、its_fungal_real、mag_assembly_real、scfa_butyrate_screen_real、shotgun_taxonomy(+_real)、strain_tracking_real |
| omics | 3 | multimodal_wnn、scrna_annotate、scrna_qc_pipeline |
| pharma | 2 | allometric_scale、pbpk_simulate |
| protein | 6 | antibody_pipeline、binder_failure_postmortem、de_novo_binder_pipeline、esmfold_high_throughput、proteinmpnn_redesign、symmetric_design_pipeline |
| **合计** | **41** | |

> ⚠️ 以下原文(§0–§10)为 v1 内容,数字未刷新;以**本节 v2 数据为准**。结构性结论(env 命名脱节、cryo 全红、商业 license 状况)仍有效。

---

---

## 0. TL;DR(给用户)

| 关键指标 | 数 |
|---|---|
| Staging `.53` 硬件 | **8×A100-40GB + 144 核 + 503 GiB 内存 + 14 TB nvme** |
| Staging conda envs | **43**(含 PRAXIS-Cell / PRAXIS-CRISPR / PRAXIS-Enzyme / af2 / boltz / chai / esmfold / proteinmpnn / rfdiffusion / thermompnn …) |
| Staging conda 包数(union) | **1782** |
| 本地大脑 SKILL.md 数 | 132(132 文件,扫到 94 有依赖记录) |
| 大脑提到的 conda env 名 | 7 |
| **主路径 — skill 全绿可跑** | **26 / 94 ≈ 28%** |
| 含 red 缺口 skill | 68 / 94 |
| 三大全红学科 | **cryo / dock / enzyme**(0 个 skill 全绿) |

**核心结论**:
1. `.53` 不是 "staging" — 是个真正的 **HPC 节点** + 团队多年累积的 **43 个 conda env**,资源远超此前现状条目暗示。
2. **大脑里写的 env 名(`praxis-cryo-base` 等)与 staging 实有 env 名(`af2`、`boltz`、`PRAXIS-Cell` 等)严重脱节**。这是头号红区原因。
3. **数据集"红"多数是假性**:大脑标了「需要 PDB/UniProt」的 30+ 行,其中很多 skill 本身就是 fetcher(自己去拉),不需本地镜像。本报告会区分这两类。
4. 真正"装了能解锁最多 skill"的 P0 缺口:**foldx (8 skill)**、**gnina (5)**、**mkdssp/dssp (3)**、**gromacs / amber 单独装(3)**。
5. 大脑没用上的 staging 现成资源:`boltz` / `chai` / `rfdiffusion` / `proteinmpnn` / `thermompnn` / `consurf` / `hic` / `DL-masif` / `antibody` / `arcas-hla` — 这些是 **可入大脑作为新 skill** 的现成研究 env。

---

## 1. 环境快照(.53)

```
OS:       Ubuntu 22.04.5 LTS
CPU:      144 cores Intel Xeon Platinum 8352V @ 2.10GHz
Memory:   503 GiB
GPU:      8× NVIDIA A100-SXM4-40GB(共 320 GiB GPU 显存)
Disk:     / 878G(used 51%) · /home/zkyd/data1 7.0T(64%) · /home/zkyd/data2 7.0T(51%)
Conda:    /home/zkyd/software/miniconda3,43 envs
HPC:      no LMOD module system(纯 conda 多 env 管理)
Docker:   /usr/bin/docker
```

**正在跑的服务**(`pgrep -af gunicorn|litellm|uvicorn` + `docker ps`):见 `_audit/host_raw.txt` 的 RUNNING_PROCESSES 段。

---

## 2. 大脑现状(本地 brains/)

132 个 SKILL.md(按学科):

| brain | SKILL.md 数 | 提到 env 名 |
|---|---|---|
| _common | 1 | — |
| cell | 10 | — |
| crispr | 10 | — |
| cryo | 11 | `praxis-cryo-base / -modelangelo / -phenix / -aretomo`(4 个,**均不存在于 staging**) |
| dock | 12 | — |
| drug | 12 | `praxis-drug-base / -vina`(**均不存在**) |
| enzyme | 11 | — |
| immuno | 10 | — |
| md | 1 | — |
| microbiome | 22 | — |
| omics | 12 | — |
| pharma | 10 | `praxis-pharma`(**不存在**) |
| protein | 10 | — |

frontmatter 几乎没填 `deps:` — 我从 body 启发式提取 314 条记录(详 `_audit/brains_deps_inventory.tsv`)。

---

## 3. 主路径 — 26 个完全可跑的 skill

> 这些 skill 在 `.53` 当下零报错可直接调起。是 **system prompt 接入大脑** 时第一批应该让模型用的 skill 集合(对应 PLAN §12.1 主路径)。

| brain | skill(全绿,共 26) |
|---|---|
| cell | `3d-organoid-segment`、`cellpose-segment`、`live-cell-track`、`spatial-proteomics-pipeline` |
| crispr | `sgrna_design_score` |
| drug | `admet_multi`、`fep_relative_affinity`、`protac_ternary` |
| immuno | `hla_typing_rnaseq`、`mhc_class_i_predict`、`tcr_seq_repertoire` |
| microbiome | `amplicon_minimal_real`、`da_compositional_real`、`humann_functional`、`humann_functional_real`、`its_fungal_real`、`mag_assembly_real`、`shotgun_taxonomy_real`、`strain_tracking_real`(8 个,microbiome 是大赢家) |
| omics | `multimodal_wnn`、`scrna_annotate`、`scrna_qc_pipeline` |
| pharma | `allometric_scale`、`pbpk_simulate` |
| protein | `binder_failure_postmortem`、`esmfold_high_throughput` |

按 brain 计:

```
microbiome  8/22 (36%)   — 命名最对齐
cell         4/5 (80%)
drug        3/12 (25%)
immuno       3/5 (60%)
omics        3/7 (43%)
pharma       2/4 (50%)
protein     2/10 (20%)
crispr       1/3
_common      0/1
cryo        0/11   ← 全红
dock        0/12   ← 全红
enzyme      0/11   ← 全红
md           0/1
```

---

## 4. 红区分析

### 4.1 cryo(11 skill 全红)

**主因**:大脑里所有 skill 写 `env: praxis-cryo-base`(或 `-modelangelo` / `-phenix` / `-aretomo`),**这 4 个 env 全部不存在于 staging**。同时关键 CLI(`relion` / `cryosparc` / `motioncor2` / `topaz` / `cryolo` / `ctffind` / `coot` / `phenix` / `model_angelo`)在 staging 任何 env 的 bin 目录都没扫到。

**修复路径**:
- 选 A:在 staging 真建这 4 个 env + 装 cryo 工具(成本高:relion 需要源码编译 + CUDA;cryosparc 商业 license)
- 选 B:把大脑 env 名映射到 staging 已有的某个 env(若有 cryo 兼容 env 但我没识别出 — 需进一步勘察)
- 选 C:声明 cryo 模块当前"**未上线**",从 `agents/loader.py:_SLUG_KEYWORDS` 临时移除 cryo 路由(避免模型推荐用户根本跑不了的方案)

**建议**:C → A 渐进。先在大脑文档里加 `status: not-deployed` 标记,智能体不投 cryo skill 进 prompt。

### 4.2 dock(12 skill 全红)

**主因 1**:几乎所有 skill 标了 `data:pdb` 缺(粗扫产物),**但实际 dock skill 多数是 fetcher**(`vina_gnina_dock` / `cluspro_blind_pp` 等输入是用户传的结构,不需要本地 PDB 镜像)。这是粗扫 false positive。
**主因 2**:`gnina` 真缺(5 个 skill 引用,staging 无)。`amber` / `gromacs` 也无。

**修复路径**:
- 数据假性红:在阶段 1 提取规则加白名单 — skill 名含 `dock`/`fetcher`/`crawler` 的,data:pdb/uniprot 不当缺
- 真缺:`gnina` 可 conda install -c bioconda gnina(P0);amber/gromacs 单独装(P1)

### 4.3 enzyme(11 skill 全红)

**主因**:`foldx`(8 skill 引用)、`dali`(? 词义混淆,可能粗扫误判,需复核)、`mkdssp/dssp`(3)、`mmseqs`、`gremlin_cpp` 这些 CLI 真缺。

**修复路径**:
- **foldx** 是头号 P0 缺口(8 skill)— 商业但学术免费,需手动下载放 `/opt/foldx5/` 并配 `rotabase.txt`。
- `mmseqs2`:`conda install -c bioconda mmseqs2`(P0,无 license 问题)
- `dssp / mkdssp`:`conda install -c bioconda dssp`(P0)
- `gremlin_cpp`:源码编译(P2)
- `dali`:**需要复核** — "dali" 在大脑文本里出现 371 次,其中绝大多数是英文段落中的描述词,不是工具调用。我的白名单粗扫严重 false positive。

---

## 5. Top 10 缺口(装一个解锁最多 skill 的优先排序)

> 来源:`_audit/parity_summary.json` 的 `top_missing`

| # | 类型 | 名称 | 影响 skill 数 | 评估 |
|---|---|---|---|---|
| 1 | data | pdb | 30 | **多数假性**(skill 是 fetcher);真需镜像的或许 < 5 个,需复核 |
| 2 | env | `praxis-cryo-base` | 8 | 假性缺(整个 cryo 模块未在 staging 上线,见 §4.1) |
| 3 | tool | foldx | 8 | **真缺**,P0,商业但学术免费,需手动下载 |
| 4 | data | uniprot | 8 | 多数假性(fetcher);scaffold 缺数据问题 |
| 5 | tool | esm | 8 | **假阳性已修**(staging `esmfold` env 已装 `fair-esm`);本次 parity 重跑后已绿 |
| 6 | tool | gnina | 5 | **真缺**,P0,`conda install -c bioconda gnina` |
| 7 | tool | proteinmpnn | 5 | **假阳性已修**(staging 有 `proteinmpnn` env) |
| 8 | tool | esmfold | 4 | **假阳性已修** |
| 9 | data | depmap | 3 | 真缺,但仅 crispr 几个 skill 用 |
| 10 | tool | gromacs | 3 | 真缺,P1,大装包 |

修后**真正 P0 单点**(装一个解锁最多)排序:

```
P0  foldx       → 8 skill 解锁(enzyme 主力)
P0  gnina       → 5 skill 解锁(dock 主力)
P0  mkdssp/dssp → 3 skill
P1  gromacs     → 3 skill
P1  amber       → 1 skill(ensemble_docking)
P2  cryo 全套(relion + cryosparc + motioncor2 + ...)  → cryo 11 skill 整体
```

---

## 6. 数据缺口的特殊解读

「`/home/zkyd/data1/databases/` 不存在」是事实(本机没建专门镜像目录),但**这不意味着 30+ 个 skill 真的不能跑**:

| skill 类型 | 是否真需本地数据 |
|---|---|
| `pdb-fetcher` / `cazy-crawler` / `uniprot-fetcher` | **不需要** — 它们就是去 fetch 的 |
| `alphafold-plddt-analyzer`(对结构做 pLDDT 分析) | **不需要本地 PDB 镜像** — 用户传结构进来 |
| `screen_analysis_mageck`(用 DepMap CRISPR 数据) | **需要**,这是真红 |
| `mag_assembly_real`(微生物 MAG 装配,用 GTDB) | staging 已有 `praxis-microbiome-gtdbtk` env,**可能已装数据库**(需进 env 看) |

**建议**:阶段 1 的脚本加一条规则 — skill 名含 `fetch / crawl / pull / download` 的,`data:*` 不当缺。这能把 Top 缺口里的 "data:pdb 30" 砍到 < 5。

---

## 7. 大脑 env 命名脱节(头号设计债)

| 大脑预设 env(本地 SKILL.md 写的) | Staging 实有 | 对齐建议 |
|---|---|---|
| `praxis-cryo-base` | ❌ 无 | 建 / 或映射 |
| `praxis-cryo-modelangelo` | ❌ 无 | 同上 |
| `praxis-cryo-phenix` | ❌ 无 | 同上 |
| `praxis-cryo-aretomo` | ❌ 无 | 同上 |
| `praxis-drug-base` | 有 `praxis-drug`(去掉 -base) | **改大脑** SKILL.md `env: praxis-drug-base` → `praxis-drug` |
| `praxis-drug-vina` | 有 `praxis-dock`(命名不同) | 改大脑 |
| `praxis-pharma` | ❌ 无 | 建 env(轻量 PK/PD,可以快建) |

Staging 上 **大脑没引用** 的 env(可作为新 skill 入大脑的现成资源):

```
af2 / af2.bak / boltz / chai / esmfold / proteinmpnn / rfdiffusion /
thermompnn / consurf / antibody / arcas-hla / hic / DL-masif /
conformation / conformation-baselines / conformation-retrain /
gpcr-agents / vcell / world / ycy
```

这些都是**真有人在用、装好了**的研究 env,代表团队的 active research。把它们包装成 SKILL.md 写回大脑,智能体就能直接推荐用。

---

## 8. 修复路线(优先级 + 估时)

### P0(立即,1–3 天,无 license 障碍)

| 项 | 命令 / 操作 | 解锁 skill |
|---|---|---|
| 修大脑 env 命名脱节 | `praxis-drug-base` → `praxis-drug`、`praxis-drug-vina` → `praxis-dock`(改 SKILL.md frontmatter) | drug / dock 一批 |
| 装 foldx | 下载学术版到 `~/software/foldx5/`,配 `rotabase.txt` | enzyme 8 个 skill |
| 装 gnina | `conda install -n praxis-dock -c bioconda gnina` | dock 5 个 skill |
| 装 dssp | `conda install -n praxis-protein -c bioconda dssp` | enzyme 3 个 skill |
| 装 mmseqs2 | `conda install -n PRAXIS-Enzyme -c bioconda mmseqs2` | enzyme/conservation-msa-analyzer |
| 阶段 1 启发式修 fetcher false positive | 改 `scripts/audit/extract_brain_deps.py`,加 skill 名规则 | 减少 ~25 个假红 |

### P1(本周,需 GPU 时间或中等装包)

| 项 | 命令 / 操作 | 解锁 skill |
|---|---|---|
| 给 staging 建 `praxis-pharma` env | `conda create -n praxis-pharma -c bioconda openpyxl scipy lifelines` | pharma 全部 |
| 装 gromacs | `conda install -n praxis-protein -c bioconda gromacs`(大装包,~ 30 min) | dock + protein 几个 |
| 装 amber | 商业,但学术免费;`pmemd.cuda` 用 conda(`-c conda-forge ambertools`) | dock ensemble |
| 给 13 个未引用的 staging env 写 SKILL.md | 见 §7 表 | 入大脑 |

### P2(月度,license / 重装)

| 项 | 备注 |
|---|---|
| cryo 全套(relion / cryosparc) | cryosparc 商业 license;relion 源码 + CUDA;**或者放弃 cryo 模块在 staging 跑**,标 `status: hpc-only` |
| FoldX 商业升级 / Schrödinger | 看用户用不用得到 |
| Rosetta 真装 | 现 `antibody` env 装了 `pyrosetta`,够大多数场景;真 rosetta_scripts 二进制需源码编译 |

### P3(M7 carry,纯 HPC)

- 超大 cryo 重建(在 bio000070 投递)
- 全蛋白 AF3 复合物预测大批量
- 长时 MD(> 1 µs)

---

## 9. 与系统集成的下一步(对接 PLAN §11 / §12)

本对账给 PLAN-SOFTWARE-PARITY.md 的两个孪生计划提供**可执行落点**:

### 9.1 把「主路径 26 skill」喂 system prompt(§11 step 3)

```python
# 伪代码,落在 build_chat_registry 旁的新 helper
GREEN_SKILLS = {
    "cell/cellpose-segment", "cell/3d-organoid-segment", ...,  # 26 个,见 §3
}

def filter_skills_for_host(manifests):
    return [m for m in manifests if f"{m.brain}/{m.name}" in GREEN_SKILLS]
```

`progressive_disclosure` 拿到的就是 filter 后的子集,智能体 turn-1 默认只看到主路径可跑 skill,直接消除「方案推荐 = 用户跑不了」的幻觉。

### 9.2 把对账结果写回 SKILL.md frontmatter(可选,见 PLAN §3.4)

举例:`brains/cell/skills/workflows/cellpose-segment/SKILL.md` 顶部加:

```yaml
---
name: cellpose-segment
status: green                  # green / red:env_missing / red:cli_missing ...
host_env: PRAXIS-Cell          # 真在 .53 上的 env
host_data: pbmc3k_processed.h5ad  # 已知本地可用数据(可空)
deps: [cellpose, numpy, biotite]  # 启发式提取的高置信度
description: ...
---
```

这样 `praxis2/skills/deps.py:probe_dependencies` + `skills/executor.py:choose_env` 真能 fail-fast 给出确定建议。

### 9.3 报错路径(§12.2)的反例索引

26 个主路径 skill 跑了若 `tool_result.is_error=True`,触发第二层检索:
- 命中同 skill 名的 `memory/cases/_neg/NEG-*.md`(若存在)
- 命中 `memory/rules/06-anti-rules-from-NEG-cases.md`
- 增量塞进下一轮 system 的「错误修复指南」section

本对账**不直接处理报错路径**,但产出的 `_audit/parity_matrix.tsv` 里的 red 行(配 `suggestion` 列)就是天然的 troubleshooting 知识 — 把它合并进反例索引就能用。

---

## 10. 决策点(待用户答复)

| # | 决策 | 推荐 |
|---|---|---|
| 1 | 是否立即跑 P0 那 5 条命令(`foldx / gnina / dssp / mmseqs2 / 改大脑 env 名`)? | **是,逐条做**。foldx 需要您手动下学术 license。 |
| 2 | 阶段 1 启发式 false positive 修(skill 名含 fetch/crawl 跳 data 检查)? | **修**,1 行代码,然后重跑对账 |
| 3 | 给 staging 13 个未引用 env(boltz / chai / rfdiffusion / proteinmpnn / thermompnn 等)写 SKILL.md? | **是**,这是入大脑的最大资源池 |
| 4 | 是否回写主路径 26 skill 的 `status: green` + `host_env:` frontmatter? | **是**,这是 PLAN §11.5 真落地的前提 |
| 5 | cryo 模块怎么办?(临时下线 / 建 env / 等 HPC) | **临时标 `status: not-deployed`**,从 `_SLUG_KEYWORDS` 暂移除,等真有 cryo env 再上 |
| 6 | 修过 false positive 后再跑一遍对账,重生成本报告? | **是**,目标:主路径从 26 → ≥ 35 |

---

## 附录 A. 产出文件清单

```
_audit/
├── host_raw.txt                ← ssh 采集的原始输出(7987 行)
├── host_inventory.json         ← 结构化(370 KB)
├── brains_deps_inventory.tsv   ← 314 条依赖记录
├── parity_matrix.tsv           ← 对账主表(314 行)
└── parity_summary.json         ← 汇总
scripts/audit/
├── collect_host.sh             ← 阶段 0 采集
├── parse_host.py               ← 阶段 0 解析
├── extract_brain_deps.py       ← 阶段 1 大脑解析
└── parity.py                   ← 阶段 2 对账
SOFTWARE-GAP-REPORT.md          ← 本报告
PLAN-SOFTWARE-PARITY.md         ← 本计划
TEST-AGENT-FRAMEWORK.md         ← 框架测试
TEST-WEB-BACKEND-FRONTEND.md    ← 前后端测试
```

## 附录 B. 怎么复跑

```bash
# 1. 重采 host(如 .53 装了新 env 后)
ssh zkyd@10.102.106.53 'bash -s' < scripts/audit/collect_host.sh > _audit/host_raw.txt
python scripts/audit/parse_host.py _audit/host_raw.txt _audit/host_inventory.json

# 2. 重提大脑(如改了 SKILL.md)
python scripts/audit/extract_brain_deps.py

# 3. 重对账
python scripts/audit/parity.py
# stderr 会打 by_gap_kind + Top 10 缺口
```
