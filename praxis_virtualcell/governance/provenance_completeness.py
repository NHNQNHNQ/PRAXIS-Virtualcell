"""Fail-closed report provenance completeness contract for models_used/models_rejected/reliability/provenance and
required provenance subkeys. These fields normally exist by construction; the gate detects omission after
refactoring. It does not compare module predictions or validate every report field.
"""
from __future__ import annotations

_TOP_REQUIRED = ("models_used", "models_rejected", "reliability", "provenance")
_PROV_REQUIRED = ("n_messages", "rules_referenced", "models_used")


def check_report_provenance(report: dict) -> list[str]:
    """Return missing/invalid required keys; provenance must be a dictionary with required subkeys. A nondictionary
    report returns all required top-level keys.
    """
    if not isinstance(report, dict):
        return list(_TOP_REQUIRED)
    missing = [k for k in _TOP_REQUIRED if k not in report]
    prov = report.get("provenance")
    if not isinstance(prov, dict):
        if "provenance" not in missing:
            missing.append("provenance")
        return missing
    missing.extend(f"provenance.{k}" for k in _PROV_REQUIRED if k not in prov)
    return missing
