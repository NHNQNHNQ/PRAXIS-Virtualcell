"""Focused checks for bounded, non-promoting NCBI assembly metadata evidence."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from datetime import UTC, datetime
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from research.mdr_gnb.mic_ncbi_assembly_metadata_qualification import (
    AssemblyMetadataQualificationError,
    derive_exact_profile_pairs,
    pair_from_raw_request,
    qualify_ncbi_assembly_metadata_response,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DRIVER_PATH = (
    _REPO_ROOT
    / "research/mdr_gnb/mic_discovery/2026-08-14-ncbi-assembly-metadata-ecoli-meropenem/derived"
    / "retrieve_and_qualify_ncbi_assembly_metadata_v1.py"
)
_RECOVERY_PATH = (
    _REPO_ROOT
    / "research/mdr_gnb/mic_discovery/2026-08-14-ncbi-assembly-metadata-ecoli-meropenem/derived"
    / "qualify_existing_ncbi_assembly_metadata_v1.py"
)


def _driver():
    spec = importlib.util.spec_from_file_location("_ncbi_assembly_driver_test", _DRIVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _recovery():
    spec = importlib.util.spec_from_file_location("_ncbi_assembly_recovery_test", _RECOVERY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _linked_row(
    *,
    assembly: str = "GCA_000000001.1",
    biosample: str = "SAMN00000001",
) -> dict[str, object]:
    return {
        "candidate_id": "candidate-1",
        "candidate_status": "record_level_quantitative_mic_candidate_unverified",
        "data_admission_status": "not_admitted",
        "scientific_status": "unverified",
        "BioSample_ID": biosample,
        "assembly_ID": assembly,
        "profile_linkage_key": f"{biosample}|{assembly}",
        "profile_linkage_status": "exact_profile_join",
    }


def _body(
    *,
    accession: str = "GCA_000000001.1",
    biosample: str = "SAMN00000001",
    organism_tax_id: int = 1438687,
    checkm_species_tax_id: int | None = 562,
) -> str:
    report: dict[str, object] = {
        "accession": accession,
        "current_accession": accession,
        "paired_accession": "GCF_000000001.1",
        "source_database": "SOURCE_DATABASE_GENBANK",
        "organism": {"tax_id": organism_tax_id, "organism_name": "Escherichia coli example"},
        "assembly_info": {
            "assembly_status": "current",
            "assembly_level": "Scaffold",
            "biosample": {"accession": biosample, "status": {"status": "live"}},
        },
    }
    if checkm_species_tax_id is not None:
        report["checkm_info"] = {"checkm_species_tax_id": checkm_species_tax_id}
    return json.dumps({"reports": [report], "total_count": 1})


def test_derives_only_exact_versioned_gca_biosample_pairs_without_data_admission() -> None:
    duplicate = _linked_row()
    unlinked = dict(duplicate)
    unlinked["profile_linkage_status"] = "unmatched_assembly"
    pairs = derive_exact_profile_pairs([duplicate, _linked_row(), unlinked], expected_count=1)

    assert pairs == [
        {"assembly_accession": "GCA_000000001.1", "biosample_accession": "SAMN00000001"}
    ]


def test_rejects_non_gca_or_ambiguous_exact_linkage() -> None:
    with pytest.raises(AssemblyMetadataQualificationError, match="not a versioned GCA"):
        derive_exact_profile_pairs([_linked_row(assembly="GCF_000000001.1")])
    with pytest.raises(AssemblyMetadataQualificationError, match="assembly maps to multiple"):
        derive_exact_profile_pairs(
            [_linked_row(biosample="SAMN00000001"), _linked_row(biosample="SAMN00000002")]
        )


def test_raw_request_metadata_is_projected_to_the_exact_identity_pair() -> None:
    request = {
        "assembly_accession": "GCA_000000001.1",
        "biosample_accession": "SAMN00000001",
        "endpoint": (
            "https://api.ncbi.nlm.nih.gov/datasets/v2/genome/accession/"
            "GCA_000000001.1/dataset_report"
        ),
    }

    assert pair_from_raw_request(request) == {
        "assembly_accession": "GCA_000000001.1",
        "biosample_accession": "SAMN00000001",
    }

    with pytest.raises(AssemblyMetadataQualificationError, match="raw request endpoint drift"):
        pair_from_raw_request({**request, "endpoint": "https://example.invalid/"})


def test_strain_level_organism_taxon_does_not_replace_checkm_species_evidence() -> None:
    pair = {"assembly_accession": "GCA_000000001.1", "biosample_accession": "SAMN00000001"}
    row = qualify_ncbi_assembly_metadata_response(
        pair, http_status=200, content_type="application/json", response_body=_body()
    )

    assert row["metadata_qualification_status"] == "metadata_exact_match_candidate_not_admitted"
    assert row["species_evidence_status"] == "checkm_species_tax_id_562"
    assert row["returned_organism_tax_id"] == 1438687
    assert row["returned_checkm_species_tax_id"] == 562
    assert row["data_admission_status"] == "not_admitted"
    assert row["training_authorized"] is False


def test_organism_tax_id_cannot_substitute_for_missing_checkm_species_evidence() -> None:
    pair = {"assembly_accession": "GCA_000000001.1", "biosample_accession": "SAMN00000001"}
    row = qualify_ncbi_assembly_metadata_response(
        pair,
        http_status=200,
        content_type="application/json",
        response_body=_body(organism_tax_id=562, checkm_species_tax_id=None),
    )

    assert row["metadata_qualification_status"] == "metadata_unresolved_not_admitted"
    assert row["species_evidence_status"] == "species_evidence_unresolved"
    assert "checkm_species_tax_id_not_562" in row["unresolved_reason_codes"]
    assert row["data_admission_status"] == "not_admitted"


def test_non_json_content_type_cannot_pass_even_if_the_body_looks_valid() -> None:
    row = qualify_ncbi_assembly_metadata_response(
        {"assembly_accession": "GCA_000000001.1", "biosample_accession": "SAMN00000001"},
        http_status=200,
        content_type="text/plain",
        response_body=_body(),
    )

    assert row["metadata_qualification_status"] == "metadata_unresolved_not_admitted"
    assert row["unresolved_reason_codes"] == ["content_type_not_json"]


@pytest.mark.parametrize(
    ("body", "expected_reason"),
    [
        (json.dumps({"reports": [_body()], "total_count": 1}), "response_report_count_not_one"),
        (
            json.dumps({"reports": [json.loads(_body())["reports"][0]], "total_count": 2}),
            "response_total_count_not_one",
        ),
        (_body(biosample="SAMN00000002"), "biosample_mismatch"),
    ],
)
def test_exact_identity_contract_rejects_count_or_biosample_drift(
    body: str, expected_reason: str
) -> None:
    row = qualify_ncbi_assembly_metadata_response(
        {"assembly_accession": "GCA_000000001.1", "biosample_accession": "SAMN00000001"},
        http_status=200,
        content_type="application/json",
        response_body=body,
    )

    assert row["metadata_qualification_status"] == "metadata_unresolved_not_admitted"
    assert expected_reason in row["unresolved_reason_codes"]


def test_non_current_or_non_live_status_never_passes() -> None:
    body = json.loads(_body())
    report = body["reports"][0]
    report["source_database"] = "SOURCE_DATABASE_REFSEQ"
    report["assembly_info"]["assembly_status"] = "suppressed"
    report["assembly_info"]["biosample"]["status"]["status"] = "suppressed"
    row = qualify_ncbi_assembly_metadata_response(
        {"assembly_accession": "GCA_000000001.1", "biosample_accession": "SAMN00000001"},
        http_status=200,
        content_type="application/json",
        response_body=json.dumps(body),
    )

    assert row["metadata_qualification_status"] == "metadata_unresolved_not_admitted"
    assert set(row["unresolved_reason_codes"]) == {
        "assembly_status_not_current",
        "biosample_status_not_live",
        "source_database_not_genbank",
    }


def test_transport_error_is_an_unresolved_observation() -> None:
    row = qualify_ncbi_assembly_metadata_response(
        {"assembly_accession": "GCA_000000001.1", "biosample_accession": "SAMN00000001"},
        http_status=None,
        content_type=None,
        response_body=None,
        transport_error="URLError: timeout",
    )

    assert row["metadata_qualification_status"] == "metadata_unresolved_not_admitted"
    assert set(row["unresolved_reason_codes"]) == {
        "http_status_not_200",
        "response_body_missing",
        "transport_error",
    }


@pytest.mark.parametrize(
    ("http_status", "body", "expected_reason"),
    [
        (503, '{"error":"unavailable"}', "http_status_not_200"),
        (200, "not-json", "response_not_json"),
        (200, json.dumps({"reports": []}), "response_report_count_not_one"),
        (200, _body(accession="GCA_000000099.1"), "accession_mismatch"),
    ],
)
def test_errors_and_identity_mismatches_stay_unresolved_and_not_admitted(
    http_status: int, body: str, expected_reason: str
) -> None:
    row = qualify_ncbi_assembly_metadata_response(
        {"assembly_accession": "GCA_000000001.1", "biosample_accession": "SAMN00000001"},
        http_status=http_status,
        content_type="application/json",
        response_body=body,
    )

    assert row["metadata_qualification_status"] == "metadata_unresolved_not_admitted"
    assert expected_reason in row["unresolved_reason_codes"]
    assert row["data_admission_status"] == "not_admitted"
    assert row["scientific_status"] == "unverified"
    assert row["prediction_authorized"] is False


def test_driver_requires_confirmation_before_any_output_or_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = _driver()
    monkeypatch.setattr(sys, "argv", [str(_DRIVER_PATH)])

    with pytest.raises(SystemExit, match="without --confirm"):
        driver.main()


def test_driver_rejects_an_expired_authorization_before_work() -> None:
    driver = _driver()

    with pytest.raises(SystemExit, match="authorization has expired"):
        driver._require_active_authorizations(now=datetime(2026, 8, 20, 7, 57, tzinfo=UTC))


def test_driver_never_follows_a_redirect() -> None:
    driver = _driver()
    request = Request(
        "https://api.ncbi.nlm.nih.gov/datasets/v2/genome/accession/GCA_000000001.1/dataset_report"
    )

    with pytest.raises(HTTPError, match="redirect blocked"):
        driver._NoRedirect().redirect_request(
            request, None, 302, "Found", None, "https://example.invalid/redirected"
        )


def test_driver_records_a_redirect_as_an_unresolved_raw_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = _driver()

    class _RedirectingOpener:
        def open(self, request: Request, timeout: int):
            raise HTTPError(request.full_url, 302, "redirect blocked", {}, io.BytesIO(b""))

    monkeypatch.setattr(driver, "_OPENER", _RedirectingOpener())
    row = driver._fetch_one(
        {"assembly_accession": "GCA_000000001.1", "biosample_accession": "SAMN00000001"}
    )

    assert row["response"]["http_status"] == 302
    assert row["response"]["body_text"] == ""
    assert row["request"]["endpoint"].startswith("https://api.ncbi.nlm.nih.gov/")


def test_driver_records_a_truncated_response_as_an_unresolved_raw_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = _driver()

    class _TruncatedOpener:
        def open(self, request: Request, timeout: int):
            raise IncompleteRead(b'{"reports":', 12)

    monkeypatch.setattr(driver, "_OPENER", _TruncatedOpener())
    row = driver._fetch_one(
        {"assembly_accession": "GCA_000000001.1", "biosample_accession": "SAMN00000001"}
    )

    assert row["response"]["http_status"] is None
    assert row["response"]["body_text"] is None
    assert row["response"]["transport_error"].startswith("IncompleteRead:")


def test_driver_records_a_truncated_http_error_body_as_an_unresolved_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = _driver()

    class _BrokenBody:
        def read(self, amount: int | None = None):
            raise IncompleteRead(b"", amount)

        def close(self) -> None:
            return None

    class _BrokenErrorOpener:
        def open(self, request: Request, timeout: int):
            raise HTTPError(request.full_url, 503, "unavailable", {}, _BrokenBody())

    monkeypatch.setattr(driver, "_OPENER", _BrokenErrorOpener())
    row = driver._fetch_one(
        {"assembly_accession": "GCA_000000001.1", "biosample_accession": "SAMN00000001"}
    )

    assert row["response"]["http_status"] == 503
    assert row["response"]["body_text"] is None
    assert row["response"]["transport_error"].startswith("IncompleteRead:")


def test_driver_records_a_socket_reset_while_reading_an_http_error_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = _driver()

    class _BrokenBody:
        def read(self, amount: int | None = None):
            raise OSError("connection reset")

        def close(self) -> None:
            return None

    class _BrokenErrorOpener:
        def open(self, request: Request, timeout: int):
            raise HTTPError(request.full_url, 503, "unavailable", {}, _BrokenBody())

    monkeypatch.setattr(driver, "_OPENER", _BrokenErrorOpener())
    row = driver._fetch_one(
        {"assembly_accession": "GCA_000000001.1", "biosample_accession": "SAMN00000001"}
    )

    assert row["response"]["http_status"] == 503
    assert row["response"]["body_text"] is None
    assert row["response"]["transport_error"] == "OSError: connection reset"


def test_driver_rejects_a_copied_output_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    driver = _driver()
    monkeypatch.setattr(driver, "OUTPUT_ROOT", tmp_path)

    with pytest.raises(SystemExit, match="outside its authorized output root"):
        driver._assert_execution_location()


def test_driver_throttles_request_starts_to_a_safe_two_per_second_rate() -> None:
    driver = _driver()
    times = iter((10.2, 10.5))
    slept: list[float] = []

    observed = driver._wait_for_next_request(
        10.0, monotonic=lambda: next(times), sleep=slept.append
    )

    assert slept == [pytest.approx(0.3)]
    assert observed == 10.5


def test_recovery_uses_the_authorized_three_per_second_wall_clock_cadence() -> None:
    recovery = _recovery()
    rows = [
        {"request_started_at": "2026-08-14T01:08:26.090969Z"},
        {"request_started_at": "2026-08-14T01:08:26.590565Z"},
    ]

    # The retrieval driver used a monotonic 2/s limiter; the journal stores a
    # wall-clock observation.  This 0.499596-second gap meets the authorization's
    # 3/s ceiling but cannot prove the driver's monotonic interval by itself.
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(recovery, "EXPECTED_REQUEST_COUNT", len(rows))
    try:
        evidence = recovery._authorized_cadence_evidence(rows)
    finally:
        monkeypatch.undo()

    assert evidence["authorization_cadence_verified"] is True
    assert evidence["minimum_observed_wall_clock_start_interval_seconds"] == pytest.approx(0.499596)


def test_recovery_rejects_wall_clock_cadence_above_the_authorized_three_per_second_cap() -> None:
    recovery = _recovery()
    rows = [
        {"request_started_at": "2026-08-14T01:08:26.000000Z"},
        {"request_started_at": "2026-08-14T01:08:26.200000Z"},
    ]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(recovery, "EXPECTED_REQUEST_COUNT", len(rows))
    try:
        with pytest.raises(SystemExit, match="authorization cadence"):
            recovery._authorized_cadence_evidence(rows)
    finally:
        monkeypatch.undo()


def test_driver_rechecks_authorization_after_the_rate_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    driver = _driver()
    calls: list[str] = []
    monkeypatch.setattr(driver, "_require_active_authorizations", lambda: calls.append("checked"))

    driver._next_authorized_request_start(None, monotonic=lambda: 1.0, sleep=lambda _: None)

    assert calls == ["checked"]


def test_driver_journals_each_response_before_finalizing_the_raw_file(tmp_path: Path) -> None:
    driver = _driver()
    raw_path = tmp_path / "responses.jsonl"
    handle = driver._open_raw_journal(raw_path)
    driver._append_raw_journal(handle, {"request_started_at": "2026-08-14T00:00:00Z"})

    assert raw_path.with_name("responses.jsonl.part").read_text(encoding="utf-8") == (
        '{"request_started_at": "2026-08-14T00:00:00Z"}\n'
    )
    assert not raw_path.exists()

    driver._finalize_raw_journal(handle, raw_path)

    assert raw_path.exists()
    assert not raw_path.with_name("responses.jsonl.part").exists()
