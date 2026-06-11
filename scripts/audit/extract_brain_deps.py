#!/usr/bin/env python3
"""阶段 1: 从 brains/*/skills/workflows/*/SKILL.md 提取「方案 → 软件/包/数据」清单。
输出 _audit/brains_deps_inventory.tsv:
  brain  skill  req_type  name  source  confidence

req_type 枚举: py_pkg / cli / env / data / license / gpu
confidence: high / medium / low (启发式; 留人审)
源策略 (优先级):
  1. frontmatter env: → req=env, name=<env>, high
  2. frontmatter deps: [...] → req=py_pkg, name=<pkg>, high
  3. body python `import X` / `from X` → req=py_pkg, high
  4. body shell `which xxx` → req=cli, high
  5. body shell `conda install -n env pkg` → req=env+py_pkg, high
  6. body shell `pip install pkg` → req=py_pkg, high
  7. 已知工具白名单匹配 + 上下文 (单词边界, 排除标题行) → medium
  8. 数据库/数据集关键词 → req=data, medium
  9. "GPU" / "CUDA" 直说 → req=gpu, medium
排除: markdown 标题行, comment-only 行, 反例段落 ("不要 / NEG / anti-")。
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent.parent / "brains"

# 已知工具白名单 (词边界 + 大小写敏感的形式)
TOOL_WHITELIST = {
    # 蛋白结构 / docking
    "alphafold", "alphafold2", "alphafold3", "colabfold", "esm", "esmfold",
    "rosettafold", "boltz", "foldx", "pymol", "chimerax", "foldseek", "tmalign",
    "dali", "hhblits", "hhsearch", "jackhmmer", "phmmer", "mafft", "muscle",
    "clustalo", "modeller", "dssp", "stride", "rosetta", "pyrosetta",
    "vina", "smina", "gnina", "openbabel", "obabel", "qvina2", "dock6", "ledock",
    "fpocket", "p2rank", "diffdock", "equibind", "rfdiffusion", "ligandmpnn", "proteinmpnn",
    # MD
    "gromacs", "namd", "amber", "openmm", "tinker", "mdanalysis", "mdtraj",
    # cryo-EM
    "relion", "cryosparc", "imod", "motioncor2", "ctffind", "topaz", "cryolo",
    "phenix", "coot", "cryoassess", "model_angelo",
    # 单细胞 / RNA-seq
    "cellpose", "cellprofiler", "scanpy", "anndata", "seurat", "star", "hisat2",
    "salmon", "kallisto", "bowtie2", "bwa", "samtools", "bcftools", "featurecounts",
    "fastqc", "trim_galore", "cutadapt", "picard", "deseq2", "edger",
    "scvi", "scvelo", "scirpy", "cellbender", "harmony",
    # 微生物组
    "qiime", "kraken2", "kraken", "humann", "humann3", "metaphlan", "metaphlan3",
    "spades", "megahit", "prodigal", "checkm", "checkm2", "gtdbtk", "dada2",
    "dram", "drep", "coverm", "bowtie",
    # CRISPR
    "crispor", "rule_set_2", "cas-offinder", "cas-offfinder", "fastp",
    # 药物 / 化学
    "rdkit", "openff", "openfe", "aizynth", "reinvent", "pocket2mol", "moflow",
    "admet-ai", "deepchem", "torchdrug",
    # 通用 / 数据
    "biopython", "biotite", "pandas", "numpy", "scipy", "scikit-learn", "torch",
    "tensorflow", "jax", "matplotlib", "seaborn", "lifelines",
    "snakemake", "nextflow", "singularity", "apptainer", "docker",
    # 数据集
    "hg38", "hg19", "grch38", "afdb", "uniprot", "pdb", "geo", "depmap", "tcga",
    "brunello", "rnacentral", "ensembl", "gencode", "kegg", "go", "interpro",
    "chembl", "drugbank", "pubchem",
}

# 数据集关键词专属
DATA_KEYWORDS = {
    "hg38", "hg19", "grch38", "afdb", "uniprot", "pdb", "geo", "depmap", "tcga",
    "brunello", "rnacentral", "ensembl", "gencode", "kegg", "interpro",
    "chembl", "drugbank", "pubchem",
}

# 反例/禁止段落标识 - 行内有这些则跳过该行
NEG_LINE_MARKERS = (
    "禁用", "禁止", "不要", "anti-rule", "NEG-", "反规则", "反例", "## 失败",
)

# python import 正则:严格锚定行首,避免 "from X import Y" 双匹配把类名 Y 当顶层包
IMPORT_LINE_RE = re.compile(r"^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_.]*)")
# shell which
WHICH_RE = re.compile(r"\bwhich\s+([a-zA-Z0-9_\-\.]+)")
# pip install
PIP_RE = re.compile(r"pip\s+install\s+(?:-[a-zA-Z]\s+\S+\s+)*([a-zA-Z0-9_\-]+(?:[\s,]+[a-zA-Z0-9_\-]+)*)")
# conda install -n env pkgs
CONDA_INSTALL_RE = re.compile(
    r"conda\s+(?:install|create)\s+(?:-[a-zA-Z]\s+\S+\s+)*-n\s+(\S+)\s+([^\n]+)"
)
# frontmatter env
ENV_FRONT_RE = re.compile(r"^env:\s*(\S+)\s*$", re.MULTILINE)
# frontmatter deps
DEPS_FRONT_RE = re.compile(r"^deps:\s*\[(.+?)\]\s*$", re.MULTILINE)
# GPU
GPU_RE = re.compile(r"\b(?:GPU|CUDA|cuDNN|nvidia|A100|V100|H100|RTX)\b", re.IGNORECASE)


def is_code_block_start(line: str) -> bool:
    return line.strip().startswith("```")


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    lines = text.splitlines()
    end = None
    for i, ln in enumerate(lines[1:], start=1):
        if ln.strip() == "---":
            end = i
            break
    if end is None:
        return "", text
    return "\n".join(lines[1:end]), "\n".join(lines[end+1:])


def iter_skill_files() -> Iterator[Path]:
    for p in sorted(ROOT.glob("*/skills/workflows/*/SKILL.md")):
        yield p


def brain_of(p: Path) -> str:
    # brains/<brain>/skills/workflows/<skill>/SKILL.md
    parts = p.relative_to(ROOT).parts
    return parts[0]


def skill_of(p: Path) -> str:
    parts = p.relative_to(ROOT).parts
    return parts[-2]  # 倒数第二个是 skill name


def is_negative_line(line: str) -> bool:
    low = line.strip()
    return any(m in low for m in NEG_LINE_MARKERS)


# 名字含这些词的 skill 是 fetcher / crawler / 远程数据拉取器,本身就是去拉,
# 「需要本地 PDB/UniProt 镜像」是 false positive(见 SOFTWARE-GAP-REPORT §6)
FETCHER_SKILL_NAME_TOKENS = ("fetch", "crawl", "pull", "download", "scrape", "search")


def is_fetcher_skill(skill_name: str) -> bool:
    s = skill_name.lower()
    return any(tok in s for tok in FETCHER_SKILL_NAME_TOKENS)


def extract_python_imports(body: str) -> Iterator[str]:
    """python import 必须在代码块内 (避免误捕 markdown 注释)。"""
    in_code = False
    code_lang: str | None = None
    for line in body.splitlines():
        s = line.rstrip()
        if is_code_block_start(s):
            in_code = not in_code
            if in_code:
                m = re.match(r"^```(\w+)?", s.strip())
                code_lang = (m.group(1) or "").lower() if m else None
            else:
                code_lang = None
            continue
        if not in_code:
            continue
        if code_lang not in (None, "", "python", "py"):
            continue
        m = IMPORT_LINE_RE.match(s)
        if m:
            top = m.group(1).split(".")[0]
            if top and not top.startswith("_"):
                yield top


def extract_shell_calls(body: str) -> Iterator[tuple[str, str]]:
    """yield (kind, name); kind ∈ which|pip|conda_env|conda_pkg。"""
    in_code = False
    code_lang: str | None = None
    for line in body.splitlines():
        s = line.rstrip()
        if is_code_block_start(s):
            in_code = not in_code
            if in_code:
                m = re.match(r"^```(\w+)?", s.strip())
                code_lang = (m.group(1) or "").lower() if m else None
            else:
                code_lang = None
            continue
        if not in_code:
            continue
        if code_lang not in (None, "", "bash", "sh", "shell", "console", "zsh"):
            continue
        if is_negative_line(s):
            continue
        for m in WHICH_RE.finditer(s):
            yield ("which", m.group(1))
        for m in PIP_RE.finditer(s):
            # split 第一项是包 (忽略多 pkg 简化处理)
            first = m.group(1).split()[0].strip(",")
            if first and not first.startswith("-"):
                yield ("pip", first)
        for m in CONDA_INSTALL_RE.finditer(s):
            env_name, pkgs = m.group(1), m.group(2)
            yield ("conda_env", env_name)
            for tok in re.split(r"[\s,]+", pkgs):
                tok = tok.strip()
                if not tok or tok.startswith("-") or tok in ("conda-forge", "bioconda"):
                    continue
                if "=" in tok:
                    tok = tok.split("=", 1)[0]
                if tok:
                    yield ("conda_pkg", tok)


def extract_whitelist_hits(body: str) -> Iterator[tuple[str, str]]:
    """yield (tool, surrounding_snippet); 严格单词边界, 排除反例行 & 标题行。"""
    for line in body.splitlines():
        if is_negative_line(line):
            continue
        if line.lstrip().startswith("#"):  # markdown title
            continue
        low = line.lower()
        for tool in TOOL_WHITELIST:
            # 词边界: 前后非字母/数字
            pat = re.compile(rf"(?<![a-z0-9_]){re.escape(tool)}(?![a-z0-9_])")
            if pat.search(low):
                yield (tool, line.strip()[:80])


# 数据「访问信号」: 出现这些短语才认为 skill 真要本地数据库/镜像; 否则
# 只是把数据格式当输入(用户传 .pdb 文件、声明 uniprot ID 等),不应计为缺口。
# 见 SOFTWARE-GAP-REPORT §6 false positive 分析。
DATA_ACCESS_SIGNALS = (
    "镜像", "mirror", "本地数据库", "local database",
    # 绝对路径下的常见数据库根 (相对路径如 "data/pdb/1abc.pdb" 是例子文件,不算)
    "/data/pdb/", "/data/uniprot/", "/data/afdb/", "/data/databases/", "/databases/",
    "~/data1/databases/", "~/data2/databases/",
    "rsync", "wget ftp", "wget https://ftp.", "ftp://", "ftp.wwpdb",
    "ftp.ncbi", "ftp.ebi", "ftp.uniprot", "ftp.ensembl",
    "download bulk", "bulk download",
    "dataset path", "数据库路径", "database root",
    "需要预先下载", "需事先下载",
)


def body_has_data_access_signal(body: str) -> bool:
    low = body.lower()
    return any(sig in low for sig in DATA_ACCESS_SIGNALS)


def parse_frontmatter_deps(fm: str) -> list[str]:
    m = DEPS_FRONT_RE.search(fm)
    if not m:
        return []
    inner = m.group(1).strip()
    out = []
    for tok in re.split(r"[,\s]+", inner):
        tok = tok.strip().strip("'\"")
        if tok:
            out.append(tok)
    return out


def parse_frontmatter_env(fm: str) -> str | None:
    m = ENV_FRONT_RE.search(fm)
    return m.group(1) if m else None


def main() -> int:
    out_rows: list[tuple] = []  # (brain, skill, type, name, source, confidence)
    files = list(iter_skill_files())
    print(f"扫描 {len(files)} 个 SKILL.md ...", file=sys.stderr)

    for p in files:
        text = p.read_text(errors="ignore")
        fm, body = split_frontmatter(text)
        brain = brain_of(p)
        skill = skill_of(p)

        # 1. frontmatter env
        env = parse_frontmatter_env(fm)
        if env:
            out_rows.append((brain, skill, "env", env, "frontmatter:env", "high"))

        # 2. frontmatter deps
        for dep in parse_frontmatter_deps(fm):
            out_rows.append((brain, skill, "py_pkg", dep.lower(), "frontmatter:deps", "high"))

        # 3. python imports
        py_seen: set[str] = set()
        for top in extract_python_imports(body):
            tl = top.lower()
            if tl in py_seen:
                continue
            py_seen.add(tl)
            out_rows.append((brain, skill, "py_pkg", tl, "body:python_import", "high"))

        # 4-6. shell
        shell_seen: set[tuple[str, str]] = set()
        for kind, name in extract_shell_calls(body):
            key = (kind, name.lower())
            if key in shell_seen:
                continue
            shell_seen.add(key)
            if kind == "which":
                out_rows.append((brain, skill, "cli", name.lower(), "body:which", "high"))
            elif kind == "pip":
                out_rows.append((brain, skill, "py_pkg", name.lower(), "body:pip", "high"))
            elif kind == "conda_env":
                out_rows.append((brain, skill, "env", name, "body:conda_install", "high"))
            elif kind == "conda_pkg":
                out_rows.append((brain, skill, "py_pkg", name.lower(), "body:conda_install", "high"))

        # 7. 白名单 (medium); 同时按 DATA_KEYWORDS 分流到 data
        wl_seen: set[str] = set()
        skill_is_fetcher = is_fetcher_skill(skill)
        skill_has_data_access = body_has_data_access_signal(body)
        for tool, _snip in extract_whitelist_hits(body):
            if tool in wl_seen:
                continue
            wl_seen.add(tool)
            if tool in DATA_KEYWORDS:
                if skill_is_fetcher:
                    # fetcher skill 自己去拉, 不当数据缺口
                    continue
                if not skill_has_data_access:
                    # skill 只是把 PDB/UniProt 当输入格式 ID, 不真的访问本地镜像
                    continue
                out_rows.append((brain, skill, "data", tool, "body:whitelist", "medium"))
            else:
                # 不重复加 python/shell 已有
                already_py = (brain, skill, "py_pkg", tool, "body:python_import", "high") in out_rows
                already_cli = (brain, skill, "cli", tool, "body:which", "high") in out_rows
                if not already_py and not already_cli:
                    out_rows.append((brain, skill, "tool", tool, "body:whitelist", "medium"))

        # 8. GPU
        if GPU_RE.search(body):
            out_rows.append((brain, skill, "gpu", "cuda", "body:keyword", "medium"))

    out_path = Path(__file__).resolve().parent.parent.parent / "_audit" / "brains_deps_inventory.tsv"
    with out_path.open("w") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["brain", "skill", "req_type", "name", "source", "confidence"])
        for row in out_rows:
            w.writerow(row)

    # 摘要
    by_type: dict[str, int] = {}
    for row in out_rows:
        by_type[row[2]] = by_type.get(row[2], 0) + 1
    print(f"→ {out_path}", file=sys.stderr)
    print(f"总条数: {len(out_rows)}", file=sys.stderr)
    print(f"按 type: {by_type}", file=sys.stderr)
    # 涉及 skill 数
    skills_seen = {(r[0], r[1]) for r in out_rows}
    print(f"涉及 (brain,skill) 对: {len(skills_seen)} (总 SKILL.md={len(files)})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
