"""9.1 /species:10 物种框架 + 支持状态(5 有模型 / 5 fail-closed)。"""

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


def test_species_lists_ten(client):
    r = client.get("/species")
    assert r.status_code == 200
    species = r.json()["species"]
    assert len(species) == 10
    names = [s["name"] for s in species]
    # 顺序确定
    assert names[0] == "escherichia_coli"


def test_species_support_split_5_5(client):
    species = client.get("/species").json()["species"]
    supported = [s for s in species if s["supported"]]
    unsupported = [s for s in species if not s["supported"]]
    assert len(supported) == 5
    assert len(unsupported) == 5
    # 5 有模型物种
    assert {s["name"] for s in supported} == {
        "escherichia_coli", "klebsiella_pneumoniae", "pseudomonas_aeruginosa",
        "acinetobacter_baumannii", "salmonella_enterica",
    }


def test_supported_species_has_live_catalog_and_separate_evidence_counts(client):
    species = {s["name"]: s for s in client.get("/species").json()["species"]}
    kp = species["klebsiella_pneumoniae"]
    assert kp["supported"] is True
    assert kp["n_declared_models"] == 37
    assert kp["n_ready_models"] == 37
    assert kp["n_validated_models"] == 0
    assert kp["n_evidence_combos"] > 0      # evidence_tiers 有收录
    assert kp["n_strong"] >= 0


def test_unsupported_species_flagged_intrinsic(client):
    species = {s["name"]: s for s in client.get("/species").json()["species"]}
    steno = species["stenotrophomonas_maltophilia"]
    assert steno["supported"] is False
    assert steno["n_declared_models"] == 0
    assert steno["n_ready_models"] == 0
    assert steno["n_validated_models"] == 0
    assert steno["intrinsic_resistance"] is True
    assert steno["n_evidence_combos"] == 0
