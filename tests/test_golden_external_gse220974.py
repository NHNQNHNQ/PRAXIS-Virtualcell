from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from scipy import sparse

from scripts.evaluate_golden_external_gse220974 import (
    _exact_sign_flip_p,
    _log_normalise,
)


def test_exact_sign_flip_gate_has_the_preregistered_five_target_resolution() -> None:
    assert _exact_sign_flip_p(np.ones(5)) == pytest.approx(1 / 32)
    assert _exact_sign_flip_p(-np.ones(5)) == pytest.approx(1.0)


def test_exact_sign_flip_rejects_scope_drift() -> None:
    with pytest.raises(ValueError, match="five finite effects"):
        _exact_sign_flip_p(np.ones(4))


def test_sparse_normalisation_remains_column_sliceable() -> None:
    matrix = sparse.csc_matrix(np.asarray([[1.0, 2.0], [3.0, 0.0]]))
    normalised = _log_normalise(matrix, np.asarray([4.0, 2.0]))

    assert sparse.isspmatrix_csc(normalised)
    assert normalised[:, [0]].shape == (2, 1)
    assert np.isfinite(normalised.data).all()


def test_preregistration_freezes_code_inputs_and_claim_ceiling() -> None:
    protocol_path = Path("data/golden/norman_2019/external_gse220974_protocol.json")
    evaluator_path = Path("scripts/evaluate_golden_external_gse220974.py")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))

    assert hashlib.sha256(evaluator_path.read_bytes()).hexdigest() == protocol["evaluator_sha256_known_before_outcome"]
    assert all(
        record["sha256_known_before_outcome"] is not None for record in protocol["external_dataset"]["files"].values()
    )
    assert protocol["selection"]["all_targets_seen_in_candidate_training"] is True
    assert protocol["claim_ceiling"]["p16_exact_external_gate_satisfied"] is False
    assert protocol["claim_ceiling"]["scientifically_validated"] is False
    assert protocol["claim_ceiling"]["production_promoted"] is False
