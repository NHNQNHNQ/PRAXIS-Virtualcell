# praxis_virtualcell/mdr_gnb/tests/test_species_registry.py
"""物种注册表测试:锁定 10 物种规范名/目录名/taxon 与固有耐药标记。"""
from praxis_virtualcell.mdr_gnb.databases.species_registry import (
    SPECIES_REGISTRY, get_species, iter_species, INTRINSIC_RESISTANT_DIRS,
)


def test_registry_has_ten_species():
    assert len(SPECIES_REGISTRY) == 10


def test_first_batch_six_present():
    dirs = {s.dir_name for s in iter_species()}
    for d in [
        "acinetobacter_baumannii", "klebsiella_pneumoniae", "escherichia_coli",
        "pseudomonas_aeruginosa", "enterobacter_cloacae", "salmonella_enterica",
    ]:
        assert d in dirs


def test_intrinsic_resistant_flagged():
    # S. maltophilia 等 4 个二期固有耐药物种须标记 intrinsic_resistant=True
    assert INTRINSIC_RESISTANT_DIRS == {
        "stenotrophomonas_maltophilia", "serratia_marcescens",
        "proteus_mirabilis", "morganella_morganii",
    }
    for d in INTRINSIC_RESISTANT_DIRS:
        assert get_species(d).intrinsic_resistant is True


def test_taxon_ids_are_positive_int():
    for s in iter_species():
        assert isinstance(s.taxon_id, int) and s.taxon_id > 0


def test_get_species_by_dir_and_alias():
    ec = get_species("escherichia_coli")
    assert ec.taxon_id == 562
    # BV-BRC 物种名别名可反查
    assert get_species("Escherichia coli").dir_name == "escherichia_coli"
