"""CARD/RGI 数据加载(公开耐药决定子本体;D3;53 conda env mdrtools)。

RGI(Resistance Gene Identifier)对基因组注释 CARD 本体 → ARO 命中 + drug class + 机制。
解析与运行分离:parse_rgi_txt 纯函数可离线单测;run_rgi/load_card 需装 rgi。
用途:G2R 特征增强(CARD ARO family / mechanism 作补充特征,与 AMRFinder 互补)。
"""
from __future__ import annotations

import csv
import subprocess
import tempfile
from pathlib import Path


def _col(row: dict, *names: str) -> str:
    low = {k.strip().lower(): k for k in row}
    for n in names:
        k = low.get(n.strip().lower())
        if k is not None:
            return (row.get(k) or "").strip()
    return ""


def parse_rgi_txt(text: str) -> dict:
    """RGI main 的 .txt(tab)输出 → {aro_hits, drug_classes, mechanisms, n_hits}(纯函数)。"""
    aros, classes, mechs, n = [], [], [], 0
    for row in csv.DictReader(text.splitlines(), delimiter="\t"):
        n += 1
        aro = _col(row, "Best_Hit_ARO", "ARO")
        if aro:
            aros.append(aro)
        dc = _col(row, "Drug Class")
        classes.extend(c.strip() for c in dc.split(";") if c.strip())
        m = _col(row, "Resistance Mechanism")
        if m:
            mechs.append(m)
    return {"aro_hits": sorted(set(aros)), "drug_classes": sorted(set(classes)),
            "mechanisms": sorted(set(mechs)), "n_hits": n}


def load_card(path: str) -> dict:
    """加载 RGI 结果文件(.txt)为标准化结构。"""
    return parse_rgi_txt(Path(path).read_text(encoding="utf-8"))


def run_rgi(genome_path: str, *, rgi_bin: str = "rgi", threads: int = 4, extra_args=()) -> dict:
    """对 contig FASTA 跑 RGI main → 解析 CARD 注释。需装 rgi + rgi load 过 CARD DB。"""
    with tempfile.TemporaryDirectory() as td:
        out_prefix = str(Path(td) / "rgi_out")
        cmd = [rgi_bin, "main", "-i", str(genome_path), "-o", out_prefix,
               "--input_type", "contig", "-n", str(threads), "--clean", *extra_args]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return parse_rgi_txt(Path(out_prefix + ".txt").read_text(encoding="utf-8"))
