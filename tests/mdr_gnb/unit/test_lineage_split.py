# praxis_virtualcell/mdr_gnb/tests/test_lineage_split.py
"""谱系分组测试:GroupKFold by ST 不泄漏 + temporal split + unknown 单列。"""
import pytest

from praxis_virtualcell.mdr_gnb.evaluators.lineage_split import (
    make_lineage_splits, make_temporal_split,
)
from praxis_virtualcell.mdr_gnb.evaluators.leakage_check import (
    assert_no_lineage_leak, LineageLeakError,
)


def _data():
    # 10 株,ST 分 3 群 + 2 个 unknown
    genome_ids = [f"g{i}" for i in range(10)]
    st_map = {
        "g0": "ST11", "g1": "ST11", "g2": "ST11",
        "g3": "ST258", "g4": "ST258",
        "g5": "ST405", "g6": "ST405", "g7": "ST405",
        "g8": "unknown", "g9": "unknown",
    }
    years = {f"g{i}": 2015 + i for i in range(10)}
    return genome_ids, st_map, years


def test_lineage_splits_no_st_overlap():
    genome_ids, st_map, _ = _data()
    specs = make_lineage_splits(genome_ids, st_map, n_splits=3, group_key="ST")
    for spec in specs:
        train_st = {st_map[g] for g in spec.train_ids}
        test_st = {st_map[g] for g in spec.test_ids}
        assert train_st.isdisjoint(test_st), f"fold {spec.fold} ST 泄漏"


def test_unknown_st_excluded_from_folds():
    genome_ids, st_map, _ = _data()
    specs = make_lineage_splits(genome_ids, st_map, n_splits=3, group_key="ST")
    for spec in specs:
        all_ids = set(spec.train_ids) | set(spec.test_ids)
        assert "g8" not in all_ids and "g9" not in all_ids  # unknown 单列不入 fold


def test_assert_no_lineage_leak_passes_on_clean():
    genome_ids, st_map, _ = _data()
    specs = make_lineage_splits(genome_ids, st_map, n_splits=3, group_key="ST")
    for spec in specs:
        assert_no_lineage_leak(spec, st_map)  # 不抛异常


def test_assert_no_lineage_leak_raises_on_dirty():
    _, st_map, _ = _data()
    from praxis_virtualcell.mdr_gnb.evaluators.lineage_split import SplitSpec
    dirty = SplitSpec(
        scheme="lineage_blocked", fold=0,
        train_ids=["g0", "g1"], test_ids=["g2"],  # g0/g1/g2 同 ST11 → 泄漏
        group_key="ST",
    )
    with pytest.raises(LineageLeakError):
        assert_no_lineage_leak(dirty, st_map)


def test_temporal_split_by_year():
    genome_ids, _, years = _data()
    spec = make_temporal_split(genome_ids, years, cutoff_year=2020)
    assert all(years[g] < 2020 for g in spec.train_ids)
    assert all(years[g] >= 2020 for g in spec.test_ids)
    assert spec.scheme == "temporal"
