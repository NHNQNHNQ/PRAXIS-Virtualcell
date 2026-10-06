"""T4:确定性验证。平台核心卖点"同输入 → trace 逐字节相等"的可测锚。

固定语料(多样性优先,≥30 条,非随机、非清一色 SIR),覆盖五类:
  - SIR(12条):2 条强机制锚点(build_golden_sir.ANCHORS)+ 按 _SIR_CRITERIA
    (species, drug, true_sir)从 golden_set_sir.yaml 各取首个匹配行——EC/KP 两物种、
    多个药、R/S 均覆盖。
  - 小分子活性(8条):golden_compounds.csv 里 label_source=chembl_train 且有 mic 的
    前 8 条(文件原序,固定排序,不随机)。这 8 条 drug 名占位为 SMILES,不命中代谢靶。
  - 代谢靶 activity 触发真 FBA(1条):drug 名=真实药名 "trimethoprim"(GemFbaPredictor
    靠**药名**匹配 METABOLIC_TARGET_REACTIONS,不读 SMILES)、smiles=trimethoprim 真实结构
    → cobra LP 真跑 _run_fba() 阻断 DHFR(growth_inhibition=1.0),mechanism.available=True、
    有 fba_simulation。此条专门验证 FBA(round 到 4 位吸收 ULP 噪声)后 trace_hash 仍逐字稳定
    ——否则"FBA 确定性已验证"是假覆盖(上 8 条 SMILES 占位药名永不命中代谢靶,恒早退)。
  - 肽活性(8条):golden_peptides.csv 里 label_source=dbaasp_train 且有 mic 的前 8 条
    (文件原序,固定排序)。
  - fail-closed 类(6条):OOD 小分子(甲烷/苯)、OOD 肽(polyA/polyG)、未知物种 SIR、
    已知物种但药无训练 artifact 的 SIR —— 复用 T2/T3 已实跑验证的 fail-closed 案例
    (未知物种/无 artifact 走 species/artifact fail-closed,sir=None、
    prediction_available=False;OOD 走 abstain)。

run(n_repeats) 对每条查询跑 harness.trace_hash n_repeats 次,断言 hash 集合 size==1。
若发现不稳定 hash(真 bug,如 RF 顺序/FBA round/时间戳注入/dict 无序),如实记入
unstable_examples——不改测试掩盖,留档供后续独立修复。
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation import harness
from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation.build_golden_sir import (
    ANCHORS as _SIR_ANCHORS_RAW,
)

# t4_determinism.py: .../workflows/science_v2/validation/t4_determinism.py
# parents[0]=validation parents[1]=science_v2 parents[2]=workflows parents[3]=mdr_gnb
# parents[4]=praxis_virtualcell parents[5]=仓库根(与 harness.py/t1_predictive.py 同款核对法)
_REPO_ROOT = Path(__file__).resolve().parents[5]
_GOLDEN_SIR_PATH = _REPO_ROOT / "data" / "mdr_gnb" / "golden" / "golden_set_sir.yaml"
_GOLDEN_COMPOUNDS_PATH = _REPO_ROOT / "data" / "mdr_gnb" / "golden" / "golden_compounds.csv"
_GOLDEN_PEPTIDES_PATH = _REPO_ROOT / "data" / "mdr_gnb" / "golden" / "golden_peptides.csv"

_COMPOUND_SPECIES = "escherichia_coli"
_PEPTIDE_SPECIES = "escherichia_coli"

N_COMPOUND_SAMPLE = 8
N_PEPTIDE_SAMPLE = 8

# SIR 抽样条件(species, drug, true_sir):golden_set_sir.yaml 本身按
# species/drug/true_sir/isolate_id 排序(build_golden_sir.pick_rows),按此条件各取
# 首个匹配行即固定、可复现,不随机。实跑核对(见上方模块 docstring 测算):十条组合
# 在 golden_set_sir.yaml 中均恰有 5 条可选,首个匹配稳定存在。
_SIR_CRITERIA: tuple[tuple[str, str, str], ...] = (
    ("escherichia_coli", "ceftriaxone", "R"),
    ("escherichia_coli", "ceftriaxone", "S"),
    ("escherichia_coli", "meropenem", "R"),
    ("escherichia_coli", "meropenem", "S"),
    ("escherichia_coli", "ciprofloxacin", "R"),
    ("escherichia_coli", "gentamicin", "S"),
    ("klebsiella_pneumoniae", "meropenem", "R"),
    ("klebsiella_pneumoniae", "meropenem", "S"),
    ("klebsiella_pneumoniae", "ceftriaxone", "R"),
    ("klebsiella_pneumoniae", "ciprofloxacin", "S"),
)


def _sir_query(species: str, amr_profile: dict, drug: str, drug_class: str) -> dict[str, Any]:
    return {
        "species": species,
        "amr_profile": amr_profile,
        "drug_panel": [{"drug": drug, "drug_class": drug_class}],
        "requested_outputs": ["SIR"],
    }


def _compound_query(smiles: str) -> dict[str, Any]:
    return {
        "species": _COMPOUND_SPECIES,
        "smiles": smiles,
        "drug_panel": [{"drug": smiles, "drug_class": "novel_compound"}],
        "requested_outputs": ["activity"],
    }


def _peptide_query(sequence: str) -> dict[str, Any]:
    return {
        "species": _PEPTIDE_SPECIES,
        "sequence": sequence,
        "drug_panel": [{"drug": sequence, "drug_class": "antimicrobial_peptide"}],
        "requested_outputs": ["peptide_activity"],
    }


# trimethoprim 真实结构(golden_compounds.csv 里 label_source=chembl_train 那行,与 T3C 同源)。
# drug 名用真实药名(非 SMILES 占位),才能命中 gem_fba.py 的代谢靶反应表触发真 FBA。
_TRIMETHOPRIM_SMILES = "COc1cc(Cc2cnc(N)nc2N)cc(OC)c1OC"


def _metabolic_fba_query() -> dict[str, Any]:
    """代谢靶 activity 查询:drug 名=真实药名触发 cobra LP 真跑 FBA(阻断 DHFR)。

    这是 t2_ood/t1b 的 SMILES 占位药名做不到的——那些 drug=SMILES 永不命中
    METABOLIC_TARGET_REACTIONS,fuse_mechanism 恒早退"非代谢靶",从不跑 _run_fba();
    本查询让 FBA 真正进入 trace,验证其 round-to-4 后 trace_hash 仍逐字稳定。
    """
    return {
        "species": _COMPOUND_SPECIES,
        "smiles": _TRIMETHOPRIM_SMILES,
        "drug_panel": [{"drug": "trimethoprim", "drug_class": "novel_compound"}],
        "requested_outputs": ["activity"],
    }


def _load_sir_real_rows() -> list[dict[str, Any]]:
    """读 golden_set_sir.yaml 全部行,跳过前面的强机制锚点,只留真实株。

    build_golden_sir.build() 写盘顺序恒为 `ANCHORS + real`(见 build_golden_sir.py:146),
    故跳过前 len(_SIR_ANCHORS_RAW) 条即为真实株起点,不依赖内容匹配、只依赖该固定写盘顺序。
    """
    rows = yaml.safe_load(_GOLDEN_SIR_PATH.read_text(encoding="utf-8"))
    return rows[len(_SIR_ANCHORS_RAW):]


def _first_matching_sir_row(rows: list[dict[str, Any]], species: str, drug: str,
                            true_sir: str) -> dict[str, Any]:
    for r in rows:
        if r["species"] == species and r["drug"] == drug and r["true_sir"] == true_sir:
            return r
    raise ValueError(
        f"golden_set_sir.yaml 无匹配行:species={species!r} drug={drug!r} true_sir={true_sir!r}"
    )


def _build_sir_corpus() -> list[dict[str, Any]]:
    """2 条强机制锚点 + 按 _SIR_CRITERIA 各取首个匹配行(固定排序,不随机)。"""
    queries = [
        _sir_query(a["species"], a["amr_profile"], a["drug"], a["drug_class"])
        for a in _SIR_ANCHORS_RAW
    ]
    real_rows = _load_sir_real_rows()
    for species, drug, true_sir in _SIR_CRITERIA:
        r = _first_matching_sir_row(real_rows, species, drug, true_sir)
        queries.append(_sir_query(r["species"], r["amr_profile"], r["drug"], r["drug_class"]))
    return queries


def _build_compound_corpus() -> list[dict[str, Any]]:
    """golden_compounds.csv 里 label_source=chembl_train 且有 mic 的前 N 条(文件原序)。"""
    rows = harness.load_golden(
        _GOLDEN_COMPOUNDS_PATH, required=["name", "smiles", "mic_ug_ml", "label_source"])
    valid = [r for r in rows
             if (r.get("label_source") or "").strip().lower() == "chembl_train"
             and (r.get("smiles") or "").strip()
             and (r.get("mic_ug_ml") or "").strip()]
    sample = valid[:N_COMPOUND_SAMPLE]
    if len(sample) < N_COMPOUND_SAMPLE:
        raise ValueError(
            f"golden_compounds.csv 有效行不足 {N_COMPOUND_SAMPLE} 条(实得 {len(sample)})")
    return [_compound_query(r["smiles"]) for r in sample]


def _build_peptide_corpus() -> list[dict[str, Any]]:
    """golden_peptides.csv 里 label_source=dbaasp_train 且有 mic 的前 N 条(文件原序)。"""
    rows = harness.load_golden(
        _GOLDEN_PEPTIDES_PATH, required=["name", "sequence", "mic_um", "label_source"])
    valid = [r for r in rows
             if (r.get("label_source") or "").strip().lower() == "dbaasp_train"
             and (r.get("sequence") or "").strip()
             and (r.get("mic_um") or "").strip()]
    sample = valid[:N_PEPTIDE_SAMPLE]
    if len(sample) < N_PEPTIDE_SAMPLE:
        raise ValueError(
            f"golden_peptides.csv 有效行不足 {N_PEPTIDE_SAMPLE} 条(实得 {len(sample)})")
    return [_peptide_query(r["sequence"]) for r in sample]


def _build_abstain_corpus() -> list[dict[str, Any]]:
    """复用 T2/T3 已实跑验证的 fail-closed 案例(OOD 小分子/OOD 肽/未知物种/无训练artifact药)。

    注:OOD 小分子/肽走 abstain(abstained=True);未知物种/无 artifact 药走 species/artifact
    fail-closed(sir=None、prediction_available=False,abstained 字段实测为 False)——
    两者都属"平台看不懂 → 不胡编数字"的诚实拒答,措辞统称 fail-closed 更准。
    """
    return [
        _compound_query("C"),           # 甲烷,真 OOD abstain(见 t2_ood.OOD_SMILES)
        _compound_query("c1ccccc1"),    # 苯,真 OOD abstain
        _peptide_query("A" * 18),       # polyA,真 OOD abstain(见 t2_ood.OOD_PEPTIDES)
        _peptide_query("G" * 16),       # polyG,真 OOD abstain
        # 未知物种 / 已知物种但药无训练 artifact:走 species/artifact fail-closed(sir=None)
        _sir_query("martian_bug", {"blaKPC": True}, "meropenem", "carbapenems"),
        _sir_query("escherichia_coli", {"blaKPC": True}, "totally_fake_drug_zzz", "carbapenems"),
    ]


# 模块级 fail-closed 语料常量(供 _classify 判类,不逐次重建/不读文件)。
_ABSTAIN_QUERIES: list[dict[str, Any]] = _build_abstain_corpus()


def build_corpus() -> list[dict[str, Any]]:
    """确定性组装完整语料(类别固定顺序:SIR → 小分子 → 代谢靶FBA → 肽 → fail-closed)。"""
    return (
        _build_sir_corpus()
        + _build_compound_corpus()
        + [_metabolic_fba_query()]
        + _build_peptide_corpus()
        + _ABSTAIN_QUERIES
    )


CORPUS: list[dict[str, Any]] = build_corpus()


def _classify(raw: dict[str, Any]) -> str:
    """按 raw 字段特征给单条查询分类(供 corpus_composition 据实统计,不重建默认语料)。

    fail-closed 语料优先(结构相等匹配 _ABSTAIN_QUERIES),否则按字段:
    requested_outputs 含 SIR → sir;有 smiles → compound_activity;有 sequence →
    peptide_activity;都不满足 → other。对任意传入 corpus 都成立,不依赖是否为默认 CORPUS。
    """
    if raw in _ABSTAIN_QUERIES:
        return "fail_closed"
    if "SIR" in (raw.get("requested_outputs") or []):
        return "sir"
    if (raw.get("smiles") or "").strip():
        return "compound_activity"
    if (raw.get("sequence") or "").strip():
        return "peptide_activity"
    return "other"


def _summarize_raw(raw: dict[str, Any]) -> dict[str, Any]:
    """摘要一条 raw 查询(供 unstable_examples 展示,避免整段塞入报告)。"""
    drug = None
    drug_panel = raw.get("drug_panel")
    if isinstance(drug_panel, list) and len(drug_panel) == 1:
        (drug_entry,) = drug_panel
        if isinstance(drug_entry, dict):
            drug = drug_entry.get("drug")
    return {
        "species": raw.get("species"),
        "smiles": raw.get("smiles"),
        "sequence": raw.get("sequence"),
        "drug": drug,
        "amr_profile_keys": sorted((raw.get("amr_profile") or {}).keys()),
    }


def run(n_repeats: int = 20, corpus: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """对语料每条跑 n_repeats 次 trace_hash,断言 hash 集合 size==1。

    确定性:遍历顺序严格按 corpus 原序。不稳定条目如实记入 unstable_examples——
    这是真 bug(RF 顺序/FBA round/时间戳注入/dict 无序等),不掩盖,留档供后续独立修复。
    """
    corpus = corpus if corpus is not None else CORPUS
    unstable_examples: list[dict[str, Any]] = []
    n_unstable = 0
    for raw in corpus:
        hashes = {harness.trace_hash(raw) for _ in range(n_repeats)}
        if len(hashes) != 1:
            n_unstable += 1
            unstable_examples.append({
                "raw_summary": _summarize_raw(raw),
                "distinct_hashes": sorted(hashes),
                "n_distinct": len(hashes),
            })
    # 据实统计传入 corpus 的构成(按字段特征分类,不重建默认语料、不重读 CSV/YAML):
    # run(corpus=CORPUS[:3]) 也会如实报 3 条的构成,不再固定重算默认四语料。
    composition = Counter(_classify(raw) for raw in corpus)
    # FBA 覆盖证据:实跑代谢靶查询一次,记录 mechanism 段——证明 cobra LP 真进 trace
    # (available=True/有 fba_simulation/DHFR 阻断),故"FBA 确定性已验证"是真覆盖非假声称。
    fba_mech = harness.run_query(_metabolic_fba_query())["mechanism"] or {}
    fba_sim = fba_mech.get("fba_simulation") or {}
    fba_coverage = {
        "drug": "trimethoprim",
        "mechanism_available": fba_mech.get("available"),
        "fba_simulation_present": fba_mech.get("fba_simulation") is not None,
        "growth_inhibition": fba_sim.get("growth_inhibition"),
        "reactions_blocked": fba_sim.get("reactions_blocked"),
    }
    return {
        "n_queries": len(corpus),
        "n_repeats": n_repeats,
        "n_unstable": n_unstable,
        "all_stable": n_unstable == 0,
        "unstable_examples": unstable_examples,
        "corpus_composition": dict(sorted(composition.items())),
        "fba_coverage": fba_coverage,
    }


if __name__ == "__main__":
    # 100 = 存档报告的重复次数(CI 里 test_t4_determinism 用 20 控时长)。此处必须与
    # reports/.../t4_determinism.json 的 n_repeats 一致,否则跑一次入口就把存档覆写成
    # 另一个值,报告便不可由本入口复现。
    payload = run(n_repeats=100)
    p = harness.write_report("t4_determinism", payload)
    print(f"t4_determinism 报告写入 {p}")
    print(f"  语料 {payload['n_queries']} 条 x 重复 {payload['n_repeats']} 次")
    print(f"  构成:{payload['corpus_composition']}")
    print(f"  FBA 覆盖:{payload['fba_coverage']}")
    print(f"  all_stable={payload['all_stable']} n_unstable={payload['n_unstable']}")
    if not payload["all_stable"]:
        print(f"  不稳定示例:{payload['unstable_examples']}")
