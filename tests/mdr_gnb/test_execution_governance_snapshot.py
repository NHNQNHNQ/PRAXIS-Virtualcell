"""P1 execution identity: mutable governance inputs must not reuse an old cache."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from praxis_virtualcell.mdr_gnb.api import service
from praxis_virtualcell.mdr_gnb.governance_snapshot import (
    SNAPSHOT_SCHEMA_VERSION,
    build_governance_execution_context,
    build_governance_snapshot,
)
from praxis_virtualcell.mdr_gnb.predictors.registry import PredictorRegistry, PredictorSpec
from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


def test_runtime_governance_snapshot_has_exact_hashes_for_all_declared_sources():
    snapshot = build_governance_snapshot()

    assert snapshot["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert len(snapshot["governance_digest"]) == 64
    source_ids = {source["id"] for source in snapshot["sources"]}
    assert {"evidence_tiers", "amrfinder_sir_rules"} <= source_ids
    brain_rules = [source for source in source_ids if source.endswith("/rules")]
    brain_overlays = [source for source in source_ids if source.startswith("brain/")
                      and not source.endswith("/rules")]
    assert len(brain_rules) == 10
    assert len(brain_overlays) == 40
    sources = {source["id"]: source for source in snapshot["sources"]}
    assert all(sources[source_id]["present"] and len(sources[source_id]["sha256"]) == 64
               for source_id in {"evidence_tiers", "amrfinder_sir_rules", *brain_rules})
    # Missing overlays are facts too: creating one changes the execution digest
    # instead of silently bypassing governance capture.
    assert all(not sources[source_id]["present"] for source_id in brain_overlays)


def test_governance_digest_changes_when_a_source_content_changes(tmp_path: Path):
    source = tmp_path / "governance.yaml"
    source.write_text("version: 1\n", encoding="utf-8")
    first = build_governance_snapshot({"test_governance": source})

    source.write_text("version: 2\n", encoding="utf-8")
    second = build_governance_snapshot({"test_governance": source})

    assert first["governance_digest"] != second["governance_digest"]
    assert first["sources"][0]["sha256"] != second["sources"][0]["sha256"]


def test_execution_cache_key_includes_governance_digest(monkeypatch):
    raw = {
        "species": "escherichia_coli",
        "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenems"}],
        "requested_outputs": ["SIR"],
        "amr_profile": {"blaKPC-2": True},
    }
    monkeypatch.setattr(
        service,
        "governance_snapshot_identity",
        lambda: {"governance_digest": "a" * 64},
    )
    first = service.execution_cache_key(raw)
    monkeypatch.setattr(
        service,
        "governance_snapshot_identity",
        lambda: {"governance_digest": "b" * 64},
    )
    second = service.execution_cache_key(raw)

    assert first != second


def test_service_predict_binds_one_governance_snapshot_through_trace_and_cache_key(
    monkeypatch,
):
    raw = {
        "species": "escherichia_coli",
        "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenems"}],
        "requested_outputs": ["SIR"],
        "amr_profile": {"blaKPC-2": True},
    }
    context = service.governance_execution_context()
    snapshot = {**context.snapshot, "governance_digest": "c" * 64}
    captured_context = replace(context, snapshot=snapshot)
    calls = 0

    def _one_context_only():
        nonlocal calls
        calls += 1
        if calls > 1:
            raise AssertionError("one execution must not re-capture governance inputs")
        return captured_context

    monkeypatch.setattr(service, "governance_execution_context", _one_context_only)
    result = service.predict(raw)

    response = result["response"]
    trace_record = result["trace_record"]
    assert calls == 1
    assert response["governance_snapshot"]["governance_digest"] == "c" * 64
    assert trace_record["governance_snapshot"]["governance_digest"] == "c" * 64
    assert response["execution_id"] == service.execution_cache_key(
        raw,
        lifecycle_identity=response["model_lifecycle"],
        governance_snapshot=snapshot,
    )


def _s_only_registry() -> PredictorRegistry:
    registry = PredictorRegistry()

    def predict(_context):
        return {
            "abstained": False,
            "output_kind": "sir_class",
            "sir": "S",
            "sir_prob": {"S": 0.9, "I": 0.0, "R": 0.1},
        }

    registry.register(PredictorSpec(
        name="captured-governance-test",
        version="1",
        species=["escherichia_coli"],
        drug_class=["carbapenems"],
        output_kind="sir_class",
        artifact_path="test://captured-governance.joblib",
        predict=predict,
    ))
    return registry


def test_execution_context_uses_captured_rule_evidence_and_brain_after_disk_mutation(
    tmp_path: Path,
):
    """A cache/trace digest must name the bytes the core actually consumes."""
    evidence = tmp_path / "evidence_tiers.yaml"
    rules = tmp_path / "amrfinder_sir_rules.yaml"
    brain = tmp_path / "brain" / "rules.yaml"
    brain.parent.mkdir()
    evidence.write_text(
        "evidence_tiers:\n"
        "  - species: escherichia_coli\n"
        "    drug: meropenem\n"
        "    tier: strong\n",
        encoding="utf-8",
    )
    rules.write_text(
        "schema_version: captured-v1\n"
        "rules:\n"
        "  meropenem:\n"
        "    resistant_if_any:\n"
        "      gene_family: [blaKPC]\n",
        encoding="utf-8",
    )
    brain.write_text(
        "rules: [captured-rule]\n"
        "resistance_mechanisms: []\n"
        "negative_cases: []\n"
        "assay_boundaries: []\n"
        "species_specific_breakpoints:\n"
        "  meropenem: {source: captured-breakpoint}\n",
        encoding="utf-8",
    )
    context = build_governance_execution_context({
        "evidence_tiers": evidence,
        "amrfinder_sir_rules": rules,
        "brain/escherichia_coli/rules": brain,
    })

    # Simulate an edit after cache-key construction but before core execution.
    evidence.write_text("evidence_tiers: []\n", encoding="utf-8")
    rules.write_text(
        "schema_version: mutated-v2\nrules: {}\n", encoding="utf-8"
    )
    brain.write_text(
        "rules: [mutated-rule]\n"
        "resistance_mechanisms: []\nnegative_cases: []\nassay_boundaries: []\n"
        "species_specific_breakpoints:\n"
        "  meropenem: {source: mutated-breakpoint}\n",
        encoding="utf-8",
    )

    out = run_mdr_query({
        "species": "escherichia_coli",
        "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenems"}],
        "requested_outputs": ["SIR"],
        "amr_profile": {"blaKPC-2": True},
    }, seed_task_id="captured-governance", registry=_s_only_registry(),
       governance_context=context)

    assert out["report"]["sir"] == "R"  # captured AMRFinder rule, not mutated disk
    assert out["report"]["breakpoint_source"] == "captured-breakpoint"
    by_type = {event.message_type: event for event in out["trace"]}
    assert by_type["brain_retrieved"].payload["brain_context"]["rules"] == ["captured-rule"]
    assert (by_type["governance_snapshot_bound"].payload["governance_digest"]
            == context.snapshot["governance_digest"])


def test_new_brain_overlay_changes_snapshot_and_is_consumed(tmp_path: Path):
    base = tmp_path / "brain" / "rules.yaml"
    overlay = tmp_path / "brain" / "species_specific_breakpoints.yaml"
    base.parent.mkdir()
    base.write_text(
        "rules: []\nresistance_mechanisms: []\nnegative_cases: []\n"
        "assay_boundaries: []\nspecies_specific_breakpoints: {}\n",
        encoding="utf-8",
    )
    source_paths = {
        "brain/escherichia_coli/rules": base,
        "brain/escherichia_coli/species_specific_breakpoints": overlay,
    }
    before = build_governance_execution_context(source_paths)
    overlay.write_text("meropenem: {source: captured-overlay}\n", encoding="utf-8")
    after = build_governance_execution_context(source_paths)

    assert before.snapshot["governance_digest"] != after.snapshot["governance_digest"]
    assert before.brain_for_species("escherichia_coli")["species_specific_breakpoints"] == {}
    assert (after.brain_for_species("escherichia_coli")["species_specific_breakpoints"]
            == {"meropenem": {"source": "captured-overlay"}})


def test_breakpoint_overlay_reaches_the_production_report_and_critic(tmp_path: Path):
    """An overlay is useful only when its captured value reaches a real decision boundary."""
    evidence = tmp_path / "evidence_tiers.yaml"
    rules = tmp_path / "amrfinder_sir_rules.yaml"
    base = tmp_path / "brain" / "rules.yaml"
    overlay = tmp_path / "brain" / "species_specific_breakpoints.yaml"
    base.parent.mkdir()
    evidence.write_text(
        "evidence_tiers:\n"
        "  - species: escherichia_coli\n"
        "    drug: meropenem\n"
        "    tier: strong\n",
        encoding="utf-8",
    )
    rules.write_text("schema_version: test-v1\nrules: {}\n", encoding="utf-8")
    base.write_text(
        "rules: [base-rule]\n"
        "resistance_mechanisms: []\n"
        "negative_cases: []\n"
        "assay_boundaries: []\n"
        "species_specific_breakpoints: {}\n",
        encoding="utf-8",
    )
    overlay.write_text(
        "meropenem: {source: EUCAST v14.0 captured-overlay}\n",
        encoding="utf-8",
    )
    context = build_governance_execution_context({
        "evidence_tiers": evidence,
        "amrfinder_sir_rules": rules,
        "brain/escherichia_coli/rules": base,
        "brain/escherichia_coli/species_specific_breakpoints": overlay,
    })

    out = run_mdr_query(
        {
            "species": "escherichia_coli",
            "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenems"}],
            "requested_outputs": ["SIR"],
            "amr_profile": {"blaKPC-2": True},
        },
        seed_task_id="captured-breakpoint-overlay",
        registry=_s_only_registry(),
        governance_context=context,
    )

    by_type = {event.message_type: event for event in out["trace"]}
    breakpoint = {"meropenem": {"source": "EUCAST v14.0 captured-overlay"}}
    assert (
        by_type["brain_retrieved"].payload["brain_context"]
        ["species_specific_breakpoints"]
        == breakpoint
    )
    assert out["report"]["breakpoint_source"] == "EUCAST v14.0 captured-overlay"
    assert "breakpoint_version_mismatch" not in out["report"]["critic_violations"]
    assert (
        by_type["governance_snapshot_bound"].payload["governance_digest"]
        == context.snapshot["governance_digest"]
    )
