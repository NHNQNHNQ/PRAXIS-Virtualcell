"""MorganGenerator migration must preserve the frozen small-molecule feature contract."""
from __future__ import annotations

import hashlib

import numpy as np
import pytest

from praxis_virtualcell.mdr_gnb.drug_agent.small_molecule_features import (
    morgan_bits,
    morgan_bitvect,
)
from praxis_virtualcell.mdr_gnb.workflows.science_v2.qsar_baseline import (
    _morgan_bitvect,
    morgan_fp,
)


def _packed_sha256(bits: np.ndarray) -> str:
    return hashlib.sha256(np.packbits(bits).tobytes()).hexdigest()


@pytest.mark.parametrize(
    ("smiles", "expected_sha256"),
    [
        ("C", "227feb5024463d2c93785a7647d28bec6816b2d87d9805e8b9ccca1db9cbfd0c"),
        ("c1ccccc1", "b99fb0ae3316888db0708d6f97c8547cee397ad608d18a0dfac456d694542b43"),
        (
            "COc1cc(Cc2cnc(N)nc2N)cc(OC)c1OC",
            "c8099df5d88112e9ce5450c49b906ac5131f8a9d1ba22fe990fabadb1954da33",
        ),
    ],
)
def test_morgan_generator_preserves_frozen_2048_bit_contract(smiles, expected_sha256):
    pytest.importorskip("rdkit")
    bits = morgan_bits(smiles)
    assert bits is not None
    assert bits.dtype == np.uint8
    assert bits.shape == (2048,)
    assert _packed_sha256(bits) == expected_sha256


@pytest.mark.parametrize("n_bits", [512, 2048])
def test_runtime_and_qsar_baseline_share_identical_bitvectors(n_bits):
    pytest.importorskip("rdkit")
    smiles = "Cn1cnc2n(C)c(=O)n(C)c(=O)c12"  # caffeine, nontrivial heterocyclic molecule
    runtime_bv = morgan_bitvect(smiles, n_bits=n_bits, radius=2)
    baseline_bv = _morgan_bitvect(smiles, n_bits=n_bits, radius=2)
    assert runtime_bv is not None
    assert baseline_bv is not None
    assert runtime_bv.ToBitString() == baseline_bv.ToBitString()
    assert np.array_equal(morgan_bits(smiles, n_bits=n_bits), morgan_fp(smiles, n_bits=n_bits))
    assert morgan_fp(smiles, n_bits=n_bits).dtype == np.int8


def test_morgan_generator_keeps_invalid_smiles_fail_closed():
    pytest.importorskip("rdkit")
    assert morgan_bitvect("not valid (((") is None
    assert morgan_bits("not valid (((") is None
    assert _morgan_bitvect("not valid (((") is None
    assert morgan_fp("not valid (((") is None
