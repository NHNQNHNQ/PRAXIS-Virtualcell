"""TDD 测试 seq_toolkit run.py(在 staging praxis-protein env 真跑 biopython)。

不依赖 pytest:`python test_run.py` 直接跑(env 不一定装 pytest)。
RED:run.py 不存在/不全 → 全 FAIL。GREEN:run.py 写好 → 全 PASS。
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
RUN = HERE / "run.py"

# Oracle 出处(均独立于被测 biopython,可第一性原理手工核对):
#   translate:NCBI 标准遗传密码表(translation table 1)
#     ATG=Met(M) GCC=Ala(A) TGT=Cys(C) TAA=Stop(*) → ATGGCCTGTTAA → "MAC*"
#   reverse_complement:Watson-Crick 配对 A↔T G↔C + 反向 → ATGC → 互补 TACG → 反向 GCAT
#   gc_content:GGCCATAT 中 G/C 共 4 个 ÷ 8 = 50.0%
#   pairwise identity:相同序列=100%;MKLVWWQEFH vs ...EFA 差 1/10 残基 = 90%
#   protein MW/pI:用宽松断言(>1000 Da / 0<pI<14),不固化精确值(避免记忆误差)


def run_skill(inputs: dict) -> dict:
    p = subprocess.run(
        [sys.executable, str(RUN), "--inputs", json.dumps(inputs)],
        capture_output=True, text=True,
    )
    if p.returncode != 0:
        raise AssertionError(f"run.py rc={p.returncode} stderr={p.stderr[:300]}")
    return json.loads(p.stdout)


def test_translate_dna():
    r = run_skill({"sequence": "ATGGCCTGTTAA", "operations": ["translate"]})
    assert r["ok"] is True, r
    # ATG=M GCC=A TGT=C TAA=*
    assert r["results"]["translate"] == "MAC*", r["results"]["translate"]


def test_reverse_complement():
    r = run_skill({"sequence": "ATGC", "operations": ["reverse_complement"]})
    assert r["results"]["reverse_complement"] == "GCAT", r["results"]


def test_gc_content():
    r = run_skill({"sequence": "GGCCATAT", "operations": ["gc_content"]})
    assert abs(r["results"]["gc_content"] - 50.0) < 1e-6, r["results"]


def test_auto_detect_dna():
    r = run_skill({"sequence": "ATGCATGCAT"})
    assert r["seq_type_detected"] == "dna", r


def test_auto_detect_protein():
    r = run_skill({"sequence": "MKLVWWQEFH"})
    assert r["seq_type_detected"] == "protein", r


def test_protein_mw_pi():
    r = run_skill({"sequence": "MKLVWWQEFH",
                   "operations": ["molecular_weight", "isoelectric_point"]})
    assert r["results"]["molecular_weight"] > 1000, r["results"]
    assert 0 < r["results"]["isoelectric_point"] < 14, r["results"]


def test_orf_find():
    # 含一个完整 ORF:ATG...TAA
    r = run_skill({"sequence": "TTATGGCCTGTTAAGG", "operations": ["orf"]})
    assert isinstance(r["results"]["orf"], list), r["results"]
    assert any(o["protein"].startswith("M") for o in r["results"]["orf"]), r["results"]["orf"]


def test_pairwise_identity_self():
    r = run_skill({"sequence": "MKLVWWQEFH", "sequence2": "MKLVWWQEFH",
                   "operations": ["pairwise_align"]})
    assert abs(r["results"]["pairwise_align"]["identity"] - 100.0) < 1e-6, r["results"]


def test_pairwise_identity_partial():
    r = run_skill({"sequence": "MKLVWWQEFH", "sequence2": "MKLVWWQEFA",
                   "operations": ["pairwise_align"]})
    # 9/10 相同 = 90%
    assert 85 <= r["results"]["pairwise_align"]["identity"] <= 95, r["results"]


def test_empty_sequence_error():
    r = run_skill({"sequence": "", "operations": ["translate"]})
    assert r["ok"] is False, r


def test_default_ops_when_unspecified():
    # 不传 operations:DNA 应给默认分析(至少含 length + 某些操作)
    r = run_skill({"sequence": "ATGGCCTGTTAA"})
    assert r["ok"] is True, r
    assert r["length"] == 12, r


TESTS = [
    test_translate_dna, test_reverse_complement, test_gc_content,
    test_auto_detect_dna, test_auto_detect_protein, test_protein_mw_pi,
    test_orf_find, test_pairwise_identity_self, test_pairwise_identity_partial,
    test_empty_sequence_error, test_default_ops_when_unspecified,
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
