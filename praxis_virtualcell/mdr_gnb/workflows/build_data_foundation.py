"""单 species×drug 数据基石全链编排(NCBI-only 适配,离线可测):
  SIR 表型 + ST 映射 + 年份 → 漏斗表 → 谱系分组(GroupKFold by ST) + temporal → 防泄漏断言 → 落库。

在线段(下载/展平SIR/分型)在 env/run_m1_pipeline.sh 里用 CLI + st_pipeline 完成后,把
amr_rows/st_map/year_map 读入本函数;本函数纯 Python 可离线单测(不联网、不调 CLI)。

**决策变更(2026-07-03)NCBI-only**:NCBI 无定量 MIC,modelable 集不再按 MIC 过滤,
改为该药"有效 SIR 去重 isolate"(= 漏斗 dedup_isolate_drug 对应集合)。NCBI 展平输出无
collection_year,year_map 可空(temporal split 退化为空,非 G1 关键)。
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ..evaluators.funnel import FunnelRow, _is_valid_sir, build_funnel, write_funnel_md
from ..evaluators.leakage_check import assert_no_leak_all
from ..evaluators.lineage_split import (
    SplitSpec,
    get_unknown_st_ids,
    make_lineage_splits,
    make_temporal_split,
    save_splits,
)


@dataclass
class SpeciesDrugArtifacts:
    species: str
    drug: str
    funnel_rows: list[FunnelRow]
    funnel_md: Path
    lineage_specs: list[SplitSpec]
    temporal_spec: SplitSpec
    splits_json: Path
    unknown_st_ids: list[str]


def _modelable_ids(amr_rows: list[dict], drug: str) -> list[str]:
    """该药有效 SIR 去重 isolate(保留首次出现顺序)——NCBI modelable 集。"""
    seen: dict[str, None] = {}
    for r in amr_rows:
        if r.get("antibiotic", "") != drug:
            continue
        if not _is_valid_sir(r.get("resistant_phenotype", "")):
            continue
        gid = (r.get("genome_id") or "").strip()
        if gid and gid not in seen:
            seen[gid] = None
    return list(seen.keys())


def process_species_drug(
    species_dir: str,
    drug: str,
    amr_rows: list[dict],
    st_map: dict[str, str],
    year_map: dict[str, int],
    out_root: Path,
    n_splits: int = 5,
    temporal_cutoff: int = 2020,
) -> SpeciesDrugArtifacts:
    """单 species×drug 全链:漏斗 → 分组 → 防泄漏 → 落库。"""
    # 1) 漏斗表
    funnel_rows = build_funnel(species_dir, drug, amr_rows, st_map)
    funnel_md = write_funnel_md(species_dir, drug, funnel_rows, out_root)

    # 2) 参与分组的 genome_id:该药有效 SIR 去重 isolate(NCBI 无 MIC,不做 MIC 过滤)
    modelable_ids = _modelable_ids(amr_rows, drug)

    # 3) 谱系分组(GroupKFold by ST)+ unknown 单列
    lineage_specs = make_lineage_splits(modelable_ids, st_map, n_splits=n_splits, group_key="ST")
    unknown_ids = get_unknown_st_ids(modelable_ids, st_map)

    # 4) 防泄漏硬断言(G1)——任一 fold train/test ST 不相交,违反即抛异常终止
    assert_no_leak_all(lineage_specs, st_map)

    # 5) temporal split(NCBI 无 year 时 year_map 为空 → train/test 均空,scheme 仍为 temporal)
    temporal_spec = make_temporal_split(modelable_ids, year_map, cutoff_year=temporal_cutoff)

    # 6) 落库 splits(含 lineage folds + temporal + unknown 单列)
    all_specs = list(lineage_specs) + [temporal_spec]
    splits_json = save_splits(species_dir, drug, all_specs, unknown_ids, out_root)

    return SpeciesDrugArtifacts(
        species=species_dir,
        drug=drug,
        funnel_rows=funnel_rows,
        funnel_md=funnel_md,
        lineage_specs=lineage_specs,
        temporal_spec=temporal_spec,
        splits_json=splits_json,
        unknown_st_ids=unknown_ids,
    )


def _read_isolate_st(path: Path) -> dict[str, str]:
    """读 st_pipeline 产出的 isolate_st.tsv(列 asm_acc/st)→ genome_id(asm_acc)→ST。"""
    st_map: dict[str, str] = {}
    if not path.exists():
        return st_map
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            acc = (row.get("asm_acc") or "").strip()
            st = (row.get("st") or "").strip()
            if acc:
                st_map[acc] = st or "unknown"
    return st_map


def load_inputs_from_disk(
    species_dir: str, out_root: Path,
) -> tuple[list[dict], dict[str, str], dict[str, int]]:
    """从 53 已产出文件读入(NCBI-only 路径):
      raw/<sp>/ncbi_amr_phenotypes.tsv(SIR 表型)、raw/<sp>/isolate_st.tsv(ST 分型)。
    NCBI 展平输出无 collection_year,year_map 暂空(temporal 非 G1 关键)。
    """
    raw = out_root / "raw" / species_dir
    amr_rows: list[dict] = []
    amr_tsv = raw / "ncbi_amr_phenotypes.tsv"
    if amr_tsv.exists():
        with amr_tsv.open(encoding="utf-8", newline="") as f:
            amr_rows = list(csv.DictReader(f, delimiter="\t"))

    st_map = _read_isolate_st(raw / "isolate_st.tsv")
    year_map: dict[str, int] = {}  # NCBI 展平输出无年份;需要 temporal 时再从 ncbi_metadata 补
    return amr_rows, st_map, year_map


def list_drugs(amr_rows: list[dict]) -> list[str]:
    """该物种 AMR 表里出现过的全部药物(去重、非空、字典序)。"""
    return sorted({r.get("antibiotic", "").strip() for r in amr_rows if r.get("antibiotic", "").strip()})


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="单物种全药漏斗+分组编排(读 53 已产出文件,NCBI-only)")
    ap.add_argument("--species", required=True)
    ap.add_argument("--out-root", required=True, type=Path)
    ap.add_argument("--n-splits", type=int, default=5)
    ap.add_argument("--temporal-cutoff", type=int, default=2020)
    a = ap.parse_args()

    amr_rows, st_map, year_map = load_inputs_from_disk(a.species, a.out_root)
    drugs = list_drugs(amr_rows)
    print(f"[{a.species}] 药物数={len(drugs)};ST 已分型={len(st_map)}")
    ok, degraded, insufficient = 0, 0, 0
    for drug in drugs:
        try:
            art = process_species_drug(
                a.species, drug, amr_rows, st_map, year_map,
                out_root=a.out_root, n_splits=a.n_splits,
                temporal_cutoff=a.temporal_cutoff,
            )
        except Exception as e:  # 分组失败(如某药去克隆后组数过少)不阻断其余药
            print(f"  [WARN] {drug}: {e}")
            continue
        n_final = art.funnel_rows[-1].n_strains
        if n_final >= 100:
            ok += 1
        elif n_final >= 20:
            degraded += 1
        else:
            insufficient += 1
    print(f"[OK] {a.species}: 可SIR分类={ok} 降级={degraded} 数据不足={insufficient}")
