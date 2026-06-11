"""praxis2.mcp.servers.dock_server 单元测试。

纯逻辑工具(define_box/parse_gnina/write/get/prepare_receptor)真测;
run_dock mock subprocess;prepare_ligand 需 rdkit(importorskip)。
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def dmod(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_DOCK_WORK_ROOT", str(tmp_path))
    import importlib
    import praxis2.mcp.servers.dock_server as m
    importlib.reload(m)
    return m, tmp_path


# ---- write_file / get_file(复用 gmx 模式) ----

def test_write_get_file(dmod):
    m, root = dmod
    r = m.write_file_impl("job/rec.pdb", "ATOM line\n")
    assert r["ok"] is True
    assert (root / "job" / "rec.pdb").read_text() == "ATOM line\n"
    g = m.get_file_impl("job/rec.pdb")
    assert "ATOM line" in g["content"]


def test_write_file_traversal_blocked(dmod):
    m, _ = dmod
    with pytest.raises(ValueError, match="越界"):
        m.write_file_impl("../../etc/x", "evil")


# ---- prepare_receptor(去水) ----

def test_prepare_receptor_strips_water(dmod):
    m, root = dmod
    pdb = ("ATOM      1  N   ALA A   1      11.0  12.0  13.0\n"
           "HETATM    2  O   HOH A 100      20.0  20.0  20.0\n"
           "HETATM    3  C1  STI A 201      15.0  16.0  17.0\n")
    (root / "rec.pdb").write_text(pdb)
    r = m.prepare_receptor_impl("rec.pdb", "rec_clean.pdb")
    assert r["ok"] is True
    out = (root / "rec_clean.pdb").read_text()
    assert "HOH" not in out          # 水被去掉
    assert "ALA" in out              # 蛋白保留
    assert "STI" in out              # 非水 HETATM(配体)保留


# ---- define_box(从共晶配体 resname 算 center/size) ----

def _atom(rec, serial, name, res, seq, x, y, z, chain="A"):
    """构造标准 PDB 固定列行(x/y/z 在 0-indexed 30:38/38:46/46:54)。"""
    return (f"{rec:<6}{serial:>5} {name:<4} {res:>3} {chain}{seq:>4}    "
            f"{x:>8.3f}{y:>8.3f}{z:>8.3f}\n")


def test_define_box_from_ligand_resname(dmod):
    m, root = dmod
    # STI 配体两个原子,中心 = (15,15,15),bounding 10
    pdb = (_atom("ATOM", 1, "N", "ALA", 1, 0.0, 0.0, 0.0)
           + _atom("HETATM", 2, "C1", "STI", 201, 10.0, 10.0, 10.0)
           + _atom("HETATM", 3, "C2", "STI", 201, 20.0, 20.0, 20.0))
    (root / "rec.pdb").write_text(pdb)
    r = m.define_box_impl("rec.pdb", ligand_resname="STI", padding=4.0)
    assert r["ok"] is True
    assert r["center"] == [15.0, 15.0, 15.0]
    # size = (20-10) + 2*4 = 18 per axis
    assert r["size"] == [18.0, 18.0, 18.0]


def test_define_box_resname_not_found(dmod):
    m, root = dmod
    (root / "rec.pdb").write_text(_atom("ATOM", 1, "N", "ALA", 1, 0.0, 0.0, 0.0))
    r = m.define_box_impl("rec.pdb", ligand_resname="ZZZ")
    assert r["ok"] is False


# ---- _parse_gnina_sdf(解析 pose 分数) ----

def test_parse_gnina_sdf(dmod, tmp_path):
    m, _ = dmod
    sdf = (
        "mol1\n\n\n  0  0\nM  END\n"
        "> <minimizedAffinity>\n-9.5\n\n"
        "> <CNNaffinity>\n6.2\n\n$$$$\n"
        "mol2\n\n\n  0  0\nM  END\n"
        "> <minimizedAffinity>\n-8.1\n\n"
        "> <CNNaffinity>\n5.5\n\n$$$$\n"
    )
    p = tmp_path / "docked.sdf"
    p.write_text(sdf)
    poses = m._parse_gnina_sdf(str(p))
    assert len(poses) == 2
    assert poses[0]["minimizedAffinity"] == -9.5
    assert poses[0]["CNNaffinity"] == 6.2


# ---- run_dock(mock gnina subprocess) ----

def test_run_dock_mocked(dmod, tmp_path):
    m, root = dmod
    (root / "rec.pdb").write_text("ATOM      1  N   ALA A   1   0 0 0\n")
    (root / "lig.sdf").write_text("ligand\n")
    sdf_out = (
        "m\n\n\n  0  0\nM  END\n> <minimizedAffinity>\n-9.0\n\n"
        "> <CNNaffinity>\n6.0\n\n$$$$\n"
    )

    class _P:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, **kw):
        # gnina 写出 docked.sdf.gz → 用纯文本 .sdf 模拟(parse 支持非 gz)
        out_idx = cmd.index("-o") + 1
        outp = cmd[out_idx].replace(".sdf.gz", ".sdf")
        open(outp, "w").write(sdf_out)
        return _P()

    with patch.object(m, "_which", return_value="/usr/bin/gnina"), \
         patch.object(m.subprocess, "run", side_effect=_fake_run):
        r = m.run_dock_impl("rec.pdb", "lig.sdf",
                            center=[10, 10, 10], size=[20, 20, 20])
    assert r["ok"] is True
    assert r["best_affinity"] == -9.0
    assert len(r["poses"]) == 1


def test_run_dock_no_gnina(dmod):
    m, _ = dmod
    with patch.object(m, "_which", return_value=None):
        r = m.run_dock_impl("rec.pdb", "lig.sdf", center=[0, 0, 0], size=[10, 10, 10])
    assert r["ok"] is False
    assert "gnina" in r["error"].lower()


# ---- prepare_ligand(需 rdkit) ----

def test_prepare_ligand_smiles(dmod):
    pytest.importorskip("rdkit")
    m, root = dmod
    r = m.prepare_ligand_impl("CCO", "ethanol.sdf")  # ethanol
    assert r["ok"] is True
    assert (root / "ethanol.sdf").exists()
    assert "V2000" in (root / "ethanol.sdf").read_text() or r["sdf_path"]
