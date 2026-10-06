"""Failure-focused checks for the local MIC/genome/gene-feature pairing ledger."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

DRIVER = (
    Path(__file__).resolve().parents[3]
    / "research/mdr_gnb/mic_discovery/2026-08-17-m1b1-local-genome-gene-feature-pairing-ecoli-meropenem"
    / "derived/pair_ecoli_meropenem_genome_gene_features_v1.py"
)


def _module():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("mic_genome_gene_feature_pairing", DRIVER)
    if spec is None or spec.loader is None:
        raise RuntimeError("pairing driver cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _candidate() -> dict[str, object]:
    return {
        "candidate_id": "candidate-1",
        "candidate_status": "record_level_quantitative_mic_candidate_unverified",
        "data_admission_status": "not_admitted",
        "scientific_status": "unverified",
        "BioSample_ID": "SAMN00000001",
        "assembly_ID": "GCA_000000001.1",
    }


def _profile() -> dict[str, object]:
    return {
        **_candidate(),
        "profile_linkage_status": "exact_profile_join",
        "profile_toolchain_status": "local_dirty_legacy_source_observation",
        "profile_payload_sha256": "a" * 64,
        "profile_token_count": 2,
    }


def _assembly() -> dict[str, object]:
    return {
        "assembly_accession": "GCA_000000001.1",
        "biosample_accession": "SAMN00000001",
        "metadata_qualification_status": "metadata_exact_match_candidate_not_admitted",
        "species_evidence_status": "checkm_species_tax_id_562",
        "candidate_status": "record_level_quantitative_mic_candidate_unverified",
        "data_admission_status": "not_admitted",
        "scientific_status": "unverified",
    }


class PairRowsTest(unittest.TestCase):
    def test_exact_profile_and_exact_assembly_are_paired_without_payload(self) -> None:
        row = _module().pair_rows([_candidate()], [_profile()], [_assembly()])[0]

        self.assertEqual(row["candidate_id"], "candidate-1")
        self.assertEqual(row["profile_payload_sha256"], "a" * 64)
        self.assertEqual(row["profile_token_count"], 2)
        self.assertEqual(
            row["assembly_identity_status"], "metadata_exact_match_candidate_not_admitted"
        )
        self.assertEqual(row["unpaired_reason_codes"], [])
        self.assertEqual(row["genome_bytes_status"], "genome_bytes_unavailable_not_downloaded")
        self.assertEqual(
            row["genome_annotation_status"], "genome_annotation_unavailable_not_downloaded"
        )
        self.assertNotIn("profile_raw_genotypes", row)
        self.assertNotIn("local_sir_reference_labels", row)

    def test_profile_identity_mismatch_fails_closed(self) -> None:
        profile = _profile()
        profile["BioSample_ID"] = "SAMN00000002"

        with self.assertRaises(SystemExit):
            _module().pair_rows([_candidate()], [profile], [_assembly()])

    def test_missing_exact_assembly_pair_is_explicitly_unpaired(self) -> None:
        other_assembly = _assembly()
        other_assembly["biosample_accession"] = "SAMN00000002"
        row = _module().pair_rows([_candidate()], [_profile()], [other_assembly])[0]

        self.assertEqual(row["assembly_identity_status"], "assembly_metadata_pair_unresolved")
        self.assertIn("assembly_metadata_pair_absent", row["unpaired_reason_codes"])

    def test_duplicate_exact_assembly_pair_fails_closed(self) -> None:
        with self.assertRaises(SystemExit):
            _module().pair_rows([_candidate()], [_profile()], [_assembly(), _assembly()])

    def test_missing_assembly_stays_explicitly_unpaired(self) -> None:
        candidate = _candidate()
        candidate["assembly_ID"] = None
        profile = {
            **candidate,
            "profile_linkage_status": "missing_assembly_no_local",
            "profile_toolchain_status": None,
            "profile_payload_sha256": None,
            "profile_token_count": None,
        }

        row = _module().pair_rows([candidate], [profile], [])[0]

        self.assertEqual(row["assembly_accession"], None)
        self.assertEqual(row["gene_feature_status"], "gene_feature_unavailable_no_exact_profile")
        self.assertIn("profile_linkage_missing_assembly_no_local", row["unpaired_reason_codes"])

    def test_driver_does_not_parse_unallowlisted_qualification_report_fields(self) -> None:
        module = _module()
        source = DRIVER.read_text(encoding="utf-8")

        self.assertNotIn("def _validate_reports", source)
        self.assertNotIn('INPUTS["profile_report"]["path"]).read_bytes()', source)
        self.assertNotIn('INPUTS["assembly_report"]["path"]).read_bytes()', source)
        self.assertNotIn("profile_report", module.INPUTS)
        self.assertNotIn("assembly_report", module.INPUTS)

    def test_report_separates_all_rows_from_exact_profile_rows(self) -> None:
        module = _module()
        exact = module.pair_rows([_candidate()], [_profile()], [_assembly()])[0]
        unpaired_candidate = _candidate()
        unpaired_candidate["candidate_id"] = "candidate-2"
        unpaired_candidate["assembly_ID"] = None
        unpaired_profile = {
            **unpaired_candidate,
            "profile_linkage_status": "missing_assembly_no_local",
            "profile_toolchain_status": None,
            "profile_payload_sha256": None,
            "profile_token_count": None,
        }
        unpaired = module.pair_rows([unpaired_candidate], [unpaired_profile], [])[0]
        identities = {
            "authorization": {},
            "driver": {},
            **{name: {} for name in module.INPUTS},
        }

        report = module._report(identities, [exact, unpaired])

        self.assertEqual(report["exact_profile_rows"], 1)
        self.assertEqual(
            report["exact_profile_genome_identity_counts"],
            {"official_versioned_assembly_identity_verified": 1},
        )
        self.assertEqual(
            report["all_candidate_genome_identity_counts"],
            {
                "official_versioned_assembly_identity_verified": 1,
                "versioned_assembly_identity_unresolved": 1,
            },
        )

    def test_driver_uses_pinned_input_and_output_operations(self) -> None:
        source = DRIVER.read_text(encoding="utf-8")

        self.assertNotIn("_sha256(REPO_ROOT / INPUTS", source)
        self.assertNotIn('path.open("x"', source)
        self.assertIn("O_NOFOLLOW", source)
        self.assertIn("dir_fd=parent_fd", source)


if __name__ == "__main__":
    unittest.main()
