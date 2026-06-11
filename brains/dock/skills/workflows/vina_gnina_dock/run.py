#!/usr/bin/env python3
"""dock/vina_gnina_dock — real implementation (gnina v1.3.2 + RDKit prep)。

simulate 模式保留(向后兼容);默认走 real 路径:
  receptor_pdb + (ligand_smiles | ligand_sdf) → gnina --autobox_ligand → poses
  → 解析 sdf.gz 拿每 pose 的 CNN_score / CNNaffinity / Vinardo

输入契约(stdin JSON):
  {
    "receptor_pdb": "/path/to/receptor.pdb",
    "ligand_smiles": "CCO" | null,
    "ligand_sdf":    "/path/to/lig.sdf" | null,
    "num_modes":     9,
    "exhaustiveness": 8,
    "seed":          42,
    "simulate":      false,
    "out_dir":       "/tmp/vina_gnina_<tid>"
  }

输出 stdout JSON:符合 SKILL.md output contract(vina + gnina pose 表)。
"""
from __future__ import annotations

import gzip
import json
import os
import random
import subprocess
import sys
import tempfile
import time

ARCHETYPE = "docking"
BRAIN = "dock"
SKILL = "vina_gnina_dock"


def simulate(payload: dict) -> dict:
    """合成数据路径(无 gnina / 无受体时的兜底);保持与原 run.py 输出契约相同。"""
    random.seed(int(payload.get("seed", 42)))
    n_poses = int(payload.get("num_modes", payload.get("n_poses", 9)))
    poses = []
    for i in range(n_poses):
        score = -8 + i * 0.3 + random.gauss(0, 0.2)
        poses.append({
            "rank": i + 1,
            "affinity_kcal_per_mol": round(score, 2),
            "rmsd_lb": round(random.uniform(0, 4), 2),
            "rmsd_ub": round(random.uniform(0, 6), 2),
            "pose_path": f"/tmp/pose_{i+1}.pdb",
        })
    return {
        "receptor": payload.get("receptor_pdb", "/tmp/rec.pdb"),
        "ligand": payload.get("ligand_smiles") or payload.get("ligand_sdf", "CCO"),
        "best_affinity": poses[0]["affinity_kcal_per_mol"],
        "poses": poses,
        "redock_self_test": {
            "performed": True,
            "top1_rmsd": round(random.uniform(0.3, 2.5), 2),
            "passed_2A_gate": random.random() > 0.4,
        },
        "diagnostics": {"simulated": True, "engine": "synthetic"},
    }


def _which(name: str) -> str | None:
    for p in os.environ.get("PATH", "").split(os.pathsep):
        full = os.path.join(p, name)
        if os.path.isfile(full) and os.access(full, os.X_OK):
            return full
    return None


def _prepare_ligand_sdf(smiles: str | None, sdf_path: str | None, out_dir: str) -> str:
    target = os.path.join(out_dir, "ligand.sdf")
    if sdf_path and os.path.isfile(sdf_path):
        import shutil
        shutil.copy(sdf_path, target)
        return target
    if not smiles:
        raise ValueError("既无 ligand_sdf 也无 ligand_smiles")
    from rdkit import Chem
    from rdkit.Chem import AllChem
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"RDKit 无法解析 SMILES: {smiles!r}")
    mol = Chem.AddHs(mol)
    if AllChem.EmbedMolecule(mol, randomSeed=42) != 0:
        raise RuntimeError("RDKit EmbedMolecule 失败")
    AllChem.MMFFOptimizeMolecule(mol, maxIters=200)
    w = Chem.SDWriter(target)
    w.write(mol)
    w.close()
    return target


def _extract_crystal_ligand(receptor_pdb: str, out_dir: str) -> str | None:
    """从 receptor pdb 抽最大 HETATM 残基(排除水)作 autobox center 参考。"""
    het_lines: dict[str, list[str]] = {}
    with open(receptor_pdb) as f:
        for ln in f:
            if ln.startswith("HETATM"):
                resname = ln[17:20].strip()
                if resname in ("HOH", "WAT"):
                    continue
                het_lines.setdefault(resname, []).append(ln)
    if not het_lines:
        return None
    best = max(het_lines, key=lambda r: len(het_lines[r]))
    pdb_path = os.path.join(out_dir, f"crystal_{best}.pdb")
    with open(pdb_path, "w") as f:
        f.writelines(het_lines[best])
        f.write("END\n")
    sdf_path = os.path.join(out_dir, f"crystal_{best}.sdf")
    proc = subprocess.run(
        ["obabel", pdb_path, "-O", sdf_path],
        capture_output=True, text=True, timeout=30,
    )
    if proc.returncode != 0 or not os.path.isfile(sdf_path):
        return None
    return sdf_path


def _parse_gnina_sdf(sdf_gz_path: str) -> list[dict]:
    """从 gnina 输出 .sdf.gz 解析每 pose 分数。"""
    poses: list[dict] = []
    opener = gzip.open if sdf_gz_path.endswith(".gz") else open
    with opener(sdf_gz_path, "rt", encoding="utf-8", errors="replace") as f:
        text = f.read()
    blocks = text.split("$$$$")
    rank = 0
    for blk in blocks:
        if not blk.strip():
            continue
        rank += 1
        pose: dict = {"rank": rank}
        for prop in ("minimizedAffinity", "CNNscore", "CNNaffinity", "CNN_VS"):
            tag = f"> <{prop}>"
            idx = blk.find(tag)
            if idx == -1:
                continue
            val_start = blk.find("\n", idx) + 1
            val_end = blk.find("\n", val_start)
            val = blk[val_start:val_end].strip()
            try:
                pose[prop] = float(val)
            except ValueError:
                pose[prop] = val
        poses.append(pose)
    return poses


def real(payload: dict) -> dict:
    gnina_bin = _which("gnina")
    if gnina_bin is None:
        return {
            "ok": False,
            "error": "gnina 未在 PATH;请走 praxis-dock env",
            "fallback_hint": "传 simulate=true 跑合成数据路径",
        }
    receptor = payload.get("receptor_pdb") or payload.get("receptor")
    if not receptor or not os.path.isfile(receptor):
        return {"ok": False, "error": f"receptor_pdb 不存在: {receptor!r}"}

    smiles = payload.get("ligand_smiles")
    sdf_in = payload.get("ligand_sdf")
    num_modes = int(payload.get("num_modes", 9))
    exhaustiveness = int(payload.get("exhaustiveness", 8))
    seed = int(payload.get("seed", 42))

    out_dir = payload.get("out_dir") or tempfile.mkdtemp(prefix="vina_gnina_")
    os.makedirs(out_dir, exist_ok=True)

    t0 = time.time()
    diagnostics: dict = {"out_dir": out_dir, "host": os.uname().nodename}

    try:
        lig_sdf = _prepare_ligand_sdf(smiles, sdf_in, out_dir)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"ligand prep 失败: {e}", "diagnostics": diagnostics}
    diagnostics["ligand_sdf_path"] = lig_sdf

    if payload.get("box_center") and payload.get("box_size"):
        cx, cy, cz = payload["box_center"]
        sx, sy, sz = payload["box_size"]
        box_args = [
            "--center_x", str(cx), "--center_y", str(cy), "--center_z", str(cz),
            "--size_x", str(sx), "--size_y", str(sy), "--size_z", str(sz),
        ]
        diagnostics["autobox_source"] = "user_box"
    else:
        crystal = _extract_crystal_ligand(receptor, out_dir)
        autobox = crystal or lig_sdf
        diagnostics["autobox_source"] = "crystal_ligand" if crystal else "input_ligand"
        box_args = ["--autobox_ligand", autobox]

    out_sdf = os.path.join(out_dir, "docked.sdf.gz")
    gnina_cmd = [
        gnina_bin,
        "--receptor", receptor,
        "--ligand", lig_sdf,
        *box_args,
        "--num_modes", str(num_modes),
        "--exhaustiveness", str(exhaustiveness),
        "--seed", str(seed),
        "-o", out_sdf,
        "--cnn_scoring", "rescore",
    ]
    diagnostics["gnina_command"] = " ".join(gnina_cmd)

    t_dock = time.time()
    try:
        proc = subprocess.run(
            gnina_cmd, capture_output=True, text=True,
            timeout=int(payload.get("timeout_s", 600)),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "gnina 调用超时", "diagnostics": diagnostics}
    diagnostics["gnina_wall_sec"] = round(time.time() - t_dock, 2)

    if proc.returncode != 0:
        return {
            "ok": False,
            "error": f"gnina 失败 (rc={proc.returncode})",
            "stderr": proc.stderr[-800:],
            "diagnostics": diagnostics,
        }
    if not os.path.isfile(out_sdf):
        return {"ok": False, "error": "gnina 未产出 docked.sdf.gz", "diagnostics": diagnostics}

    poses = _parse_gnina_sdf(out_sdf)
    if not poses:
        return {"ok": False, "error": "解析 sdf.gz 没拿到任何 pose", "diagnostics": diagnostics}

    def _key(p: dict):
        return -(p.get("CNNaffinity") or p.get("CNNscore") or 0)
    poses_sorted = sorted(poses, key=_key)
    for new_rank, p in enumerate(poses_sorted, start=1):
        p["rank"] = new_rank
    best = poses_sorted[0]
    vina_top = min(poses, key=lambda p: p.get("minimizedAffinity") or 0).get("minimizedAffinity")

    return {
        "ok": True,
        "skill_id": SKILL,
        "receptor": receptor,
        "ligand": smiles or sdf_in,
        "ligand_sdf_used": lig_sdf,
        "n_poses": len(poses),
        "poses": [
            {
                "rank": p["rank"],
                "vina_affinity_kcal_per_mol": p.get("minimizedAffinity"),
                "gnina_CNN_score": p.get("CNNscore"),
                "gnina_CNN_affinity": p.get("CNNaffinity"),
            }
            for p in poses_sorted
        ],
        "best_pose": {
            "rank": best["rank"],
            "vina_affinity_kcal_per_mol": best.get("minimizedAffinity"),
            "gnina_CNN_score": best.get("CNNscore"),
            "gnina_CNN_affinity": best.get("CNNaffinity"),
        },
        "vina_best_affinity_kcal_per_mol": vina_top,
        "redock_self_test": {
            "performed": False,
            "note": "本调用未跑;需 redock_self_test=true + crystal_ligand_path",
        },
        "wallclock_sec": round(time.time() - t0, 2),
        "diagnostics": diagnostics,
    }


def main():
    payload = {}
    if not sys.stdin.isatty():
        try:
            payload = json.load(sys.stdin)
            if not isinstance(payload, dict):
                payload = {}
        except json.JSONDecodeError:
            payload = {}
    if not payload:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("--simulate", action="store_true", default=False)
        ap.add_argument("--receptor")
        ap.add_argument("--smiles")
        ap.add_argument("--sdf")
        ap.add_argument("--seed", type=int, default=42)
        args, _ = ap.parse_known_args()
        payload = {
            "simulate": args.simulate,
            "receptor_pdb": args.receptor,
            "ligand_smiles": args.smiles,
            "ligand_sdf": args.sdf,
            "seed": args.seed,
        }

    simulate_mode = bool(payload.get("simulate", False))
    try:
        out = simulate(payload) if simulate_mode else real(payload)
    except Exception as e:  # noqa: BLE001
        out = {"ok": False, "error": f"run.py 内部错误: {e!r}"}

    if isinstance(out, dict):
        out.setdefault("diagnostics", {})
        if isinstance(out["diagnostics"], dict):
            out["diagnostics"].update({"archetype": ARCHETYPE, "brain": BRAIN, "skill": SKILL})
    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
