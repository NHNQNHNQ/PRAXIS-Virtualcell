"""Offline checks for the 014 current-19 full-retry template."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

DRIVER_PATH = (
    Path(__file__).resolve().parents[1]
    / "mic_discovery"
    / "2026-08-17-m1b1-ncbi-datasets-full-retry-current19-ecoli-meropenem"
    / "derived/prepare_current19_ncbi_full_retry_v1.py"
)


def _driver():
    spec = importlib.util.spec_from_file_location("ncbi_current19_full_retry", DRIVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("014 driver cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Current19FullRetryTemplateTests(unittest.TestCase):
    def test_contract_is_fixed_and_execution_is_disabled(self) -> None:
        module = _driver()
        self.assertEqual(module.NETWORK_CONTRACT["download_summary_post_count"], 1)
        self.assertEqual(module.NETWORK_CONTRACT["download_post_max_count"], 1)
        self.assertEqual(module.REQUEST_BODY["accessions"], list(module.REQUEST_ACCESSIONS))
        with self.assertRaises(module.Refusal):
            module.refuse_network_execution()

    def test_summary_receipt_keeps_only_shape_and_counts(self) -> None:
        module = _driver()
        summary = {
            "record_count": 19,
            "assembly_count": 19,
            "available_files": {
                "all_genomic_fasta": {"file_count": 19, "private": "discard"},
                "genome_gff": {"file_count": 19},
                "sequence_report": {"file_count": 19},
            },
            "errors": [{"message": "do-not-persist-this-error-text"}],
            "messages": ["do-not-persist-this-message-text"],
            "unexpected_top_level": "discard",
        }
        receipt = module.summary_shape_receipt(200, summary)
        rendered = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("do-not-persist", rendered)
        self.assertNotIn("unexpected_top_level", rendered)
        self.assertNotIn("private", rendered)
        self.assertEqual(receipt["record_count"], {"present": True, "type": "integer", "value": 19})
        self.assertEqual(receipt["errors"], {"present": True, "type": "array", "count": 1})
        self.assertEqual(receipt["messages"], {"present": True, "type": "array", "count": 1})
        self.assertEqual(
            receipt["available_files"]["required_files"]["all_genomic_fasta"],
            {
                "present": True,
                "type": "object",
                "file_count": {"present": True, "type": "integer", "value": 19},
            },
        )
        with self.assertRaises(module.Refusal):
            module.validate_download_summary(summary)

    def test_exact_summary_and_prior_failure_receipt_validate(self) -> None:
        module = _driver()
        exact = {
            "record_count": 19,
            "assembly_count": 19,
            "available_files": {name: {"file_count": 19} for name in module.SUMMARY_FILE_COUNTS},
            "errors": [],
            "messages": [],
        }
        module.validate_download_summary(exact)
        module.validate_prior_failure_receipt(
            {
                "schema_version": "gnb.mic-m1b1-ncbi-current19-genome-package-failure.v1",
                "status": "failed_closed_not_admitted",
                "network_request_count": 1,
                "data_admission_status": "not_admitted",
                "scientific_status": "unverified",
                "pack_authorized": False,
                "training_authorized": False,
                "evaluation_authorized": False,
                "prediction_authorized": False,
            }
        )

    def test_real_package_name_and_organism_taxid_contract(self) -> None:
        module = _driver()
        self.assertTrue(module.is_genomic_fasta_name("GCA_001874785.1_genomic.fna"))
        self.assertFalse(module.is_genomic_fasta_name("genome.fna"))
        member_names = []
        for assembly in module.REQUEST_ACCESSIONS:
            prefix = f"ncbi_dataset/data/{assembly}/"
            member_names.extend(
                [
                    f"{prefix}{assembly}_genomic.fna",
                    f"{prefix}genomic.gff",
                    f"{prefix}sequence_report.jsonl",
                ]
            )
        layout = module.validate_package_member_layout(member_names)
        self.assertEqual(len(layout), 19)
        member_names[0] = f"ncbi_dataset/data/{module.REQUEST_ACCESSIONS[0]}/nested/x_genomic.fna"
        with self.assertRaises(module.Refusal):
            module.validate_package_member_layout(member_names)
        report = {
            "accession": "GCA_001874785.1",
            "sourceDatabase": "SOURCE_DATABASE_GENBANK",
            "assemblyInfo": {
                "biosample": {"accession": "SAMN04014842"},
                "assemblyStatus": "current",
            },
            "organism": {"taxId": 562},
            "checkmInfo": {"checkmSpeciesTaxId": 562},
        }
        module.validate_assembly_report_identity(
            report,
            biosample="SAMN04014842",
            assembly="GCA_001874785.1",
        )
        report["organism"]["taxId"] = 561
        with self.assertRaises(module.Refusal):
            module.validate_assembly_report_identity(
                report,
                biosample="SAMN04014842",
                assembly="GCA_001874785.1",
            )

    def test_frozen_009_and_012_identity_contract(self) -> None:
        module = _driver()
        current_rows = []
        pairing_rows = []
        for candidate, biosample, assembly in module.FROZEN_TRIPLES:
            common = {
                "candidate_id": candidate,
                "biosample_accession": biosample,
                "assembly_accession": assembly,
                "candidate_status": "record_level_quantitative_mic_candidate_unverified",
                "data_admission_status": "not_admitted",
                "scientific_status": "unverified",
                "pack_authorized": False,
                "training_authorized": False,
                "evaluation_authorized": False,
                "prediction_authorized": False,
            }
            current_rows.append(common)
            pairing_rows.append(
                {
                    **common,
                    "profile_linkage_status": "exact_profile_join",
                    "assembly_identity_status": "metadata_exact_match_candidate_not_admitted",
                    "genome_identity_status": "official_versioned_assembly_identity_verified",
                }
            )
        self.assertEqual(
            module.validate_frozen_rows(current_rows, pairing_rows),
            module.FROZEN_TRIPLES,
        )
        pairing_rows[0]["biosample_accession"] = "SAMN00000000"
        with self.assertRaises(module.Refusal):
            module.validate_frozen_rows(current_rows, pairing_rows)

    def test_write_new_refuses_overwrite(self) -> None:
        module = _driver()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            module.write_new(path, b"{}\n")
            with self.assertRaises(module.Refusal):
                module.write_new(path, b"{}\n")


if __name__ == "__main__":
    unittest.main()
