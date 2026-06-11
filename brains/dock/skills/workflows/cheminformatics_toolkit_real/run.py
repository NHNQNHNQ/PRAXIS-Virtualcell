"""cheminformatics_toolkit — RDKit 通用化学信息学工具(host_env: praxis-dock)。

通用、原子级分子操作(非对接分析链):格式转换、指纹相似性、子结构匹配、
Murcko 骨架、Lipinski 类描述符。

I/O:
  --inputs '{"smiles":"CC(=O)Oc1ccccc1C(=O)O","operations":["formula"]}'(JSON 文件路径或 inline)
  --out 输出 JSON 路径(默认 stdout)
  stdout: {"ok":true,"input_smiles":"...","results":{...}}
"""
import argparse
import json
import sys
from pathlib import Path


def _mol(smiles, Chem):
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        raise ValueError(f"无法解析 SMILES: {smiles!r}")
    return m


def compute(spec: dict) -> dict:
    from rdkit import Chem, DataStructs  # noqa: PLC0415
    from rdkit.Chem import (  # noqa: PLC0415
        Descriptors, rdFingerprintGenerator, rdMolDescriptors,
    )
    from rdkit.Chem.Scaffolds import MurckoScaffold  # noqa: PLC0415

    smiles = (spec.get("smiles") or "").strip()
    if not smiles:
        return {"ok": False, "error": "smiles 为空"}
    try:
        mol = _mol(smiles, Chem)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    ops = spec.get("operations")
    if not ops:
        ops = ["canonical_smiles", "formula", "inchikey", "descriptors"]
    smiles2 = (spec.get("smiles2") or "").strip()
    smarts = (spec.get("smarts") or "").strip()

    results: dict = {}
    for op in ops:
        if op == "canonical_smiles":
            results["canonical_smiles"] = Chem.MolToSmiles(mol)
        elif op == "inchi":
            results["inchi"] = Chem.MolToInchi(mol)
        elif op == "inchikey":
            results["inchikey"] = Chem.MolToInchiKey(mol)
        elif op == "formula":
            results["formula"] = rdMolDescriptors.CalcMolFormula(mol)
        elif op == "scaffold":
            results["scaffold"] = Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(mol))
        elif op == "tanimoto":
            if not smiles2:
                results["tanimoto"] = {"error": "需要 smiles2"}
                continue
            gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
            fp1 = gen.GetFingerprint(mol)
            fp2 = gen.GetFingerprint(_mol(smiles2, Chem))
            results["tanimoto"] = round(DataStructs.TanimotoSimilarity(fp1, fp2), 4)
        elif op == "substructure_match":
            if not smarts:
                results["substructure_match"] = {"error": "需要 smarts"}
                continue
            patt = Chem.MolFromSmarts(smarts)
            if patt is None:
                results["substructure_match"] = {"error": f"非法 SMARTS: {smarts}"}
                continue
            matches = mol.GetSubstructMatches(patt)
            results["substructure_match"] = {"match": len(matches) > 0, "count": len(matches)}
        elif op == "descriptors":
            results["descriptors"] = {
                "mol_weight": round(Descriptors.MolWt(mol), 2),
                "logp": round(Descriptors.MolLogP(mol), 3),
                "h_donors": rdMolDescriptors.CalcNumHBD(mol),
                "h_acceptors": rdMolDescriptors.CalcNumHBA(mol),
                "tpsa": round(rdMolDescriptors.CalcTPSA(mol), 2),
                "num_rings": rdMolDescriptors.CalcNumRings(mol),
                "rotatable_bonds": rdMolDescriptors.CalcNumRotatableBonds(mol),
            }
        else:
            results[op] = {"error": f"未知 operation: {op}"}

    return {"ok": True, "input_smiles": smiles, "results": results}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True, help="JSON 文件路径或 inline JSON 字符串")
    ap.add_argument("--out", help="输出 JSON 路径(默认 stdout)")
    args, _unknown = ap.parse_known_args()

    raw = args.inputs
    try:
        p = Path(raw)
        spec = json.loads(p.read_text()) if (len(raw) < 512 and p.exists()) else json.loads(raw)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"无法解析 inputs: {e}"}, ensure_ascii=False))
        return 0

    try:
        out = compute(spec)
    except Exception as e:  # noqa: BLE001
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    payload = json.dumps(out, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
