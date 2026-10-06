# praxis_virtualcell/mdr_gnb/tests/test_mlst_runner.py
"""mlst 输出解析测试(纯逻辑,不真跑 mlst 二进制)。"""
from pathlib import Path

from praxis_virtualcell.mdr_gnb.databases.mlst_runner import parse_mlst_tsv


def test_parse_mlst_tsv_basic(tmp_path: Path):
    tsv = tmp_path / "mlst_out.tsv"
    tsv.write_text(
        "g0.fna\tecoli\t131\tadk(6)\tfumC(4)\tgyrB(8)\ticd(2)\tmdh(15)\tpurA(1)\trecA(3)\n"
        "g1.fna\tecoli\t-\t-\t-\t-\t-\t-\t-\t-\n",
        encoding="utf-8",
    )
    st_map = parse_mlst_tsv(tsv)
    assert st_map["g0"] == "ST131"
    assert st_map["g1"] == "unknown"


def test_parse_mlst_tsv_missing_file():
    # 文件不存在返回空 dict,不抛异常
    assert parse_mlst_tsv(Path("/nonexistent/no.tsv")) == {}


def test_parse_mlst_tsv_empty_file(tmp_path: Path):
    tsv = tmp_path / "empty.tsv"
    tsv.write_text("", encoding="utf-8")
    assert parse_mlst_tsv(tsv) == {}


def test_mlst_cmd_supports_multi_token_prefix(monkeypatch):
    # 回归:53 实测 conda 环境下直接调二进制路径缺 PERL5LIB 报错,
    # 需支持 "conda run -n mdr-bio mlst" 这类多 token 命令前缀
    import importlib

    from praxis_virtualcell.mdr_gnb.databases import mlst_runner
    monkeypatch.setenv("MLST_CMD", "conda run -n mdr-bio mlst")
    importlib.reload(mlst_runner)
    try:
        assert mlst_runner.MLST_CMD == ["conda", "run", "-n", "mdr-bio", "mlst"]
    finally:
        monkeypatch.delenv("MLST_CMD", raising=False)
        importlib.reload(mlst_runner)  # 恢复默认,避免污染后续测试


def test_run_mlst_batch_chunked_parallel(tmp_path, monkeypatch):
    """分块并行:n_chunks 块各起一个 mlst,合并后覆盖全部基因组。mock subprocess.Popen。"""
    import praxis_virtualcell.mdr_gnb.databases.mlst_runner as mr

    fasta_dir = tmp_path / "fasta"
    fasta_dir.mkdir()
    for i in range(10):
        (fasta_dir / f"g{i}.fna").write_text(">s\nACGT\n")

    class FakePopen:
        def __init__(self, cmd, stdout=None):
            # cmd 尾部是该块的 fasta 路径;每个写一行假 mlst 输出到 part 文件
            self._stdout = stdout
            self._fastas = [c for c in cmd if c.endswith(".fna")]

        def wait(self):
            for fa in self._fastas:
                gid = fa.split("/")[-1]
                self._stdout.write(f"{gid}\tecoli\t131\ta\tb\tc\n")
            return 0

    monkeypatch.setattr(mr.subprocess, "Popen", FakePopen)
    out = tmp_path / "mlst_raw.tsv"
    mr.run_mlst_batch(fasta_dir, out, threads=2, n_chunks=3)
    st_map = mr.parse_mlst_tsv(out)
    assert len(st_map) == 10                     # 10 个基因组都在合并结果里
    assert all(v == "ST131" for v in st_map.values())
    # part 文件已清理
    assert not list(out.parent.glob("mlst_raw.part*.tsv"))
