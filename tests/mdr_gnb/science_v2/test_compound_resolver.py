"""B2 gate:化合物标识符 → canonical SMILES 解析器 + 接进 run_mdr_query(线B 输入层)。

覆盖:
  1. classify_identifier:名称/CID/ChEMBL/DrugBank/SMILES 分类。
  2. 裸 SMILES 本地 canonical(无网,rdkit)。
  3. 名称/CID → PubChem(可注入 http_get,测试确定)→ canonical。
  4. **红线:解析失败诚实报错不伪造**——无网(http_get 抛)/查不到(404/空)→ ok=False,绝不编造 SMILES。
  5. 端到端:run_mdr_query 吃 compound(注入解析器)→ 走通 B1 sm_activity 预测。
  6. 端到端:解析失败 → 报告级 fail-closed 弃权(compound_resolution_failed),不产 MIC。
  7. task_parser 放行 compound;service.predict 的 activity 也算 prediction_available。

网络相关用例全用注入的假 http_get(不真联网,确定);真 PubChem 由手动验证覆盖。rdkit 用例 importorskip。
"""
import json

import pytest


# ---------------------------------------------------------------- 缝1:分类
def test_classify_identifier():
    from praxis_virtualcell.mdr_gnb.drug_agent.compound_resolver import classify_identifier
    assert classify_identifier("CHEMBL25") == "chembl_id"
    assert classify_identifier("chembl192") == "chembl_id"
    assert classify_identifier("DB00619") == "drugbank_id"
    assert classify_identifier("2764") == "pubchem_cid"
    assert classify_identifier("ciprofloxacin") == "name"       # 名称(非 SMILES)
    # 合法 SMILES 归类为 smiles(需 rdkit)
    pytest.importorskip("rdkit")
    assert classify_identifier("CCO") == "smiles"
    assert classify_identifier("c1ccccc1") == "smiles"


# ---------------------------------------------------------------- 缝2:裸 SMILES 本地 canonical
def test_resolve_smiles_local_no_network():
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.drug_agent.compound_resolver import resolve_compound

    def _no_net(url, timeout):        # 若碰网络直接失败(证明裸 SMILES 不联网)
        raise AssertionError("裸 SMILES 不应联网")
    r = resolve_compound("OCC", http_get=_no_net)     # 乙醇非 canonical 写法
    assert r["ok"] is True
    assert r["input_kind"] == "smiles"
    assert r["source"] == "rdkit_local"
    # canonical 一致:OCC 与 CCO 应规范到同一串
    r2 = resolve_compound("CCO", http_get=_no_net)
    assert r["smiles"] == r2["smiles"]


def test_resolve_pubchem_malformed_smiles_fails():
    # PubChem 返回非法 SMILES → RDKit 规范化失败 → rdkit_parse_failed,诚实不伪造
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.drug_agent.compound_resolver import resolve_compound
    body = json.dumps({"PropertyTable": {"Properties": [{"CID": 1, "SMILES": "C(C(C("}]}})
    r = resolve_compound("weirdname", http_get=lambda u, t: (200, body))
    assert r["ok"] is False
    assert r["reason"] == "rdkit_parse_failed"
    assert r.get("smiles") is None            # 绝不返回编造/半成品 SMILES


def test_resolve_empty_and_none_honest():
    # 空/None/空白标识符 → 诚实报错不伪造(不返回空串 SMILES 当成功)
    from praxis_virtualcell.mdr_gnb.drug_agent.compound_resolver import resolve_compound
    for bad in ("", "   ", None):
        r = resolve_compound(bad, http_get=lambda u, t: (200, "{}"))
        assert r["ok"] is False
        assert r.get("smiles") is None


# ---------------------------------------------------------------- 缝3:名称/CID → PubChem(注入)
def _fake_pubchem(smiles="C1CC1N2C=C(C(=O)C3=CC(=C(C=C32)N4CCNCC4)F)C(=O)O"):
    def _get(url, timeout):
        body = json.dumps({"PropertyTable": {"Properties": [{"CID": 2764, "SMILES": smiles}]}})
        return (200, body)
    return _get


def test_resolve_name_via_pubchem():
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.drug_agent.compound_resolver import resolve_compound
    r = resolve_compound("ciprofloxacin", http_get=_fake_pubchem())
    assert r["ok"] is True
    assert r["input_kind"] == "name"
    assert r["source"] == "pubchem"
    assert r["smiles"]        # 非空 canonical


def test_resolve_cid_via_pubchem():
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.drug_agent.compound_resolver import resolve_compound
    r = resolve_compound("2764", http_get=_fake_pubchem())
    assert r["ok"] is True and r["input_kind"] == "pubchem_cid"


# ---------------------------------------------------------------- 缝4:红线——失败诚实不伪造
def test_resolve_network_error_honest():
    from praxis_virtualcell.mdr_gnb.drug_agent.compound_resolver import resolve_compound

    def _boom(url, timeout):
        raise OSError("network down")
    r = resolve_compound("ciprofloxacin", http_get=_boom)
    assert r["ok"] is False
    assert r["reason"] == "network_error"
    assert "smiles" not in r or r.get("smiles") is None    # 绝不编造


def test_resolve_not_found_honest():
    from praxis_virtualcell.mdr_gnb.drug_agent.compound_resolver import resolve_compound
    r = resolve_compound("不存在的化合物xyz", http_get=lambda u, t: (404, "NotFound"))
    assert r["ok"] is False
    assert r["reason"] == "not_found"
    r2 = resolve_compound("weirdname", http_get=lambda u, t: (200, '{"Fault":{}}'))  # 200 但无 SMILES
    assert r2["ok"] is False


# ---------------------------------------------------------------- 缝5-6:接进 run_mdr_query
_TRAIN_SMILES = [
    "c1ccccc1", "c1ccccc1C", "c1ccccc1CC", "c1ccc(cc1)O", "c1ccc(cc1)N",
    "c1ccc2ccccc2c1", "c1ccc2c(c1)cccc2C", "c1ccc(cc1)c1ccccc1",
    "CCO", "CCCO", "CCCCO", "CC(=O)O", "CCN", "CCCN", "CC(C)O", "CCCCCC",
]
_TRAIN_Y = [-1.0, -1.0, -0.8, -1.2, -0.9, -1.5, -1.4, -1.6,
            2.0, 2.1, 2.2, 1.8, 2.0, 2.1, 1.9, 2.3]


def _wire_tiny_model(tmp_path, monkeypatch):
    from praxis_virtualcell.mdr_gnb.predictors.small_molecule_model import SmallMoleculeModel
    import praxis_virtualcell.mdr_gnb.predictors.default_registry as dr
    monkeypatch.setattr(dr, "_MODELS_ROOT", tmp_path)
    dr._load_test_sm_activity.cache_clear()
    art = tmp_path / "escherichia_coli" / "sm_activity__mic.joblib"
    art.parent.mkdir(parents=True, exist_ok=True)
    m = SmallMoleculeModel(n_bits=512, radius=2, ood_threshold=0.3, n_estimators=50)
    m.fit(_TRAIN_SMILES, _TRAIN_Y)
    m.save(art)


def _compound_raw(compound):
    return {"species": "escherichia_coli", "compound": compound,
            "drug_panel": [{"drug": "novel_compound_X", "drug_class": "novel_compound"}],
            "requested_outputs": ["activity"]}


def test_pipeline_compound_identifier_resolves(tmp_path, monkeypatch):
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire_tiny_model(tmp_path, monkeypatch)

    # 注入解析器:把名称解析成训练集内的芳香化合物(在分布内,不 OOD)
    def _resolve(identifier):
        return {"ok": True, "smiles": "c1ccccc1", "input_kind": "name", "source": "pubchem"}
    out = run_mdr_query(_compound_raw("benzene"), seed_task_id="cr1", resolve=_resolve)
    rep = out["report"]
    assert rep["output_kind"] == "sm_activity"
    assert rep["abstained"] is False
    assert rep["activity"] is not None


def test_pipeline_compound_resolution_failure_abstains(tmp_path, monkeypatch):
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire_tiny_model(tmp_path, monkeypatch)

    def _fail(identifier):
        return {"ok": False, "reason": "not_found", "input_kind": "name"}
    rep = run_mdr_query(_compound_raw("不存在的分子"), seed_task_id="cr2", resolve=_fail)["report"]
    assert rep["abstained"] is True
    assert "compound_resolution_failed" in rep["abstain_reasons"]
    assert rep["activity"] is None                # 不伪造


def test_pipeline_smiles_still_works_without_resolver(tmp_path, monkeypatch):
    # B1 兼容:直接给 smiles 不触发解析(resolve 不应被调用)
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire_tiny_model(tmp_path, monkeypatch)

    def _resolve(identifier):
        raise AssertionError("给了 smiles 不应调用解析器")
    raw = {"species": "escherichia_coli", "smiles": "c1ccccc1",
           "drug_panel": [{"drug": "x", "drug_class": "novel_compound"}],
           "requested_outputs": ["activity"]}
    rep = run_mdr_query(raw, seed_task_id="cr3", resolve=_resolve)["report"]
    assert rep["abstained"] is False and rep["activity"] is not None


# ---------------------------------------------------------------- 缝7:task_parser + service
def test_task_parser_allows_compound():
    from praxis_virtualcell.mdr_gnb.coordinator.task_parser import parse_task
    msg = parse_task({"species": "escherichia_coli", "compound": "ciprofloxacin",
                      "sir": "R"},                       # 裁决字段仍剥离
                     task_id="t")
    assert msg.compound == "ciprofloxacin"
    assert any("adjudication" in b for b in msg.boundaries)   # sir 被剥离告警


def test_service_activity_prediction_available(tmp_path, monkeypatch):
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.api import service
    import praxis_virtualcell.mdr_gnb.drug_agent.compound_resolver as cr
    _wire_tiny_model(tmp_path, monkeypatch)
    # 在解析器源头注入(_default_resolve 惰性 import resolve_compound → patch 它,不真联网)
    monkeypatch.setattr(cr, "resolve_compound",
                        lambda ident, **kw: {"ok": True, "smiles": "c1ccccc1",
                                             "input_kind": "name", "source": "pubchem"})
    res = service.predict(_compound_raw("benzene"))
    assert res["response"]["prediction_available"] is True    # activity 也算有预测
