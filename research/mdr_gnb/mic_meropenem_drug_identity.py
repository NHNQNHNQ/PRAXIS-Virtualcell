"""Strict offline identity receipt for the planned meropenem MIC scope.

This research helper only verifies a fixed drug identity.  It does not admit
data, train a model, create a Pack, or enable ``predict_mic``.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

EXPECTED_STANDARDIZED_SMILES = (
    "C[C@@H](O)[C@H]1C(=O)N2C(C(=O)O)=C(S[C@@H]3CN[C@H](C(=O)N(C)C)C3)"
    "[C@H](C)[C@H]12"
)
EXPECTED_INCHIKEY = "DMJNNHOOLUXYBV-PQTSNVLCSA-N"
EXPECTED_RDKIT_VERSION = "2026.03.3"
STANDARDIZER_ID = "rdkit-canonical-isomeric-single-fragment-exact-identity"
STANDARDIZER_VERSION = "rdkit-2026.03.3-policy-1"
_POLICY = {
    "schema_version": "gnb.mic-meropenem-standardizer-policy.v1",
    "canonical_drug_id": "ARO:0000073",
    "chemical_cross_reference": "CHEBI:43968",
    "expected_standardized_smiles": EXPECTED_STANDARDIZED_SMILES,
    "expected_standard_inchikey": EXPECTED_INCHIKEY,
    "rdkit_version": EXPECTED_RDKIT_VERSION,
    "fragment_count": 1,
    "formal_charge": 0,
    "stereochemistry": "fully_assigned_exact_isomeric_smiles",
}


class MICMeropenemDrugIdentityError(ValueError):
    """A fail-closed error for the fixed meropenem identity receipt."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"invalid meropenem identity: {code}")


def _canonical_json_sha256(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


STANDARDIZER_FINGERPRINT = _canonical_json_sha256(_POLICY)


def _admission_drug_binding_fingerprint() -> str:
    return _canonical_json_sha256(
        {
            "schema_version": "gnb.mic-canonical-drug-binding.v1",
            "canonical_drug_id": "ARO:0000073",
            "standardized_smiles": EXPECTED_STANDARDIZED_SMILES,
            "standardizer_id": STANDARDIZER_ID,
            "standardizer_version": STANDARDIZER_VERSION,
            "standardizer_fingerprint": STANDARDIZER_FINGERPRINT,
        }
    )


def meropenem_admission_drug_receipt(input_smiles: str) -> dict[str, Any]:
    """Return an exact M1 admission-compatible receipt for meropenem free acid.

    The caller must provide a single, fully stereospecified structure.  Salt,
    hydrate, different compound, invalid input, and an unexpected RDKit
    runtime all fail closed.
    """

    if (
        not isinstance(input_smiles, str)
        or not input_smiles
        or input_smiles.strip() != input_smiles
    ):
        raise MICMeropenemDrugIdentityError("input_smiles_invalid")
    if any(character.isspace() for character in input_smiles):
        raise MICMeropenemDrugIdentityError("input_smiles_invalid")
    try:
        from rdkit import Chem, RDLogger, rdBase
    except ImportError as exc:
        raise MICMeropenemDrugIdentityError("standardizer_unavailable") from exc
    if rdBase.rdkitVersion != EXPECTED_RDKIT_VERSION:
        raise MICMeropenemDrugIdentityError("standardizer_version_mismatch")
    RDLogger.DisableLog("rdApp.*")
    try:
        molecule = Chem.MolFromSmiles(input_smiles)
    finally:
        RDLogger.EnableLog("rdApp.*")
    if molecule is None:
        raise MICMeropenemDrugIdentityError("input_smiles_invalid")
    if len(Chem.GetMolFrags(molecule)) != 1:
        raise MICMeropenemDrugIdentityError("single_fragment_required")
    if Chem.GetFormalCharge(molecule) != 0:
        raise MICMeropenemDrugIdentityError("drug_identity_mismatch")
    standardized_smiles = Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)
    if standardized_smiles != EXPECTED_STANDARDIZED_SMILES:
        raise MICMeropenemDrugIdentityError("drug_identity_mismatch")
    if Chem.MolToInchiKey(molecule) != EXPECTED_INCHIKEY:
        raise MICMeropenemDrugIdentityError("drug_identity_mismatch")
    return {
        "schema_version": "gnb.mic-admission-drug.v1",
        "drug_cardinality": 1,
        "canonical_drug_id": "ARO:0000073",
        "standardized_smiles": EXPECTED_STANDARDIZED_SMILES,
        "standardized_smiles_fingerprint": hashlib.sha256(
            EXPECTED_STANDARDIZED_SMILES.encode("utf-8")
        ).hexdigest(),
        "canonical_structure_fingerprint": _admission_drug_binding_fingerprint(),
        "standardizer": {
            "schema_version": "gnb.mic-admission-standardizer.v1",
            "id": STANDARDIZER_ID,
            "version": STANDARDIZER_VERSION,
            "fingerprint": STANDARDIZER_FINGERPRINT,
        },
    }


__all__ = [
    "EXPECTED_INCHIKEY",
    "EXPECTED_STANDARDIZED_SMILES",
    "MICMeropenemDrugIdentityError",
    "STANDARDIZER_FINGERPRINT",
    "meropenem_admission_drug_receipt",
]
