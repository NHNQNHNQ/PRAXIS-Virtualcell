# praxis_virtualcell/mdr_gnb/databases/species_registry.py
"""首批 6 + 固有耐药 4 共 10 物种注册表(命名/目录/taxon 锁定,契约 D6)。

dir_name 与契约 agents/<species>/ 目录名严格一致;taxon_id 用 NCBI Taxonomy species-level id,
BV-BRC genome 检索用 taxon_lineage_ids 命中该 id 的基因组。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SpeciesSpec:
    dir_name: str          # 契约锁定的目录名(snake_case)
    scientific_name: str   # BV-BRC / NCBI 学名
    taxon_id: int          # NCBI Taxonomy species-level id
    intrinsic_resistant: bool = False  # 固有耐药/二期物种(折点/规则层特殊处理)
    aliases: tuple[str, ...] = field(default_factory=tuple)


# NCBI Taxonomy species-level id(已核实):
#   562 E. coli;573 K. pneumoniae;470 A. baumannii;287 P. aeruginosa;
#   550 Enterobacter cloacae(complex 以 species 锚点);28901 Salmonella enterica;
#   40324 Stenotrophomonas maltophilia;615 Serratia marcescens;
#   584 Proteus mirabilis;582 Morganella morganii
SPECIES_REGISTRY: tuple[SpeciesSpec, ...] = (
    SpeciesSpec("escherichia_coli", "Escherichia coli", 562),
    SpeciesSpec("klebsiella_pneumoniae", "Klebsiella pneumoniae", 573),
    SpeciesSpec("acinetobacter_baumannii", "Acinetobacter baumannii", 470),
    SpeciesSpec("pseudomonas_aeruginosa", "Pseudomonas aeruginosa", 287),
    SpeciesSpec(
        "enterobacter_cloacae", "Enterobacter cloacae", 550,
        aliases=("Enterobacter cloacae complex",),
    ),
    SpeciesSpec("salmonella_enterica", "Salmonella enterica", 28901),
    SpeciesSpec(
        "stenotrophomonas_maltophilia", "Stenotrophomonas maltophilia", 40324,
        intrinsic_resistant=True,
    ),
    SpeciesSpec(
        "serratia_marcescens", "Serratia marcescens", 615,
        intrinsic_resistant=True,
    ),
    SpeciesSpec(
        "proteus_mirabilis", "Proteus mirabilis", 584,
        intrinsic_resistant=True,
    ),
    SpeciesSpec(
        "morganella_morganii", "Morganella morganii", 582,
        intrinsic_resistant=True,
    ),
)

INTRINSIC_RESISTANT_DIRS: frozenset[str] = frozenset(
    s.dir_name for s in SPECIES_REGISTRY if s.intrinsic_resistant
)

# 反查索引:dir_name / scientific_name / alias(小写)→ SpeciesSpec
_INDEX: dict[str, SpeciesSpec] = {}
for _s in SPECIES_REGISTRY:
    _INDEX[_s.dir_name.lower()] = _s
    _INDEX[_s.scientific_name.lower()] = _s
    for _a in _s.aliases:
        _INDEX[_a.lower()] = _s


def get_species(key: str) -> SpeciesSpec:
    """按 dir_name / 学名 / 别名(大小写不敏感)反查。"""
    try:
        return _INDEX[key.lower()]
    except KeyError as e:
        raise KeyError(f"未知物种键:{key!r}(须为 10 物种之一的 dir_name/学名/别名)") from e


def iter_species():
    """按注册顺序迭代(前 6 首批,后 4 固有耐药二期)。"""
    return iter(SPECIES_REGISTRY)
