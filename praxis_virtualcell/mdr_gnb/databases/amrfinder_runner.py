"""NCBI AMRFinderPlus 运行/解析(版本冻结,供规则基线与特征;53 conda env mdrtools)。

run_amrfinder:对基因组跑 AMRFinderPlus → 解析 TSV → 输出对齐训练用的 ncbi_amr_genotypes 格式
(gene 名 + 点突变 `<sym>=POINT`),使「新基因组 → AMRFinder → parse_genotypes → 模型」闭环。
解析与运行分离:parse_amrfinder_tsv 纯函数可离线单测;run_amrfinder 调工具(需装 amrfinder)。
"""
from __future__ import annotations

import csv
import subprocess
import tempfile
from pathlib import Path

# 物种 → AMRFinderPlus --organism 值(启用点突变检测);未列出的物种不传 --organism。
_ORGANISM = {
    "escherichia_coli": "Escherichia",
    "klebsiella_pneumoniae": "Klebsiella_pneumoniae",
    "acinetobacter_baumannii": "Acinetobacter_baumannii",
    "pseudomonas_aeruginosa": "Pseudomonas_aeruginosa",
    "salmonella_enterica": "Salmonella",
    "enterobacter_cloacae": "Enterobacter_cloacae",
    "serratia_marcescens": "Serratia_marcescens",
}


def _col(row: dict, *names: str) -> str:
    """按候选列名(大小写/空格无关)取值,兼容 AMRFinderPlus 各版本表头。"""
    low = {k.strip().lower(): k for k in row}
    for n in names:
        k = low.get(n.strip().lower())
        if k is not None:
            return (row.get(k) or "").strip()
    return ""


def parse_amrfinder_tsv(text: str) -> dict:
    """AMRFinderPlus TSV 文本 → {genes, mutations, ncbi_amr_genotypes, n_hits}(纯函数,可离线测)。"""
    genes, muts, n = [], [], 0
    for row in csv.DictReader(text.splitlines(), delimiter="\t"):
        n += 1
        sym = _col(row, "Gene symbol", "Element symbol", "Element name")
        if not sym:
            continue
        # AMRFinderPlus v4:点突变在 **Element subtype**=POINT(Element type=AMR);兼容旧版 Element type=POINT
        is_point = any("POINT" in _col(row, c).upper()
                       for c in ("Element subtype", "Subtype", "Element type", "Type"))
        if is_point:
            muts.append(f"{sym}=POINT" if not sym.endswith("=POINT") else sym)
        else:
            genes.append(sym)
    genes, muts = sorted(set(genes)), sorted(set(muts))
    return {"genes": genes, "mutations": muts,
            "ncbi_amr_genotypes": ",".join(genes + muts), "n_hits": n}


def run_amrfinder(genome_path: str, db_version: str, *, species: str | None = None,
                  amrfinder_bin: str = "amrfinder", extra_args=()) -> dict:
    """对 nucleotide FASTA 跑 AMRFinderPlus(--plus,物种匹配则 --organism 启点突变)→ 解析。
    需装 amrfinder;结果附 db_version(冻结锁)。"""
    with tempfile.NamedTemporaryFile("w+", suffix=".tsv", delete=False) as tf:
        out = tf.name
    cmd = [amrfinder_bin, "-n", str(genome_path), "-o", out, "--plus"]
    org = _ORGANISM.get((species or "").lower())
    if org:
        cmd += ["--organism", org]
    cmd += list(extra_args)
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        parsed = parse_amrfinder_tsv(Path(out).read_text(encoding="utf-8"))
    finally:
        Path(out).unlink(missing_ok=True)
    parsed["db_version"] = db_version
    parsed["organism"] = org
    return parsed
