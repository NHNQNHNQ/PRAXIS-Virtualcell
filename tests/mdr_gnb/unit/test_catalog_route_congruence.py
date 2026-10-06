"""T4 contract for the catalog-backed portion of the production route.

The default registry still owns a deliberately broader, hard-coded declaration
shell.  This test does not call that shell a universal ModelBroker.  It proves
the narrower safety property: every catalog entry that says it is a routeable
``execution: predict`` model can be reached through the production router, and
the shell's catalog-external SIR species remain fail-closed rather than becoming
accidentally ready.
"""
from __future__ import annotations

from praxis_virtualcell.mdr_gnb.coordinator.mdr_router import route_mdr
from praxis_virtualcell.mdr_gnb.predictors.default_registry import (
    build_default_registry,
)
from praxis_virtualcell.model_zoo.runtime_manifest import RuntimeModelManifest

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


def _request_for_model(model_id: str) -> tuple[dict[str, object], str]:
    family, species, *tail = model_id.split("/")
    if family == "sir":
        assert len(tail) == 1
        return (
            {
                "species": species,
                "drug": tail[0],
                "drug_class": "catalog_route_probe",
                "requested_outputs": ["SIR"],
            },
            "genotype_to_sir",
        )
    if model_id == "activity/escherichia_coli/small_molecule":
        return (
            {
                "species": species,
                "drug": "catalog_activity_probe",
                "drug_class": "catalog_route_probe",
                "requested_outputs": ["activity"],
            },
            "sm_activity_model",
        )
    if model_id == "activity/escherichia_coli/peptide":
        return (
            {
                "species": species,
                "drug": "catalog_peptide_probe",
                "drug_class": "catalog_route_probe",
                "requested_outputs": ["peptide_activity"],
            },
            "peptide_activity_model",
        )
    raise AssertionError(f"unexpected routeable catalog model: {model_id}")


def test_every_routeable_predict_catalog_model_has_a_production_route_candidate():
    """Catalog routeable predict IDs must stay congruent with default routing."""
    manifest = RuntimeModelManifest()
    registry = build_default_registry(runtime_manifest=manifest)
    routeable = {
        model_id
        for model_id, model in manifest.models.items()
        if model.get("execution") == "predict"
        and bool((model.get("lifecycle") or {}).get("routeable_when_ready"))
    }

    assert len(routeable) == 129
    for model_id in sorted(routeable):
        request, expected_spec_name = _request_for_model(model_id)
        route = route_mdr(request, registry)

        assert route.disposition in {"accept", "caution"}, model_id
        assert any(spec.name == expected_spec_name for spec in route.candidates), model_id


def test_default_registry_species_outside_the_catalog_remain_fail_closed():
    """Hard-coded SIR declarations cannot make catalog-external species ready."""
    manifest = RuntimeModelManifest()
    registry = build_default_registry(runtime_manifest=manifest)
    catalog_sir_species = {
        model_id.split("/")[1]
        for model_id, model in manifest.models.items()
        if model_id.startswith("sir/")
        and bool((model.get("lifecycle") or {}).get("routeable_when_ready"))
    }
    declared_sir_species = {
        species
        for spec in registry.all_specs()
        if spec.name == "genotype_to_sir"
        for species in spec.species
    }
    catalog_external_species = declared_sir_species - catalog_sir_species

    assert catalog_external_species
    for species in sorted(catalog_external_species):
        route = route_mdr(
            {
                "species": species,
                "drug": "catalog_external_probe",
                "drug_class": "catalog_route_probe",
                "requested_outputs": ["SIR"],
            },
            registry,
        )

        assert route.disposition == "abstain"
        assert route.reason == "no_ready_capability"
        assert {
            "name": "genotype_to_sir",
            "reason_code": "sir_model_not_declared",
        } in route.unready_candidates
