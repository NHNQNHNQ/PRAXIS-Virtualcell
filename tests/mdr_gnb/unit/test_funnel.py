"""漏斗表测试(NCBI-only 适配):逐级 N 单调不增、阶段标签、去重 isolate×drug、按 ST 去克隆。

决策变更(2026-07-03):项目 NCBI-only。NCBI Pathogen Detection 只有 S/I/R(无定量 MIC),
故漏斗级不再有 has_quantitative_mic / breakpoint_harmonized,改为:
  total -> has_ast -> valid_sir -> dedup_isolate_drug -> declonalized -> single_species_single_drug
"""
from praxis_virtualcell.mdr_gnb.evaluators.funnel import build_funnel, FunnelRow, STAGES


def _sample_rows():
    # 模拟 ncbi_amr_phenotypes.tsv 行:genome_id=asm_acc、antibiotic、resistant_phenotype=S/I/R
    amr = [
        {"genome_id": "g1", "antibiotic": "meropenem", "resistant_phenotype": "R"},    # 有效, ST11
        {"genome_id": "g2", "antibiotic": "meropenem", "resistant_phenotype": "S"},    # 有效, ST258
        {"genome_id": "g3", "antibiotic": "meropenem", "resistant_phenotype": "ND"},   # 非 SIR, valid_sir 级丢弃
        {"genome_id": "g4", "antibiotic": "meropenem", "resistant_phenotype": "R"},    # 有效, ST11(g1 的克隆)
        {"genome_id": "g1", "antibiotic": "meropenem", "resistant_phenotype": "R"},    # g1 重复提交(dedup 去掉)
        {"genome_id": "g5", "antibiotic": "ceftriaxone", "resistant_phenotype": "R"},  # 别的药(meropenem 漏斗排除)
    ]
    st_map = {"g1": "ST11", "g2": "ST258", "g3": "ST11", "g4": "ST11", "g5": "ST405"}
    return amr, st_map


def test_funnel_rows_monotonic_nonincreasing():
    amr, st_map = _sample_rows()
    rows = build_funnel("klebsiella_pneumoniae", "meropenem", amr, st_map)
    ns = [r.n_records for r in rows]
    assert ns == sorted(ns, reverse=True), f"漏斗 N 非单调不增:{ns}"


def test_funnel_stage_labels():
    amr, st_map = _sample_rows()
    rows = build_funnel("klebsiella_pneumoniae", "meropenem", amr, st_map)
    assert [r.stage for r in rows] == STAGES


def test_valid_sir_drops_non_sir():
    amr, st_map = _sample_rows()
    rows = build_funnel("klebsiella_pneumoniae", "meropenem", amr, st_map)
    has_ast = next(r for r in rows if r.stage == "has_ast")
    valid = next(r for r in rows if r.stage == "valid_sir")
    # has_ast 含 g3(ND)共 5 条;valid_sir 丢 g3 剩 4 条
    assert has_ast.n_records == 5
    assert valid.n_records == 4


def test_dedup_isolate_drug_counts_unique_isolate():
    amr, st_map = _sample_rows()
    rows = build_funnel("klebsiella_pneumoniae", "meropenem", amr, st_map)
    dedup = next(r for r in rows if r.stage == "dedup_isolate_drug")
    # 有效 SIR 的 g1,g2,g4,g1(重复)-> 去重 isolate×drug = {g1,g2,g4} = 3
    assert dedup.n_records == 3


def test_declonalization_counts_unique_st():
    amr, st_map = _sample_rows()
    rows = build_funnel("klebsiella_pneumoniae", "meropenem", amr, st_map)
    declon = next(r for r in rows if r.stage == "declonalized")
    # g1,g2,g4 -> ST{ST11,ST258,ST11} -> 去克隆后唯一 ST=2
    assert declon.n_strains == 2


def test_unknown_st_not_merged():
    # ST 缺失/unknown 的每株各计为独立株(不合并),避免虚高去克隆
    amr = [
        {"genome_id": "x1", "antibiotic": "meropenem", "resistant_phenotype": "R"},
        {"genome_id": "x2", "antibiotic": "meropenem", "resistant_phenotype": "R"},
    ]
    st_map = {}  # 两株都 unknown ST
    rows = build_funnel("klebsiella_pneumoniae", "meropenem", amr, st_map)
    declon = next(r for r in rows if r.stage == "declonalized")
    assert declon.n_strains == 2  # unknown 不合并


def test_empty_and_null_genome_id_not_inflating_strains():
    # 空/NULL genome_id 无 assembly 标识不计为株;未定型 isolate 按 gid 去重(不按行膨胀)
    amr = [
        {"genome_id": "", "antibiotic": "meropenem", "resistant_phenotype": "R"},
        {"genome_id": "NULL", "antibiotic": "meropenem", "resistant_phenotype": "S"},
        {"genome_id": "gA", "antibiotic": "meropenem", "resistant_phenotype": "R"},
        {"genome_id": "gA", "antibiotic": "meropenem", "resistant_phenotype": "R"},  # 同 isolate 重复行
    ]
    st_map = {}  # gA 未定型
    rows = build_funnel("x", "meropenem", amr, st_map)
    total = next(r for r in rows if r.stage == "total")
    # 只有 gA 一个真实 isolate(未定型);空/NULL 不计、重复不膨胀 → 1
    assert total.n_strains == 1


def test_funnelrow_is_dataclass_with_contract_fields():
    r = FunnelRow(stage="total", n_records=10, n_strains=5, note="x")
    assert (r.stage, r.n_records, r.n_strains, r.note) == ("total", 10, 5, "x")
