"""target_compound channel — Tanimoto similarity over RDKit Morgan fingerprints.

When the query has a SMILES, compute Tanimoto vs every case's compound SMILES
(resolved via the KEGG cache). Returns ranking by similarity desc, threshold 0.3.
"""

from __future__ import annotations

import json
from pathlib import Path


def _resolve_compound_smiles(name_or_id: str, kegg_cache_dir: Path) -> str | None:
    """Best-effort SMILES resolution: check KEGG cache, then return None."""
    if not name_or_id:
        return None
    # Try KEGG cache for compound name → SMILES (we'd populate this offline)
    safe = name_or_id.replace(" ", "_").replace("/", "_")[:80]
    for cand in (kegg_cache_dir / f"{safe}.json", kegg_cache_dir / f"{name_or_id}.smi"):
        if cand.exists():
            try:
                if cand.suffix == ".json":
                    d = json.loads(cand.read_text(encoding="utf-8"))
                    if d.get("smiles"):
                        return d["smiles"]
                else:
                    return cand.read_text(encoding="utf-8").strip()
            except Exception:
                pass
    return None


def rank_by_compound(query_smiles: str, cases: list[dict], kegg_cache_dir: Path,
                     min_tanimoto: float = 0.3) -> list[str]:
    """Tanimoto rank case_ids; return only those above threshold (in order)."""
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, DataStructs
    except ImportError:
        return []
    if not query_smiles:
        return []
    qmol = Chem.MolFromSmiles(query_smiles)
    if qmol is None:
        return []
    qfp = AllChem.GetMorganFingerprintAsBitVect(qmol, radius=2, nBits=2048)

    scored: list[tuple[str, float]] = []
    for c in cases:
        comp = c.get("target_compound") or c.get("target_analyte")
        if not comp:
            continue
        smi = _resolve_compound_smiles(comp, kegg_cache_dir)
        if not smi:
            continue
        cmol = Chem.MolFromSmiles(smi)
        if cmol is None:
            continue
        cfp = AllChem.GetMorganFingerprintAsBitVect(cmol, radius=2, nBits=2048)
        t = DataStructs.TanimotoSimilarity(qfp, cfp)
        if t >= min_tanimoto:
            scored.append((c["case_id"], t))
    scored.sort(key=lambda x: -x[1])
    return [cid for cid, _ in scored]
