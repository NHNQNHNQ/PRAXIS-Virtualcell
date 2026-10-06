# praxis_virtualcell/mdr_gnb/databases/mlst_runner.py
"""对基因组批量跑 mlst(Torsten Seemann),产出 genome_id→ST 映射。

mlst 自动按 PubMLST scheme 判型;输出 TSV:FILE, SCHEME, ST, allele...
ST 为 '-' 或 'unknown' 的记为 'unknown'(下游单列不混入分组)。

**mlst 依赖 Perl 环境(PERL5LIB 等)**:若装在 conda 环境,直接调二进制路径会缺失
conda 激活时设置的环境变量而报 "Can't locate List/MoreUtils.pm"(实测于 53)。
MLST_CMD 支持多 token 命令前缀,如 "conda run -n mdr-bio mlst",以正确带上环境。
"""
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

# 支持多 token 命令前缀(如 "conda run -n mdr-bio mlst"),默认假设 PATH 里直接有 mlst
MLST_CMD: list[str] = shlex.split(os.environ.get("MLST_CMD", "mlst"))


def run_mlst_batch(fasta_dir: Path, out_tsv: Path, threads: int = 4, n_chunks: int = 1) -> Path:
    """对 fasta_dir 下所有 *.fna 跑 mlst,汇总到单个 out_tsv。

    mlst 逐个基因组串行处理,单进程对上万基因组极慢(threads 仅并行单基因组的 blast)。
    n_chunks>1 时把 fasta 轮询分成 n_chunks 块、并行起 n_chunks 个 mlst 进程(各 threads 线程),
    跨基因组并行,再合并各块输出(行序无关,parse_mlst_tsv 建 dict)。53 有 144 核,可开大 n_chunks。
    """
    out_tsv.parent.mkdir(parents=True, exist_ok=True)
    fastas = sorted(str(p) for p in fasta_dir.glob("*.fna"))
    if not fastas:
        out_tsv.write_text("", encoding="utf-8")
        return out_tsv

    if n_chunks <= 1 or len(fastas) <= n_chunks:
        with out_tsv.open("w", encoding="utf-8") as f:
            cmd = [*MLST_CMD, "--quiet", "--threads", str(threads), *fastas]
            subprocess.run(cmd, check=True, stdout=f)
        return out_tsv

    # 轮询分块(均衡各块大小),并行起多个 mlst,各写自己的 part 文件
    chunks = [fastas[i::n_chunks] for i in range(n_chunks)]
    procs, parts = [], []
    for i, chunk in enumerate(chunks):
        if not chunk:
            continue
        pf = out_tsv.parent / f"{out_tsv.stem}.part{i}.tsv"
        fh = pf.open("w", encoding="utf-8")
        cmd = [*MLST_CMD, "--quiet", "--threads", str(threads), *chunk]
        procs.append((subprocess.Popen(cmd, stdout=fh), fh, pf))
        parts.append(pf)

    errs = []
    for p, fh, pf in procs:
        rc = p.wait()
        fh.close()
        if rc != 0:
            errs.append((pf.name, rc))

    # 合并各块(串接即可,行序对 parse 无影响)
    with out_tsv.open("w", encoding="utf-8") as out:
        for pf in parts:
            if pf.exists():
                out.write(pf.read_text(encoding="utf-8"))
                pf.unlink()
    if errs:
        raise RuntimeError(f"mlst 分块失败:{errs}")
    return out_tsv


def parse_mlst_tsv(out_tsv: Path) -> dict[str, str]:
    """解析 mlst 输出为 genome_id→ST。genome_id 取 FILE 列去扩展名。"""
    st_map: dict[str, str] = {}
    if not out_tsv.exists():
        return st_map
    for line in out_tsv.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cols = line.split("\t")
        if len(cols) < 3:
            continue
        genome_id = Path(cols[0]).stem
        st = cols[2].strip()
        if st in ("", "-", "0"):
            st = "unknown"
        st_map[genome_id] = f"ST{st}" if st != "unknown" and not st.startswith("ST") else st
    return st_map


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="mlst 批量分型")
    ap.add_argument("--fasta-dir", required=True, type=Path)
    ap.add_argument("--out-tsv", required=True, type=Path)
    ap.add_argument("--threads", type=int, default=8)
    a = ap.parse_args()
    p = run_mlst_batch(a.fasta_dir, a.out_tsv, a.threads)
    st_map = parse_mlst_tsv(p)
    n_unknown = sum(1 for v in st_map.values() if v == "unknown")
    print(f"[OK] mlst: {len(st_map)} 基因组分型;unknown={n_unknown} → {p}")
