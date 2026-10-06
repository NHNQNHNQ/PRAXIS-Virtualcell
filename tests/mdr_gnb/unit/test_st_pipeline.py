"""st_pipeline 并行下载编排测试(mock 网络/mlst,不联网)。

验证:并行下载 fasta 时成功/失败计数正确、单个失败不中断整批。
"""
import csv
from pathlib import Path

import praxis_virtualcell.mdr_gnb.databases.st_pipeline as stp


def _write_amr(tmp_path: Path, accs) -> Path:
    raw = tmp_path / "raw" / "escherichia_coli"
    raw.mkdir(parents=True)
    p = raw / "ncbi_amr_phenotypes.tsv"
    with p.open("w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["genome_id", "antibiotic", "resistant_phenotype"])
        for a in accs:
            w.writerow([a, "meropenem", "R"])
    return raw


def test_parallel_download_counts_ok_and_fail(tmp_path, monkeypatch):
    accs = [f"GCA_00000{i}.1" for i in range(6)]
    _write_amr(tmp_path, accs)

    def fake_download(acc, dest_dir):
        if acc.endswith("3.1"):
            raise RuntimeError("boom")  # 模拟单个下载失败
        return Path(dest_dir) / f"{acc}.fna.gz"

    monkeypatch.setattr(stp, "download_genome_fasta", fake_download)
    monkeypatch.setattr(stp, "_gunzip_all", lambda d: None)
    monkeypatch.setattr(stp, "run_mlst_batch", lambda fasta_dir, out, threads=4, n_chunks=1: out)
    monkeypatch.setattr(
        stp, "parse_mlst_tsv",
        lambda p: {a: "ST1" for a in accs if not a.endswith("3.1")},
    )

    r = stp.run_species_st_typing("escherichia_coli", tmp_path, download_workers=4)
    assert r["n_accs_requested"] == 6
    assert r["n_fasta_ok"] == 5
    assert r["n_fasta_fail"] == 1
    assert r["n_typed"] == 5


def test_gunzip_skips_corrupt_gz(tmp_path):
    """截断/损坏的 .fna.gz 应被删除跳过,不崩溃;好文件正常解压。"""
    import gzip
    fasta = tmp_path / "fasta"
    fasta.mkdir()
    # 好文件
    good = fasta / "GCA_good.fna.gz"
    with gzip.open(good, "wb") as f:
        f.write(b">seq1\nACGT\n")
    # 损坏文件(写入非法 gzip 字节,截断)
    bad = fasta / "GCA_bad.fna.gz"
    bad.write_bytes(b"\x1f\x8b\x08\x00truncated-garbage")
    n_bad = stp._gunzip_all(fasta)
    assert n_bad == 1
    assert (fasta / "GCA_good.fna").exists()   # 好的解压成功
    assert not bad.exists()                     # 坏的被删除
    assert not (fasta / "GCA_bad.fna").exists() # 半解压产物也删除
