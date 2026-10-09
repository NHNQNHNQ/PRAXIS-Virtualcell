# Skill simulate→real 转换指南

> 起草: 2026-05-22
> 参照实现: `brains/dock/skills/workflows/vina_gnina_dock/run.py`
> 适用 51 个 TODO skill,见 `_audit/skill_real_impl_inventory.csv`
> 单 skill 工作量:**5–30 行 real() 函数 + 测试**(典型 15–60 分钟)

---

## 1. 范式(从 vina_gnina_dock 抽出来的)

每个 run.py 长这样:

```python
ARCHETYPE = "<docking|structure_predict|...>"
BRAIN = "<dock|protein|...>"
SKILL = "<vina_gnina_dock|...>"

def simulate(payload):
    """合成数据,不依赖 host_env;原 archetype 模板保留。"""
    ...

def real(payload):
    """真调用 host_env 内的工具,subprocess + 解析输出 → JSON。"""
    # 1. 找工具 binary(确保 conda env 已激活,在 PATH 里)
    # 2. 校验输入(必须的文件/参数存在)
    # 3. subprocess.run(cli_args)
    # 4. 解析输出文件 / stdout
    # 5. 返回符合 SKILL.md output contract 的 JSON

def main():
    payload = read_stdin_or_args()
    out = simulate(payload) if payload.get("simulate") else real(payload)
    json.dump(out, sys.stdout)
```

**关键约束**:
- 失败必须返结构化 `{"ok": False, "error": "..."}`,**不抛 traceback** 到 stdout(SkillExecTool 会 JSONDecodeError)
- 真模式默认开:`payload.get("simulate", False)` — 用户/智能体不显式传就跑真的
- 所有输出必须能 `json.dumps`(numpy 数组先 .tolist())
- 子进程超时设 `payload.get("timeout_s", 600)`

---

## 2. 各 archetype 的 CLI 入口速查

| archetype | 主 CLI 工具 | env | 调用范式 | 解析 |
|---|---|---|---|---|
| **docking** | `gnina --autobox_ligand` (或 vina) | praxis-dock | subprocess + 输出 .sdf.gz | `gzip.open` + `$$$$` 切块 + 找 `> <CNNscore>` |
| **structure_predict** | `boltz predict` / `chai-lab fold` / `esm-fold` / RFdiffusion python API | boltz/chai/esmfold/rfdiffusion | CLI 或 python from torch | 找 `*.pdb` 输出 + parse plddt / pTM |
| **mutation_scan** | `pyrosetta.cartesian_ddg` python API | antibody | python `import pyrosetta` + protocol | 解析 .ddg 输出文件 |
| **omics_scrna** | `cellpose --image_path` / `scanpy.api` | PRAXIS-Cell / praxis-omics | CLI 或 python from anndata/scanpy | 读 `*_seg.npy` (cellpose) / `.h5ad` (scanpy) |
| **microbiome_pipeline** | `kraken2` / `humann` / `metaphlan` | praxis-microbiome-kraken/humann | subprocess 多步管线 | TSV 解析 |
| **mhc_epitope** | `netMHCpan` (需 license) / `mhcflurry` / `optitype` (HLA typing) | praxis-immuno | CLI subprocess | TSV / JSON 解析 |
| **crispr** | `crispor` / `chopchop` / `mageck` | PRAXIS-CRISPR / PRAXIS-CRISPR-crispor | CLI | TSV |
| **drug** | RDKit python API / `admet-ai` | praxis-drug-admet / praxis-drug | python in-process | dict / DataFrame |
| **pharma** | `scipy.integrate.solve_ivp` (PBPK ODE) | praxis-pharma | python in-process | numpy → list |
| **msa_conservation** | `mmseqs2 easy-search` / `foldseek` / `hhblits` | PRAXIS-Enzyme | subprocess | TSV (mmseqs m8 format) |
| **fetcher** | `requests.get` PDB/UniProt API | 任意有 python | python HTTP | JSON / FASTA |

---

## 3. 单 skill 转换步骤(用 vina_gnina_dock 为例)

```bash
# 1. 在 .53 上找工具 + 试跑一次 CLI
ssh zkyd@10.102.106.53
conda activate praxis-dock
gnina --help
# 真试一发(用 /tmp/praxis-test/dock/1iep.pdb 之类)
echo "[done] CLI OK"

# 2. 本地编辑 brains/<brain>/skills/workflows/<skill>/run.py:
#    - 保留 simulate() 不动
#    - 把 real() 从 stub 替换成真 subprocess.run(...)
#    - 解析输出,返回符合 SKILL.md 输出契约的 JSON

# 3. rsync 到 .53
rsync -a brains/<brain>/skills/workflows/<skill>/run.py \
  zkyd@10.102.106.53:/home/zkyd/data1/mzy/praxis2-brains/<brain>/skills/workflows/<skill>/

# 4. 在 .53 上跑一次(stdin JSON)
ssh zkyd@10.102.106.53 '
source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh
conda activate <host_env>
echo "<inputs JSON>" | python /home/zkyd/data1/mzy/praxis2-brains/<brain>/skills/workflows/<skill>/run.py
' | python -m json.tool

# 5. 智能体 E2E 测试(从 Mac 起):
PRAXIS_SKILL_SSH_HOST=zkyd@10.102.106.53 \
PRAXIS_SKILL_REMOTE_BRAINS=/home/zkyd/data1/mzy/praxis2-brains \
PRAXIS_SKILL_CONDA_INIT=/home/zkyd/software/miniconda3/etc/profile.d/conda.sh \
python /tmp/e2e_real_chat.py <agent_spec> '<用户提问>'
```

---

## 4. 51 个 TODO 优先级建议

按 **杠杆**(智能体使用频率 × 上线后被引用次数)和 **工作量**(纯 in-process python ≪ CLI subprocess ≪ 多步管线)排序:

### P0(纯 in-process python,5–15 行)
| skill | brain | archetype | 工具 | 估时 |
|---|---|---|---|---|
| `admet_multi` | drug | drug | RDKit + admet-ai | 15 min |
| `allometric_scale` | pharma | pharma | scipy.curve_fit | 10 min |
| `pbpk_simulate` | pharma | pharma | scipy.integrate.solve_ivp | 20 min |
| `pkpd_emax` | pharma | pharma | scipy | 10 min |
| `ppb_assess` | pharma | pharma | RDKit + 经验公式 | 10 min |
| `cazy-crawler` | enzyme | fetcher | requests.get | 10 min |
| `mhc_class_i_predict` | immuno | mhc_epitope | mhcflurry python API | 15 min |
| `sgrna_design_score` | crispr | crispr | Doench RS2 python | 20 min |

### P1(subprocess CLI 单步,15–30 行)
| skill | brain | archetype | CLI | 估时 |
|---|---|---|---|---|
| `cellpose-segment` | cell | omics_scrna | cellpose CLI | 20 min |
| `3d-organoid-segment` | cell | omics_scrna | cellpose CLI(--Zstack) | 20 min |
| `boltz_structure_predict` | protein | structure_predict | boltz predict | 25 min |
| `chai_complex_predict` | protein | structure_predict | chai-lab fold | 25 min |
| `esmfold_high_throughput` | protein | structure_predict | esmfold python API | 30 min |
| `rfdiffusion_design` | protein | structure_predict | python API | 30 min |
| `proteinmpnn_sequence` | protein | structure_predict | python API | 25 min |
| `hla_typing_rnaseq` | immuno | mhc_epitope | OptiType / arcasHLA | 25 min |
| `tcr_seq_repertoire` | immuno | mhc_epitope | MiXCR | 25 min |
| `covalent_docking` | dock | docking | gnina --covalent_atom | 15 min(模仿 vina_gnina_dock) |
| `redock_benchmark` | dock | docking | gnina + crystal | 20 min(同上) |

### P2(多步管线,30–60 行)
| skill | brain | archetype | 备注 |
|---|---|---|---|
| `scrna_qc_pipeline` | omics | omics_scrna | scanpy 完整管线 |
| `scrna_annotate` | omics | omics_scrna | scanpy + 标记基因 |
| `multimodal_wnn` | omics | omics_scrna | scanpy WNN |
| `shotgun_taxonomy_real` | microbiome | microbiome_pipeline | fastp → bowtie2 → kraken2 → bracken |
| `humann_functional_real` | microbiome | microbiome_pipeline | humann 多步 |
| `mag_assembly_real` | microbiome | microbiome_pipeline | megahit → checkm2 |
| `induced_fit_docking` | dock | docking | gnina + receptor flex |
| `flexpepdock_peptide` | dock | docking | pyrosetta FlexPepDock |
| `tcr_pmhc_dock` | immuno | mhc_epitope | TCRpMHCmodels + gnina |
| `pose_buster_validate` | dock | docking | posebusters python |
| `pyrosetta-stability-scan` real path | enzyme | mutation_scan | 把 simulate 切到真 cartesian_ddg(pyrosetta.init + protocol) |

### P3(需大数据/远程数据库,留 carry)
- `protein_na_docking`(需 RNA force field)
- `snugdock_antibody`(SnugDock)
- `humann_functional` 真数据库(ChocoPhlAn,300+ GB)
- 所有 `_real` 后缀的 microbiome skill(真公开数据集)

---

## 5. 共用 helpers(给 51 个 skill 共享的工具函数)

把以下函数放到 `brains/_common/skills/_helpers.py`(待建),让每个 run.py 顶部 `from _helpers import ...`:

```python
def which(name: str) -> str | None: ...
def run_cli(argv, timeout_s=600, stdin_bytes=None) -> tuple[int, str, str]: ...
def parse_tsv(path: str) -> list[dict]: ...
def prepare_sdf_from_smiles(smiles: str, out_dir: str) -> str: ...
def write_pdb_from_pose(pose, path: str): ...
def safe_json_dump(obj, path: str): ...  # numpy → list 自动转
```

写完后,vina_gnina_dock 的 run.py 可以从 200 行缩到 ~80 行。其余 51 个新写的都按这套调。

---

## 6. 验收清单(每个 skill 真跑完要满足)

- [ ] `python run.py < empty_inputs.json` → 走 simulate 路径,产合理 JSON
- [ ] `python run.py < real_inputs.json` → 走 real,产真 CLI 输出 JSON
- [ ] real 失败时返 `{"ok": false, "error": ...}`,不抛 traceback
- [ ] 输出能被 `json.loads()`(SkillExecTool 严格校验)
- [ ] 通过 SkillExecTool 调,智能体能在下一轮转述结果
- [ ] (可选)接 unit test 把 simulate 路径锁定

---

## 7. 我做了的范本(给后接手参照)

- **`brains/dock/skills/workflows/vina_gnina_dock/run.py`**(reference real impl)
  - 200 行,gnina CLI + RDKit ligand prep + autobox 智能选择 + sdf.gz 解析
  - E2E 验证:1iep + Imatinib → 5 pose / -7.69 kcal/mol / 26.86 秒
  - 智能体真用了它,在 `/chat/stream` 闭环里调起来并转述结果(含 cross-method divergence 提示 + 推荐下一步 skill)

后续 51 个跟着这个模式做即可。
