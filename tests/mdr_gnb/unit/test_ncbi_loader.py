# praxis_virtualcell/mdr_gnb/tests/test_ncbi_loader.py
"""NCBI Pathogen Detection 加载器解析核心测试(纯解析,不联网)。

覆盖:AST_phenotypes(drug=SIR)展平、scientific_name 过滤(属级混合目录)、
ND/DD/NS 丢弃、契约字段对齐(measurement 等留空、laboratory_typing_method=SIR)。
"""
from praxis_virtualcell.mdr_gnb.databases.ncbi_loader import (
    flatten_metadata_rows, AMR_FIELDS, OUTPUT_FIELDS, NCBI_ORGANISM,
    _pdg_sort_key, extract_unique_asm_accs,
)


def test_extract_unique_asm_accs_dedup_preserves_order(tmp_path):
    tsv = tmp_path / "amr.tsv"
    tsv.write_text(
        "genome_id\tantibiotic\tresistant_phenotype\n"
        "GCA_1\tmeropenem\tR\n"
        "GCA_2\tmeropenem\tS\n"
        "GCA_1\tamikacin\tI\n"  # 重复 GCA_1(同菌株多药)不应重复出现
        "\tcolistin\tR\n",       # genome_id 为空应跳过
        encoding="utf-8",
    )
    accs = extract_unique_asm_accs(tsv)
    assert accs == ["GCA_1", "GCA_2"]


def test_pdg_version_sorted_numerically_not_lexically():
    # 回归:字典序会把 .836 当成比 .2454 新(错),数值序才对
    pdgs = ["PDG000000012.836", "PDG000000012.2454", "PDG000000012.90"]
    newest = sorted(pdgs, key=_pdg_sort_key)[-1]
    assert newest == "PDG000000012.2454"

# 模拟 NCBI metadata.tsv(仅列出被引用的列,解析按列名而非位置)
HEADER = [
    "target_acc", "asm_acc", "biosample_acc", "scientific_name",
    "AST_phenotypes", "AMR_genotypes",
]
ROWS = [
    # KP,有 AST:4 个有效 SIR + 1 个 ND(应丢)
    ["PDT000015887.2", "GCA_000417105.1", "SAMN02141969", "Klebsiella pneumoniae",
     "amikacin=I,meropenem=R,colistin=R,tigecycline=S,cefepime=ND", "blaKPC-2,blaSHV"],
    # K. oxytoca:属级混合目录里的非目标种,应被 scientific_name 过滤掉
    ["PDT000099999.1", "GCA_000999999.1", "SAMN09999999", "Klebsiella oxytoca",
     "meropenem=S", "blaOXY"],
    # KP,AST 为 NULL:0 条
    ["PDT000012345.1", "GCA_000123456.1", "SAMN01234567", "Klebsiella pneumoniae",
     "NULL", "fosA"],
]


def test_flatten_filters_species_and_drops_non_sir():
    out = flatten_metadata_rows(HEADER, ROWS, scientific_prefix="Klebsiella pneumoniae")
    # 仅第 1 行(KP)产出,cefepime=ND 丢弃 → 4 条
    assert len(out) == 4
    drugs = sorted(r["antibiotic"] for r in out)
    assert drugs == ["amikacin", "colistin", "meropenem", "tigecycline"]


def test_contract_fields_aligned():
    out = flatten_metadata_rows(HEADER, ROWS, scientific_prefix="Klebsiella pneumoniae")
    r = next(x for x in out if x["antibiotic"] == "meropenem")
    # 契约字段:SIR 值、来源标记、MIC 相关列留空
    assert r["resistant_phenotype"] == "R"
    assert r["laboratory_typing_method"] == "SIR"
    assert r["measurement"] == "" and r["measurement_unit"] == "" and r["measurement_sign"] == ""
    assert r["genome_id"] == "GCA_000417105.1"
    assert r["genome_name"] == "Klebsiella pneumoniae"
    # 额外列供 join / 基因型特征
    assert r["ncbi_biosample_acc"] == "SAMN02141969"
    assert r["ncbi_amr_genotypes"] == "blaKPC-2,blaSHV"
    # 输出字段前 8 位与 bvbrc AMR_FIELDS 完全一致(可直接 concat)
    assert OUTPUT_FIELDS[: len(AMR_FIELDS)] == AMR_FIELDS


def test_no_ast_column_or_empty_yields_nothing():
    # 无 AST_phenotypes 列时安全返回空,不抛异常
    out = flatten_metadata_rows(
        ["asm_acc", "scientific_name"],
        [["GCA_1", "Klebsiella pneumoniae"]],
        scientific_prefix="Klebsiella pneumoniae",
    )
    assert out == []


def test_anchor_species_have_organism_mapping():
    # 锚点物种必须有 NCBI organism 目录映射
    assert NCBI_ORGANISM["escherichia_coli"] == "Escherichia_coli_Shigella"
    assert NCBI_ORGANISM["klebsiella_pneumoniae"] == "Klebsiella"
