"""B0.1:从 ChEMBL 拉取物种 MIC 活性 → 清洗成 QSAR 数据集(化合物 SMILES + log-MIC)。

数据门(B0 探针确认):ChEMBL_37 `target_organism=<菌>&standard_type=MIC` → EC 90099/KP 31130,
100% 带 canonical_smiles,83% 关系"=",单位 ug.mL-1。pchembl 未填 → 自算 log10-MIC(ug/mL)。

纪律:游标分页(follow page_meta.next)、增量落盘可续、retry;清洗只留 relation="="+有效 SMILES+有效值;
同 canonical SMILES 的重复测量取**中位**(去噪);去盐(取最大有机片段)。
raw 缓存落 data/mdr_gnb/raw/compound_activity/(gitignore),清洗集 parquet 同处。
用法:python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.chembl_pull --species escherichia_coli
"""
from __future__ import annotations

import argparse
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://www.ebi.ac.uk/chembl/api/data"
OUT = Path("data/mdr_gnb/raw/compound_activity")
_ORG = {"escherichia_coli": "Escherichia coli", "klebsiella_pneumoniae": "Klebsiella pneumoniae",
        "pseudomonas_aeruginosa": "Pseudomonas aeruginosa",
        "acinetobacter_baumannii": "Acinetobacter baumannii", "salmonella_enterica": "Salmonella"}


def _fetch(url: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    for _ in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except Exception:
            time.sleep(2.0)
    raise RuntimeError(f"efetch 3 次失败: {url[:90]}")


def pull_raw(species: str) -> Path:
    """游标分页拉全部 MIC 活性,增量写 JSONL(可续:已存在则跳过重拉)。"""
    org = _ORG[species]
    OUT.mkdir(parents=True, exist_ok=True)
    raw = OUT / f"{species}_mic_raw.jsonl"
    if raw.exists():
        print(f"{species}: raw 缓存已存在 {raw}(跳过拉取;删文件可重拉)", flush=True)
        return raw
    params = urllib.parse.urlencode({"target_organism": org, "standard_type": "MIC",
                                     "limit": 1000,
                                     "only": "molecule_chembl_id,canonical_smiles,"
                                             "standard_value,standard_units,standard_relation"})
    url = f"{BASE}/activity.json?{params}"
    n = 0
    with raw.open("w") as f:
        while url:
            d = _fetch(url)
            for a in d["activities"]:
                f.write(json.dumps({k: a.get(k) for k in
                                    ("molecule_chembl_id", "canonical_smiles",
                                     "standard_value", "standard_units", "standard_relation")},
                                   ensure_ascii=False) + "\n")
            n += len(d["activities"])
            nxt = d["page_meta"].get("next")
            url = f"https://www.ebi.ac.uk{nxt}" if nxt else None
            print(f"  [{n}/{d['page_meta']['total_count']}]", flush=True)
            time.sleep(0.25)
    print(f"{species}: 拉取 {n} 条 → {raw}", flush=True)
    return raw


def _desalt(smiles: str) -> str | None:
    """去盐:取最大(重原子最多)有机片段。失败/无机返回 None。"""
    from rdkit import Chem
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    frags = Chem.GetMolFrags(m, asMols=True, sanitizeFrags=False)
    if not frags:
        return None
    big = max(frags, key=lambda fr: fr.GetNumHeavyAtoms())
    try:
        return Chem.MolToSmiles(big)
    except Exception:
        return None


def clean(species: str) -> Path:
    """清洗:relation='=' + 有效 SMILES + 有效值;去盐;同 canonical SMILES 取中位 MIC;log10-MIC。"""
    import pandas as pd

    raw = pull_raw(species)
    rows = []
    for line in raw.open():
        r = json.loads(line)
        if r.get("standard_relation") != "=":
            continue
        if (r.get("standard_units") or "").strip() != "ug.mL-1":
            continue
        smi = r.get("canonical_smiles")
        val = r.get("standard_value")
        if not smi or val in (None, ""):
            continue
        try:
            mic = float(val)
        except (TypeError, ValueError):
            continue
        if not (mic > 0):
            continue
        canon = _desalt(smi)
        if canon is None:
            continue
        rows.append({"smiles": canon, "mic_ug_ml": mic})
    df = pd.DataFrame(rows)
    # 同化合物重复测量取中位(去噪),记 n_meas
    agg = (df.groupby("smiles")["mic_ug_ml"].agg(["median", "count"])
             .rename(columns={"median": "mic_ug_ml", "count": "n_meas"}).reset_index())
    agg["log10_mic"] = agg["mic_ug_ml"].map(lambda v: math.log10(v))
    out = OUT / f"{species}_mic_clean.parquet"
    agg.to_parquet(out, index=False)
    print(f"{species}: 清洗后唯一化合物 {len(agg)}(原始有效测量 {len(df)})"
          f" | log10-MIC 范围 [{agg['log10_mic'].min():.2f},{agg['log10_mic'].max():.2f}] → {out}", flush=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="B0.1 ChEMBL MIC 拉取+清洗")
    ap.add_argument("--species", default="escherichia_coli", help="逗号分隔物种")
    args = ap.parse_args()
    for sp in [s.strip() for s in args.species.split(",") if s.strip()]:
        clean(sp)
