"""Strict, offline meropenem identity receipt tests."""

from __future__ import annotations

import pytest

from research.mdr_gnb.mic_meropenem_drug_identity import (
    EXPECTED_STANDARDIZED_SMILES,
    STANDARDIZER_FINGERPRINT,
    MICMeropenemDrugIdentityError,
    meropenem_admission_drug_receipt,
)


def test_exact_meropenem_free_acid_receipt_is_stable() -> None:
    receipt = meropenem_admission_drug_receipt(EXPECTED_STANDARDIZED_SMILES)

    assert receipt["canonical_drug_id"] == "ARO:0000073"
    assert receipt["standardized_smiles"] == EXPECTED_STANDARDIZED_SMILES
    assert (
        STANDARDIZER_FINGERPRINT
        == "de03a39577a3a68fa3efd899844923d3ef49cca69a014f495ab8e1e25ba92030"
    )
    assert receipt["standardizer"]["fingerprint"] == STANDARDIZER_FINGERPRINT
    assert (
        receipt["canonical_structure_fingerprint"]
        == "8102f609a9c75e039d1c2ef35f70d35852b03754e8d5321186934892e078466b"
    )


@pytest.mark.parametrize(
    ("smiles", "code"),
    (
        ("CCO", "drug_identity_mismatch"),
        (EXPECTED_STANDARDIZED_SMILES + ".O", "single_fragment_required"),
        (EXPECTED_STANDARDIZED_SMILES.replace("@@", "", 1), "drug_identity_mismatch"),
    ),
)
def test_nonexact_or_multifragment_input_fails_closed(smiles: str, code: str) -> None:
    with pytest.raises(MICMeropenemDrugIdentityError) as exc:
        meropenem_admission_drug_receipt(smiles)
    assert exc.value.code == code
