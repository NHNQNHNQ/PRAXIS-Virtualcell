"""PredictRequest.to_raw():线B 三方向共用一个请求体。
红线:SIR 请求(不带 compound/smiles/sequence)的 to_raw 与旧形状逐字相等 → task_id 不漂移;
线B 字段(compound/smiles/sequence)非空才进 raw,空则不进(向后兼容 + 确定性)。"""
from praxis_virtualcell.mdr_gnb.api.schemas import PredictRequest


def test_sir_request_raw_unchanged():
    """纯 SIR 请求:to_raw 只含 4 键,不因新增字段而多出 compound/smiles/sequence。"""
    req = PredictRequest(
        species="klebsiella_pneumoniae",
        drug_panel=[{"drug": "meropenem", "drug_class": "carbapenem"}],
        requested_outputs=["SIR"],
        amr_profile={"blaKPC-2": True},
    )
    raw = req.to_raw()
    assert set(raw.keys()) == {"species", "drug_panel", "requested_outputs", "amr_profile"}
    assert raw["amr_profile"] == {"blaKPC-2": True}


def test_compound_smiles_preserved_in_raw():
    """小分子请求:smiles 必须进 raw(否则被剥离 → 后端拿不到结构 → 误弃权)。"""
    req = PredictRequest(
        species="escherichia_coli",
        smiles="CCO",
        drug_panel=[{"drug": "probe", "drug_class": "novel_compound"}],
        requested_outputs=["activity"],
    )
    raw = req.to_raw()
    assert raw["smiles"] == "CCO"
    assert "compound" not in raw          # 未给的字段不进 raw
    assert "sequence" not in raw


def test_compound_identifier_preserved_in_raw():
    """化合物名/CID/ChEMBL 标识符:compound 进 raw,交后端解析器。"""
    req = PredictRequest(
        species="escherichia_coli",
        compound="ciprofloxacin",
        drug_panel=[{"drug": "ciprofloxacin", "drug_class": "novel_compound"}],
        requested_outputs=["activity"],
    )
    raw = req.to_raw()
    assert raw["compound"] == "ciprofloxacin"
    assert "smiles" not in raw


def test_peptide_sequence_preserved_in_raw():
    """肽请求:sequence 进 raw。"""
    req = PredictRequest(
        species="escherichia_coli",
        sequence="GIGKFLHSAKKFGKAFVGEIMNS",
        drug_panel=[{"drug": "magainin-2", "drug_class": "antimicrobial_peptide"}],
        requested_outputs=["peptide_activity"],
    )
    raw = req.to_raw()
    assert raw["sequence"] == "GIGKFLHSAKKFGKAFVGEIMNS"
    assert "smiles" not in raw
    assert "compound" not in raw


def test_empty_line_b_fields_not_in_raw():
    """空字符串的线B字段不进 raw(等价未给 → task_id 与纯 SIR 一致)。"""
    with_empty = PredictRequest(
        species="escherichia_coli", compound="", smiles="", sequence="",
        drug_panel=[{"drug": "meropenem", "drug_class": "carbapenem"}],
        requested_outputs=["SIR"],
    ).to_raw()
    assert set(with_empty.keys()) == {"species", "drug_panel", "requested_outputs", "amr_profile"}
