"""工具链接线(阶段7):AMRFinderPlus/RGI 解析器离线单测 + 工具集成测(缺工具 skip)。"""
import shutil

import pytest

from praxis_virtualcell.mdr_gnb.databases.amrfinder_runner import parse_amrfinder_tsv, run_amrfinder
from praxis_virtualcell.mdr_gnb.databases.card_loader import parse_rgi_txt

_AMRFINDER_TSV = (
    "Protein identifier\tContig id\tGene symbol\tScope\tElement type\tClass\tSubclass\tMethod\n"
    "NA\tc1\tblaKPC-2\tcore\tAMR\tBETA-LACTAM\tCARBAPENEM\tEXACTX\n"
    "NA\tc2\tgyrA_S83I\tcore\tPOINT\tQUINOLONE\tQUINOLONE\tPOINTX\n"
    "NA\tc3\tompK36_D135DGD\tcore\tPOINT\tEFFLUX\tEFFLUX\tPOINTX\n"
)
_RGI_TXT = (
    "ORF_ID\tContig\tBest_Hit_ARO\tARO\tDrug Class\tResistance Mechanism\tAMR Gene Family\n"
    "orf1\tc1\tKPC-2\t3000001\tcarbapenem; cephalosporin\tantibiotic inactivation\tbeta-lactamase\n"
    "orf2\tc2\tOqxA\t3000002\tfluoroquinolone\tantibiotic efflux\tRND efflux\n"
)


def test_parse_amrfinder_genes_and_mutations():
    d = parse_amrfinder_tsv(_AMRFINDER_TSV)
    assert d["genes"] == ["blaKPC-2"]
    assert set(d["mutations"]) == {"gyrA_S83I=POINT", "ompK36_D135DGD=POINT"}
    # ncbi_amr_genotypes 对齐训练格式(可直接喂 parse_genotypes / augmented_features)
    assert "blaKPC-2" in d["ncbi_amr_genotypes"] and "gyrA_S83I=POINT" in d["ncbi_amr_genotypes"]
    assert d["n_hits"] == 3


def test_amrfinder_output_feeds_model_featurizer():
    from praxis_virtualcell.mdr_gnb.predictors.mechanism_features import augmented_features
    geno = parse_amrfinder_tsv(_AMRFINDER_TSV)["ncbi_amr_genotypes"]
    feats = augmented_features(geno)
    assert "gene=blaKPC-2" in feats
    assert "mut=ompK36_D135DGD" in feats
    assert "mech=carbapenemase" in feats and "mech=porin_ompK36_loss" in feats


def test_parse_rgi_aro_and_classes():
    d = parse_rgi_txt(_RGI_TXT)
    assert set(d["aro_hits"]) == {"KPC-2", "OqxA"}
    assert "carbapenem" in d["drug_classes"] and "fluoroquinolone" in d["drug_classes"]
    assert "antibiotic efflux" in d["mechanisms"]


def test_parse_empty_safe():
    assert parse_amrfinder_tsv("")["n_hits"] == 0
    assert parse_rgi_txt("")["aro_hits"] == []


@pytest.mark.skipif(shutil.which("amrfinder") is None, reason="amrfinder 未装(53 上跑)")
def test_run_amrfinder_integration(tmp_path):
    # 集成:需装 amrfinder + DB;本地无则 skip。构造最小 FASTA。
    fa = tmp_path / "g.fna"
    fa.write_text(">c1\n" + "ATGC" * 100 + "\n")
    out = run_amrfinder(str(fa), db_version="test", species="escherichia_coli")
    assert "ncbi_amr_genotypes" in out and out["db_version"] == "test"
