"""确定性重生 golden_set_sir.yaml(可一键从 NCBI tsv 重建、可审计)。

用法(从仓库根):
    .venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.validation.build_golden_sir

取样规则(确定性,固定排序):
  - 物种:仅 EC/KP —— 本地仅这两个物种有 data/mdr_gnb/raw/<sp>/ncbi_amr_phenotypes.tsv
    (PA/AB/SE 的 raw 目录为空,如实不纳入;这是 T1A 轨A 面值的物种覆盖局限)。
  - 每 species × 每选定 drug:R/S 各取 K=5 株(按 genome_id 升序取前 K,genome_id 去重),
    共 2 物种 × 5 药 × (5R+5S) = 100 真实株(true_sir 取自 tsv resistant_phenotype 真实值,
    只保留 S/R,丢 I/空)。
  - amr_profile 用 **base 名**(tsv ncbi_amr_genotypes 每 token 剥 =modifier):与部署模型训练
    特征化(augmented_features)经服务端 _amr_to_X 逐位一致 —— 保真见 verify_amr_fidelity.py。
  - 另加 2 条强机制锚点(教科书级基因→表型,synthetic 最小 profile,非真实 isolate →
    in_training=false;label_source=curated_anchor),置于文件首部。

红线:纯确定性(固定排序 + 手写 yaml,不依赖 dict/yaml.dump 顺序)。重跑字节一致。
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

# 仓库根(本文件 parents:[0]=validation [1]=science_v2 [2]=workflows [3]=mdr_gnb
# [4]=praxis_virtualcell [5]=仓库根)
_REPO_ROOT = Path(__file__).resolve().parents[5]
DATA = _REPO_ROOT / "data" / "mdr_gnb"
OUT = DATA / "golden" / "golden_set_sir.yaml"

# 每 species×drug 取的 R/S 数(确定性:按 genome_id 排序取前 K)
K = 5

DRUG_CLASS = {
    "ceftriaxone": "cephalosporins", "cefotaxime": "cephalosporins",
    "ceftazidime": "cephalosporins", "cefepime": "cephalosporins",
    "meropenem": "carbapenems", "imipenem": "carbapenems", "ertapenem": "carbapenems",
    "ciprofloxacin": "fluoroquinolones", "levofloxacin": "fluoroquinolones",
    "gentamicin": "aminoglycosides", "amikacin": "aminoglycosides",
    "tobramycin": "aminoglycosides", "ampicillin": "penicillins",
}

DRUGS_BY_SP = {
    "escherichia_coli": [
        "ceftriaxone", "meropenem", "ciprofloxacin", "gentamicin", "ampicillin"],
    "klebsiella_pneumoniae": [
        "meropenem", "ceftriaxone", "ciprofloxacin", "gentamicin", "imipenem"],
}

# 强机制锚点(教科书级基因→表型;synthetic 最小 profile,非真实 isolate → in_training=false)
ANCHORS = [
    {
        "isolate_id": "ANCHOR_KP_KPC2",
        "species": "klebsiella_pneumoniae",
        "amr_profile": {"blaKPC-2": True},
        "drug": "meropenem", "drug_class": "carbapenems",
        "true_sir": "R", "label_source": "curated_anchor", "in_training": False,
    },
    {
        "isolate_id": "ANCHOR_EC_CTXM15",
        "species": "escherichia_coli",
        "amr_profile": {"blaCTX-M-15": True},
        "drug": "ceftriaxone", "drug_class": "cephalosporins",
        "true_sir": "R", "label_source": "curated_anchor", "in_training": False,
    },
]


def base_profile(genostr: str) -> dict[str, bool]:
    """ncbi_amr_genotypes 串 → {base名: True}(剥 =modifier;保真见 verify_amr_fidelity.py)。"""
    prof: dict[str, bool] = {}
    for raw in (genostr or "").split(","):
        raw = raw.strip()
        if not raw:
            continue
        b = raw.partition("=")[0].strip()
        if b:
            prof[b] = True
    return prof


def pick_rows() -> list[dict]:
    """从 tsv 确定性抽样(每 species×drug 排序后 R/S 各取前 K)。"""
    rows: list[dict] = []
    for sp, drugs in DRUGS_BY_SP.items():
        p = DATA / "raw" / sp / "ncbi_amr_phenotypes.tsv"
        by_drug = {d: {"R": {}, "S": {}} for d in drugs}
        with p.open(encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                d = row["antibiotic"]
                ph = row["resistant_phenotype"]
                if d not in by_drug or ph not in ("R", "S"):
                    continue
                gid = row["genome_id"]
                if gid in by_drug[d][ph]:
                    continue  # 同 genome 同药同表型去重
                by_drug[d][ph][gid] = row["ncbi_amr_genotypes"]
        for d in drugs:
            for ph in ("R", "S"):
                for gid in sorted(by_drug[d][ph])[:K]:
                    rows.append({
                        "isolate_id": gid,
                        "species": sp,
                        "amr_profile": base_profile(by_drug[d][ph][gid]),
                        "drug": d,
                        "drug_class": DRUG_CLASS[d],
                        "true_sir": ph,
                        "label_source": "ncbi_real",
                        "in_training": True,  # 部署模型在全量 tsv 上训过,真实株即训练行
                    })
    rows.sort(key=lambda r: (r["species"], r["drug"], r["true_sir"], r["isolate_id"]))
    return rows


def _yq(s: str) -> str:
    """基因名做 yaml key:含特殊字符则单引号包裹(单引号内转义为两个)。"""
    if any(c in s for c in ":#{}[],&*!|>'\"%@` ") or s != s.strip():
        return "'" + s.replace("'", "''") + "'"
    return s


def to_yaml(rows: list[dict]) -> str:
    """手写确定性 yaml(list of dict),amr_profile 内键排序,不依赖 yaml.dump 顺序。"""
    lines: list[str] = []
    for r in rows:
        lines.append(f"- isolate_id: {r['isolate_id']}")
        lines.append(f"  species: {r['species']}")
        prof = r["amr_profile"]
        if prof:
            lines.append("  amr_profile:")
            for k in sorted(prof):
                lines.append(f"    {_yq(k)}: true")
        else:
            lines.append("  amr_profile: {}")
        lines.append(f"  drug: {r['drug']}")
        lines.append(f"  drug_class: {r['drug_class']}")
        lines.append(f"  true_sir: {r['true_sir']}")
        lines.append(f"  label_source: {r['label_source']}")
        lines.append(f"  in_training: {str(r['in_training']).lower()}")
    return "\n".join(lines) + "\n"


def build(out_path: Path = OUT) -> dict:
    """重生 golden 并写盘;返回统计。"""
    real = pick_rows()
    allrows = ANCHORS + real
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(to_yaml(allrows), encoding="utf-8")
    return {
        "path": str(out_path),
        "n_total": len(allrows),
        "n_anchor": len(ANCHORS),
        "n_real": len(real),
        "real_sir": dict(Counter(r["true_sir"] for r in real)),
        "species": dict(Counter(r["species"] for r in allrows)),
    }


if __name__ == "__main__":
    stat = build()
    print(f"golden 写入 {stat['path']}")
    print(f"  总 {stat['n_total']} 行(anchor {stat['n_anchor']} + real {stat['n_real']})")
    print(f"  真实 R/S: {stat['real_sir']}")
    print(f"  物种: {stat['species']}")
