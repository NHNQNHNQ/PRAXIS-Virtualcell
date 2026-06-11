"""MCP stdio server — 分子对接交互式工具(gnina,praxis-dock env)。

让 agent 交互式做对接探索:准备受体/配体 → 定义 box → gnina 对接 → 看 affinity →
调参重对接。复用 dock 学科 skill 的已验证逻辑(RDKit 配体 embed / gnina 命令 /
pose 解析)。gnina 直接接受 pdb 受体 + sdf 配体(不需 pdbqt/meeko)。

启动(praxis-dock env,有 gnina/rdkit/obabel):
  python -m praxis2.mcp.servers.dock_server

6 个 tool:
  write_file        — 写受体 pdb / 输入文件
  prepare_receptor  — 去水清理受体 → clean pdb
  prepare_ligand    — RDKit SMILES → 3D embed → sdf
  define_box        — 从共晶配体 resname / 残基算 box center+size
  run_dock          — gnina 对接(CNN rescoring),返 poses + best_affinity
  get_file          — 取结果文件

纯逻辑 _impl 不依赖 mcp,可单测。
"""
from __future__ import annotations

import gzip
import os
import shutil
import subprocess
from pathlib import Path

_SAFE_ROOT = Path(os.environ.get("PRAXIS_DOCK_WORK_ROOT", "/home/zkyd/praxis-dock-mcp"))


def _safe_path(p: str) -> Path:
    resolved = (_SAFE_ROOT / p).resolve()
    if not str(resolved).startswith(str(_SAFE_ROOT)):
        raise ValueError(f"路径越界: {p!r} 不在 {_SAFE_ROOT}")
    return resolved


def _which(binary: str) -> str | None:
    return shutil.which(binary)


# ---- write_file / get_file ----

def write_file_impl(path: str, content: str) -> dict:
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(target)}


def get_file_impl(path: str, max_bytes: int = 8192) -> dict:
    target = _safe_path(path)
    if not target.exists():
        return {"content": "", "size": 0, "truncated": False, "error": "file not found"}
    size = target.stat().st_size
    if size <= max_bytes:
        return {"content": target.read_text(errors="replace"), "size": size, "truncated": False}
    with target.open("rb") as f:
        f.seek(-max_bytes, 2)
        raw = f.read(max_bytes)
    return {"content": raw.decode("utf-8", errors="replace"), "size": size, "truncated": True}


# ---- prepare_receptor(去水清理) ----

def prepare_receptor_impl(pdb_path: str, out_name: str, keep_water: bool = False) -> dict:
    src = _safe_path(pdb_path)
    if not src.exists():
        return {"ok": False, "error": f"受体 pdb 不存在: {pdb_path}"}
    out = _safe_path(out_name)
    kept = []
    for ln in src.read_text(errors="replace").splitlines(keepends=True):
        if ln.startswith(("ATOM", "HETATM")):
            resname = ln[17:20].strip()
            if not keep_water and resname in ("HOH", "WAT"):
                continue
        kept.append(ln)
    out.write_text("".join(kept), encoding="utf-8")
    return {"ok": True, "clean_pdb": str(out), "n_lines": len(kept)}


# ---- prepare_ligand(RDKit SMILES → sdf) ----

def prepare_ligand_impl(smiles: str, out_name: str) -> dict:
    out = _safe_path(out_name)
    try:
        from rdkit import Chem  # noqa: PLC0415
        from rdkit.Chem import AllChem  # noqa: PLC0415
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"ok": False, "error": f"RDKit 无法解析 SMILES: {smiles!r}"}
        mol = Chem.AddHs(mol)
        if AllChem.EmbedMolecule(mol, randomSeed=42) != 0:
            return {"ok": False, "error": "RDKit EmbedMolecule 失败(构象生成)"}
        AllChem.MMFFOptimizeMolecule(mol, maxIters=200)
        w = Chem.SDWriter(str(out))
        w.write(mol)
        w.close()
        return {"ok": True, "sdf_path": str(out), "n_atoms": mol.GetNumAtoms()}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


# ---- define_box(从配体 resname / 残基算 box) ----

def _atom_coords(pdb_text: str, *, resname: str | None, residue_ids: list | None) -> list:
    coords = []
    rid_set = {str(r) for r in (residue_ids or [])}
    for ln in pdb_text.splitlines():
        if not ln.startswith(("ATOM", "HETATM")):
            continue
        if resname is not None and ln[17:20].strip() != resname:
            continue
        if residue_ids and ln[22:26].strip() not in rid_set:
            continue
        try:
            coords.append((float(ln[30:38]), float(ln[38:46]), float(ln[46:54])))
        except ValueError:
            continue
    return coords


def define_box_impl(receptor_pdb: str, ligand_resname: str | None = None,
                    residue_ids: list | None = None, padding: float = 5.0) -> dict:
    src = _safe_path(receptor_pdb)
    if not src.exists():
        return {"ok": False, "error": f"受体 pdb 不存在: {receptor_pdb}"}
    if not ligand_resname and not residue_ids:
        return {"ok": False, "error": "需提供 ligand_resname 或 residue_ids 之一"}
    coords = _atom_coords(src.read_text(errors="replace"),
                          resname=ligand_resname, residue_ids=residue_ids)
    if not coords:
        return {"ok": False, "error": "未找到匹配原子(resname/residue_ids 不存在?)"}
    xs, ys, zs = zip(*coords, strict=True)
    center = [round((min(a) + max(a)) / 2, 3) for a in (xs, ys, zs)]
    size = [round((max(a) - min(a)) + 2 * padding, 3) for a in (xs, ys, zs)]
    return {"ok": True, "center": center, "size": size, "n_atoms": len(coords)}


# ---- gnina pose 解析(复用 dock skill) ----

def _parse_gnina_sdf(sdf_path: str) -> list:
    opener = gzip.open if sdf_path.endswith(".gz") else open
    with opener(sdf_path, "rt", encoding="utf-8", errors="replace") as f:
        text = f.read()
    poses = []
    rank = 0
    for blk in text.split("$$$$"):
        if not blk.strip():
            continue
        rank += 1
        pose = {"rank": rank}
        for prop in ("minimizedAffinity", "CNNscore", "CNNaffinity", "CNN_VS"):
            tag = f"> <{prop}>"
            idx = blk.find(tag)
            if idx == -1:
                continue
            vs = blk.find("\n", idx) + 1
            ve = blk.find("\n", vs)
            try:
                pose[prop] = float(blk[vs:ve].strip())
            except ValueError:
                pose[prop] = blk[vs:ve].strip()
        poses.append(pose)
    return poses


# ---- run_dock(gnina) ----

def run_dock_impl(receptor_pdb: str, ligand_sdf: str, center: list, size: list,
                  cnn_scoring: str = "rescore", num_modes: int = 9,
                  exhaustiveness: int = 8, seed: int = 42, timeout_s: int = 600) -> dict:
    gnina = _which("gnina")
    if gnina is None:
        return {"ok": False, "error": "gnina 未在 PATH(应在 praxis-dock env 跑此 server)"}
    rec = _safe_path(receptor_pdb)
    lig = _safe_path(ligand_sdf)
    if not rec.exists() or not lig.exists():
        return {"ok": False, "error": "受体或配体文件不存在"}
    out_sdf = str(rec.parent / "docked.sdf")
    cmd = [
        gnina, "--receptor", str(rec), "--ligand", str(lig),
        "--center_x", str(center[0]), "--center_y", str(center[1]), "--center_z", str(center[2]),
        "--size_x", str(size[0]), "--size_y", str(size[1]), "--size_z", str(size[2]),
        "--num_modes", str(num_modes), "--exhaustiveness", str(exhaustiveness),
        "--seed", str(seed), "-o", out_sdf, "--cnn_scoring", cnn_scoring,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"gnina 超时(>{timeout_s}s)"}
    if proc.returncode != 0:
        return {"ok": False, "error": f"gnina 失败 rc={proc.returncode}",
                "stderr": proc.stderr[-600:]}
    if not os.path.isfile(out_sdf):
        return {"ok": False, "error": "gnina 未产出 docked.sdf"}
    poses = _parse_gnina_sdf(out_sdf)
    if not poses:
        return {"ok": False, "error": "未解析到 pose"}
    poses.sort(key=lambda p: -(p.get("CNNaffinity") or p.get("CNNscore") or 0))
    best = poses[0].get("minimizedAffinity")
    return {"ok": True, "poses": poses, "best_affinity": best,
            "n_poses": len(poses), "out_sdf": out_sdf}


# ---- MCP 绑定(仅 __main__) ----

if __name__ == "__main__":
    from mcp.server.fastmcp import FastMCP  # noqa: PLC0415

    mcp = FastMCP("praxis-dock")

    @mcp.tool()
    def write_file(path: str, content: str) -> dict:
        """写受体 pdb / 输入文件到 SAFE_ROOT。"""
        return write_file_impl(path, content)

    @mcp.tool()
    def prepare_receptor(pdb_path: str, out_name: str, keep_water: bool = False) -> dict:
        """去水清理受体 pdb → clean pdb(gnina 直接接受 pdb,无需 pdbqt)。"""
        return prepare_receptor_impl(pdb_path, out_name, keep_water)

    @mcp.tool()
    def prepare_ligand(smiles: str, out_name: str) -> dict:
        """RDKit 把 SMILES 转 3D 构象 sdf(embed+MMFF 优化),供 gnina 对接。"""
        return prepare_ligand_impl(smiles, out_name)

    @mcp.tool()
    def define_box(receptor_pdb: str, ligand_resname: str = "", residue_ids: list | None = None,
                   padding: float = 5.0) -> dict:
        """从共晶配体 resname 或结合位点 residue_ids 算对接 box 的 center+size。
        对接最关键一步:定位结合口袋。传共晶配体的 3 字母 resname(如 STI)最方便。"""
        return define_box_impl(receptor_pdb, ligand_resname or None, residue_ids, padding)

    @mcp.tool()
    def run_dock(receptor_pdb: str, ligand_sdf: str, center: list, size: list,
                 cnn_scoring: str = "rescore", num_modes: int = 9,
                 exhaustiveness: int = 8) -> dict:
        """gnina 对接(CNN rescoring),返 poses(亲和力/CNN分数)+ best_affinity。
        看 best_affinity 不满意可调 center/size/exhaustiveness 重对接。
        cnn_scoring=rescore(默认,准)|none(避 CUDA 问题,快)。"""
        return run_dock_impl(receptor_pdb, ligand_sdf, center, size,
                             cnn_scoring, num_modes, exhaustiveness)

    @mcp.tool()
    def get_file(path: str, max_bytes: int = 8192) -> dict:
        """读结果文件(docked.sdf / 日志)末尾内容。"""
        return get_file_impl(path, max_bytes)

    mcp.run("stdio")
