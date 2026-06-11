"""TDD 测试 cheminformatics_toolkit run.py(staging praxis-dock env 真跑 rdkit)。

不依赖 pytest:`python test_run.py` 直接跑。
真实分子:阿司匹林 SMILES = CC(=O)Oc1ccccc1C(=O)O (C9H8O4, InChIKey BSYNRYMUTXBXSQ-...)。
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
RUN = HERE / "run.py"

# 阿司匹林(乙酰水杨酸)。Oracle 出处 = PubChem CID 2244(独立权威源,
# curl REST property 2026-06-11 核对,不经被测 RDKit 自证):
#   MolecularFormula = C9H8O4
#   MolecularWeight  = 180.16
#   InChIKey         = BSYNRYMUTXBXSQ-UHFFFAOYSA-N
# https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/property/...
ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"


def run_skill(inputs: dict) -> dict:
    p = subprocess.run(
        [sys.executable, str(RUN), "--inputs", json.dumps(inputs)],
        capture_output=True, text=True,
    )
    if p.returncode != 0:
        raise AssertionError(f"run.py rc={p.returncode} stderr={p.stderr[:300]}")
    return json.loads(p.stdout)


def test_canonical_smiles():
    # 非规范写法 → 规范化,且能再被解析
    r = run_skill({"smiles": "OC(=O)c1ccccc1OC(C)=O", "operations": ["canonical_smiles"]})
    assert r["ok"] is True, r
    assert r["results"]["canonical_smiles"], r["results"]


def test_inchikey_aspirin():
    r = run_skill({"smiles": ASPIRIN, "operations": ["inchikey"]})
    # InChIKey skeleton(前14)对确定结构稳定跨版本
    assert r["results"]["inchikey"].startswith("BSYNRYMUTXBXSQ"), r["results"]


def test_formula_aspirin():
    r = run_skill({"smiles": ASPIRIN, "operations": ["formula"]})
    assert r["results"]["formula"] == "C9H8O4", r["results"]


def test_inchi():
    r = run_skill({"smiles": ASPIRIN, "operations": ["inchi"]})
    assert r["results"]["inchi"].startswith("InChI="), r["results"]


def test_tanimoto_self():
    r = run_skill({"smiles": ASPIRIN, "smiles2": ASPIRIN, "operations": ["tanimoto"]})
    assert abs(r["results"]["tanimoto"] - 1.0) < 1e-6, r["results"]


def test_tanimoto_different():
    r = run_skill({"smiles": ASPIRIN, "smiles2": "c1ccccc1", "operations": ["tanimoto"]})
    assert 0 < r["results"]["tanimoto"] < 1, r["results"]


def test_substructure_benzene_match():
    r = run_skill({"smiles": ASPIRIN, "smarts": "c1ccccc1", "operations": ["substructure_match"]})
    assert r["results"]["substructure_match"]["match"] is True, r["results"]
    assert r["results"]["substructure_match"]["count"] >= 1, r["results"]


def test_substructure_no_phosphorus():
    r = run_skill({"smiles": ASPIRIN, "smarts": "[P]", "operations": ["substructure_match"]})
    assert r["results"]["substructure_match"]["match"] is False, r["results"]


def test_scaffold_benzene():
    # 阿司匹林 Murcko scaffold = 苯环
    r = run_skill({"smiles": ASPIRIN, "operations": ["scaffold"]})
    sc = r["results"]["scaffold"].lower()
    assert "c1ccccc1" in sc, r["results"]


def test_descriptors():
    r = run_skill({"smiles": ASPIRIN, "operations": ["descriptors"]})
    d = r["results"]["descriptors"]
    assert 170 < d["mol_weight"] < 190, d  # 阿司匹林 ~180.16
    assert d["num_rings"] == 1, d


def test_invalid_smiles_error():
    r = run_skill({"smiles": "not_a_valid_smiles_xyz", "operations": ["canonical_smiles"]})
    assert r["ok"] is False, r


def test_default_ops():
    r = run_skill({"smiles": ASPIRIN})
    assert r["ok"] is True, r
    assert "canonical_smiles" in r["results"], r["results"]


TESTS = [
    test_canonical_smiles, test_inchikey_aspirin, test_formula_aspirin, test_inchi,
    test_tanimoto_self, test_tanimoto_different, test_substructure_benzene_match,
    test_substructure_no_phosphorus, test_scaffold_benzene, test_descriptors,
    test_invalid_smiles_error, test_default_ops,
]

if __name__ == "__main__":
    failed = 0
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(TESTS) - failed}/{len(TESTS)} passed")
    sys.exit(1 if failed else 0)
