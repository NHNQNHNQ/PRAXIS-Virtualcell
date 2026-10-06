"""单物种全链编排测试(离线,NCBI-only 适配):
给定已下载 SIR 表型 + ST 映射,产出漏斗 + splits + 防泄漏(内建断言)。

NCBI-only:无定量 MIC,modelable 集 = 有效 SIR 去重 isolate(非 MIC 过滤)。
"""
from pathlib import Path

from praxis_virtualcell.mdr_gnb.workflows.build_data_foundation import (
    process_species_drug,
    list_drugs,
)


def _fixture():
    # 12 株,全 meropenem,SIR 交替 R/S;3 个 ST 群 + 1 unknown 循环
    amr_rows = [
        {"genome_id": f"g{i}", "antibiotic": "meropenem",
         "laboratory_typing_method": "SIR",
         "resistant_phenotype": "R" if i % 2 else "S"}
        for i in range(12)
    ]
    st_map = {f"g{i}": ["ST11", "ST258", "ST405", "unknown"][i % 4] for i in range(12)}
    year_map = {f"g{i}": 2014 + i for i in range(12)}
    return amr_rows, st_map, year_map


def test_process_species_drug_end_to_end(tmp_path: Path):
    amr_rows, st_map, year_map = _fixture()
    out = process_species_drug(
        "klebsiella_pneumoniae", "meropenem",
        amr_rows, st_map, year_map, out_root=tmp_path, n_splits=3,
    )
    # 漏斗 md 存在且逐级单调不增
    assert out.funnel_md.exists()
    ns = [r.n_records for r in out.funnel_rows]
    assert ns == sorted(ns, reverse=True)
    # splits json 存在,含 folds 且各 fold 无 ST 泄漏(编排内部已断言,未抛即通过)
    assert out.splits_json.exists()
    assert len(out.lineage_specs) >= 2
    # temporal split 存在
    assert out.temporal_spec.scheme == "temporal"
    # unknown ST 单列(g3/g7/g11)
    assert len(out.unknown_st_ids) == 3


def test_no_leak_specs_hold(tmp_path: Path):
    # 编排产出的 lineage folds 必须无 ST 跨 train/test
    amr_rows, st_map, year_map = _fixture()
    out = process_species_drug(
        "klebsiella_pneumoniae", "meropenem",
        amr_rows, st_map, year_map, out_root=tmp_path, n_splits=3,
    )
    for spec in out.lineage_specs:
        tr = {st_map[g] for g in spec.train_ids}
        te = {st_map[g] for g in spec.test_ids}
        assert not (tr & te), f"fold{spec.fold} ST 泄漏:{tr & te}"


def test_list_drugs_dedup_sorted():
    amr_rows = [
        {"genome_id": "g1", "antibiotic": "meropenem"},
        {"genome_id": "g2", "antibiotic": "ceftriaxone"},
        {"genome_id": "g3", "antibiotic": "meropenem"},
        {"genome_id": "g4", "antibiotic": ""},  # 空药名忽略
    ]
    assert list_drugs(amr_rows) == ["ceftriaxone", "meropenem"]
