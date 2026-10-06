"""谱系分组切分:按 ST/克隆群分块,杜绝谱系跨 train/test 泄漏(G1)。

关键防泄漏:同一 ST(克隆群)绝不跨 train/test;ST=unknown 单列不进 fold。
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from sklearn.model_selection import GroupKFold


@dataclass
class SplitSpec:
    """一折切分规格(字段名锁定,G0 契约测试依赖默认值)。"""

    scheme: str  # lineage_blocked | temporal | random
    fold: int
    train_ids: list[str] = field(default_factory=list)
    test_ids: list[str] = field(default_factory=list)
    group_key: str = ""


def make_lineage_splits(
    genome_ids: list[str],
    st_map: dict[str, str],
    n_splits: int = 5,
    group_key: str = "ST",
    cc_map: dict[str, str] | None = None,
) -> list[SplitSpec]:
    """GroupKFold 按 ST/克隆复合体分组;ST=unknown 剔除出 fold(单列另存)。

    cc_map=None(默认)→ 按精确 ST 分组(旧行为,向后兼容,逐字不变)。
    传入 cc_map(ST→CC)→ 分组键改用 CC:同一克隆复合体(如 CC258 的
    {ST258,ST11,...})整组同侧,杜绝把一个近缘克隆群切成多组的跨折泄漏;
    无 CC 映射的 ST(单例/缺映射)诚实回退按该 ST 自身分组。
    """
    usable = [
        g for g in genome_ids
        if st_map.get(g) and str(st_map[g]).lower() != "unknown"
    ]
    if cc_map:
        groups = [cc_map.get(st_map[g], st_map[g]) for g in usable]
    else:
        groups = [st_map[g] for g in usable]
    n_groups = len(set(groups))
    if n_groups < 2:
        return []  # 组数不足以做 GroupKFold(至少需 2 组)
    if n_groups < n_splits:
        n_splits = n_groups
    gkf = GroupKFold(n_splits=n_splits)
    specs: list[SplitSpec] = []
    for fold, (tr_idx, te_idx) in enumerate(gkf.split(usable, groups=groups)):
        specs.append(SplitSpec(
            scheme="lineage_blocked",
            fold=fold,
            train_ids=[usable[i] for i in tr_idx],
            test_ids=[usable[i] for i in te_idx],
            group_key=group_key,
        ))
    return specs


def make_temporal_split(
    genome_ids: list[str],
    year_map: dict[str, int],
    cutoff_year: int,
) -> SplitSpec:
    """按 collection_year 时间切分:< cutoff 训练,>= cutoff 测试。无年份的丢弃。"""
    train_ids, test_ids = [], []
    for g in genome_ids:
        y = year_map.get(g)
        if y is None:
            continue
        (train_ids if y < cutoff_year else test_ids).append(g)
    return SplitSpec(
        scheme="temporal",
        fold=0,
        train_ids=train_ids,
        test_ids=test_ids,
        group_key="year",
    )


def get_unknown_st_ids(genome_ids: list[str], st_map: dict[str, str]) -> list[str]:
    """返回 ST=unknown 的样本(单列,供下游 abstain/单独处理)。"""
    return [
        g for g in genome_ids
        if not st_map.get(g) or str(st_map[g]).lower() == "unknown"
    ]


def save_splits(
    species_dir: str,
    drug: str,
    specs: list[SplitSpec],
    unknown_ids: list[str],
    out_root: Path,
) -> Path:
    """存 splits/<species>/<drug>.json(含各 fold + unknown 单列清单)。"""
    out_dir = out_root / "splits" / species_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{drug}.json"
    payload = {
        "species": species_dir,
        "drug": drug,
        "folds": [asdict(s) for s in specs],
        "unknown_st_ids": unknown_ids,  # 单列,不参与 fold
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path
