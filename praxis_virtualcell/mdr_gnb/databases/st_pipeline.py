# praxis_virtualcell/mdr_gnb/databases/st_pipeline.py
"""ST 分型编排:物种 ncbi_amr_phenotypes.tsv → 唯一菌株 → 下 FASTA → 跑 mlst → isolate_st.tsv。

供 evaluators/lineage_split.make_lineage_splits 的 st_map 输入。数据量大时用 max_isolates
先抽子集验证管线通畅,再全量跑(53 后台长任务)。
"""
from __future__ import annotations

import gzip
import shutil
import socket
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .mlst_runner import parse_mlst_tsv, run_mlst_batch
from .ncbi_loader import download_genome_fasta, extract_unique_asm_accs
from .species_registry import get_species


def _gunzip_all(fasta_dir: Path) -> int:
    """把 *.fna.gz 解压为 *.fna(mlst 按 *.fna 匹配)。已存在则跳过。

    截断/损坏的 .fna.gz(下载不完整,断网/超时所致)会抛 EOFError/BadGzipFile——
    捕获后删除损坏的 .gz 与半解压的 .fna 并跳过(不让单个坏文件毁掉整批;
    重跑时 exists-first 会重新下载)。返回损坏跳过的文件数。
    """
    n_bad = 0
    for gz in fasta_dir.glob("*.fna.gz"):
        fna = gz.with_suffix("")  # 去掉 .gz 后缀
        if fna.exists() and fna.stat().st_size > 0:
            continue
        try:
            with gzip.open(gz, "rb") as f_in, fna.open("wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        except (EOFError, OSError, gzip.BadGzipFile, zlib.error) as e:
            print(f"[WARN] {gz.name} 解压失败(损坏/截断,删除跳过):{e}")
            if fna.exists():
                fna.unlink()
            try:
                gz.unlink()
            except OSError:
                pass
            n_bad += 1
    return n_bad


def run_species_st_typing(
    species_key: str, out_root: Path, max_isolates: int | None = None,
    threads: int = 4, download_workers: int = 6, mlst_chunks: int = 1,
) -> dict:
    """对单物种跑 ST 分型全流程,返回统计与产物路径。

    download_workers:并行下载 fasta 的线程数(每个 fasta 需 _list_dir+下载 2 次 HTTP,
    顺序下载 ~10-18/min 太慢;并行数适度即可,过大易触发 NCBI 限速)。已存在文件会跳过。
    """
    # 全局 socket 超时:urlretrieve 无超时参数,断网时连接半开会挂死阻塞整个线程池;
    # 设默认超时后,挂死的下载会超时抛错(计入 n_fail),不阻塞其余(重跑 exists-first 补齐)。
    socket.setdefaulttimeout(60)

    spec = get_species(species_key)
    raw_dir = out_root / "raw" / spec.dir_name
    amr_tsv = raw_dir / "ncbi_amr_phenotypes.tsv"
    if not amr_tsv.exists():
        raise FileNotFoundError(f"未找到 {amr_tsv}(先跑 ncbi_loader.download_species)")

    accs = extract_unique_asm_accs(amr_tsv)
    if max_isolates is not None:
        accs = accs[:max_isolates]

    fasta_dir = raw_dir / "fasta"
    fasta_dir.mkdir(parents=True, exist_ok=True)
    n_ok, n_fail = 0, 0
    with ThreadPoolExecutor(max_workers=max(1, download_workers)) as ex:
        futs = {ex.submit(download_genome_fasta, acc, fasta_dir): acc for acc in accs}
        for fut in as_completed(futs):
            acc = futs[fut]
            try:
                fut.result()
                n_ok += 1
            except Exception as e:  # noqa: BLE001 — 单个菌株下载失败不应中断整批
                print(f"[WARN] {acc} FASTA 下载失败:{e}")
                n_fail += 1

    _gunzip_all(fasta_dir)

    mlst_raw = raw_dir / "mlst_raw.tsv"
    run_mlst_batch(fasta_dir, mlst_raw, threads=threads, n_chunks=mlst_chunks)
    st_map = parse_mlst_tsv(mlst_raw)

    st_tsv = raw_dir / "isolate_st.tsv"
    with st_tsv.open("w", encoding="utf-8") as f:
        f.write("asm_acc\tst\n")
        for acc, st in sorted(st_map.items()):
            f.write(f"{acc}\t{st}\n")

    n_unknown = sum(1 for v in st_map.values() if v == "unknown")
    return {
        "n_accs_requested": len(accs),
        "n_fasta_ok": n_ok,
        "n_fasta_fail": n_fail,
        "n_typed": len(st_map),
        "n_unknown": n_unknown,
        "st_tsv": st_tsv,
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="NCBI 菌株 ST 分型编排")
    ap.add_argument("--species", required=True, help="dir_name/学名/别名")
    ap.add_argument("--out-root", required=True, type=Path, help="data/mdr_gnb 根")
    ap.add_argument("--max-isolates", type=int, default=None, help="先跑子集验证用")
    ap.add_argument("--threads", type=int, default=4, help="每个 mlst 进程的线程数")
    ap.add_argument("--download-workers", type=int, default=6, help="并行下载 fasta 线程数")
    ap.add_argument("--mlst-chunks", type=int, default=1, help="mlst 分块并行数(53 有 144 核,大库用 12)")
    a = ap.parse_args()
    r = run_species_st_typing(
        a.species, a.out_root, a.max_isolates, a.threads, a.download_workers, a.mlst_chunks,
    )
    print(
        f"[OK] {a.species}: 请求={r['n_accs_requested']} "
        f"下载成功={r['n_fasta_ok']} 下载失败={r['n_fasta_fail']} "
        f"分型={r['n_typed']}(unknown={r['n_unknown']}) → {r['st_tsv']}"
    )
