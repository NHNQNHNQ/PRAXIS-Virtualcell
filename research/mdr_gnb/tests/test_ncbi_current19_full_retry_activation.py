"""Focused fail-closed checks for the 015 current-19 package retriever."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

DRIVER = (
    Path(__file__).resolve().parents[3] / "research/mdr_gnb/mic_discovery/"
    "2026-08-17-m1b1-ncbi-datasets-full-retry-activation-current19-ecoli-meropenem/"
    "derived/retrieve_current19_ncbi_genome_gff3_activation_v1.py"
)


def _module():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("ncbi_current19_genome_package", DRIVER)
    if spec is None or spec.loader is None:
        raise RuntimeError("015 package retrieval driver cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _summary(*, include_optional_fields: bool = True) -> dict[str, object]:
    summary: dict[str, object] = {
        "record_count": 19,
        "assembly_count": 19,
        "available_files": {
            "all_genomic_fasta": {"file_count": 19},
            "genome_gff": {"file_count": 19},
            "sequence_report": {"file_count": 19},
        },
    }
    if include_optional_fields:
        summary.update({"errors": [], "messages": []})
    return summary


def _report(assembly: str, biosample: str, *, organism_tax_id: int = 562) -> dict[str, object]:
    return {
        "accession": assembly,
        "sourceDatabase": "SOURCE_DATABASE_GENBANK",
        "organism": {"taxId": organism_tax_id},
        "assemblyInfo": {
            "biosample": {"accession": biosample},
            "assemblyStatus": "current",
        },
        "checkmInfo": {"checkmSpeciesTaxId": 562},
        "pairedAccession": assembly.replace("GCA_", "GCF_"),
    }


def _write_package(
    path: Path,
    module: object,
    *,
    extra_member: tuple[str, bytes] | None = None,
    gff_accession: str | None = None,
    gff_seqid: str | None = None,
    report_biosample: str | None = None,
    report_organism_tax_id: int | None = None,
    fasta_accession: str | None = None,
    sequence_accession: str | None = None,
    extra_sequence_accession: str | None = None,
    extra_genomic_fasta: bool = False,
    corrupt_md5: bool = False,
    symlink_member: bool = False,
) -> None:
    """Write the smallest package matching the authorized member layout."""

    members: dict[str, bytes] = {
        "README.md": b"NCBI Datasets package\n",
        "ncbi_dataset/dataset_catalog.json": json.dumps(
            {"assemblies": [{"accession": accession} for accession in module.REQUEST_ACCESSIONS]}
        ).encode(),
    }
    reports: list[str] = []
    for index, (_, biosample, assembly) in enumerate(module.FROZEN_TRIPLES, start=1):
        report_sample = (
            report_biosample if index == 1 and report_biosample is not None else biosample
        )
        report_tax_id = (
            report_organism_tax_id if index == 1 and report_organism_tax_id is not None else 562
        )
        reports.append(
            json.dumps(
                _report(assembly, report_sample, organism_tax_id=report_tax_id), sort_keys=True
            )
        )
        sequence = (
            sequence_accession
            if index == 1 and sequence_accession is not None
            else f"CM{index:06d}.1"
        )
        fasta_sequence = fasta_accession if index == 1 and fasta_accession is not None else sequence
        base = f"ncbi_dataset/data/{assembly}"
        fasta_lines = [f">{fasta_sequence} fixture\nATGC\n"]
        sequence_rows = [
            json.dumps(
                {"assemblyAccession": assembly, "genbankAccession": sequence}, sort_keys=True
            )
        ]
        if index == 1 and extra_sequence_accession is not None:
            fasta_lines.append(f">{extra_sequence_accession} extra\nATGC\n")
            sequence_rows.append(
                json.dumps(
                    {"assemblyAccession": assembly, "genbankAccession": extra_sequence_accession},
                    sort_keys=True,
                )
            )
        members[f"{base}/{assembly}_fixture_genomic.fna"] = "".join(fasta_lines).encode()
        if extra_genomic_fasta and index == 1:
            members[f"{base}/{assembly}_alternate_genomic.fna"] = b">CM000001.1 alternate\nATGC\n"
        directive = (
            gff_accession
            if index == 1 and gff_accession is not None
            else f"NCBI_Assembly:{assembly}"
        )
        feature_seqid = gff_seqid if index == 1 and gff_seqid is not None else sequence
        members[f"{base}/genomic.gff"] = (
            f"##gff-version 3\n#!genome-build-accession {directive}\n"
            f"{feature_seqid}\tfixture\tgene\t1\t4\t.\t+\t.\tID=g{index}\n"
        ).encode()
        members[f"{base}/sequence_report.jsonl"] = ("\n".join(sequence_rows) + "\n").encode()
    members["ncbi_dataset/data/assembly_data_report.jsonl"] = ("\n".join(reports) + "\n").encode()
    if extra_member is not None:
        members[extra_member[0]] = extra_member[1]

    md5_lines = [
        f"{hashlib.md5(content).hexdigest()}  {name}" for name, content in sorted(members.items())
    ]
    if corrupt_md5:
        md5_lines[0] = "0" * 32 + md5_lines[0][32:]
    members["md5sum.txt"] = ("\n".join(md5_lines) + "\n").encode()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(members.items()):
            archive.writestr(name, content)
        if symlink_member:
            link = zipfile.ZipInfo("ncbi_dataset/data/GCA_001874785.1/unsafe-link")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(link, b"target")


def _current_row(candidate: str, biosample: str, assembly: str) -> dict[str, object]:
    return {
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


def _pairing_row(candidate: str, biosample: str, assembly: str) -> dict[str, object]:
    return {
        **_current_row(candidate, biosample, assembly),
        "profile_linkage_status": "exact_profile_join",
        "assembly_identity_status": "metadata_exact_match_candidate_not_admitted",
        "genome_identity_status": "official_versioned_assembly_identity_verified",
    }


class RequestAndFrozenIdentityTest(unittest.TestCase):
    def test_fixed_request_has_exact_authorized_body_and_endpoints(self) -> None:
        module = _module()

        self.assertEqual(
            module.REQUEST_BODY,
            {
                "accessions": list(module.REQUEST_ACCESSIONS),
                "include_annotation_type": ["GENOME_FASTA", "GENOME_GFF", "SEQUENCE_REPORT"],
                "hydrated": "FULLY_HYDRATED",
            },
        )
        self.assertEqual(
            module.ENDPOINTS,
            (
                "https://api.ncbi.nlm.nih.gov/datasets/v2/genome/download_summary",
                "https://api.ncbi.nlm.nih.gov/datasets/v2/genome/download",
            ),
        )
        self.assertEqual(len(module.FROZEN_TRIPLES), 19)
        self.assertEqual(set(module.REQUEST_ACCESSIONS), {row[2] for row in module.FROZEN_TRIPLES})

    def test_summary_needs_exact_counts_file_counts_and_no_error(self) -> None:
        module = _module()
        module.validate_download_summary(_summary())

        module.validate_download_summary(_summary(include_optional_fields=False))

        missing = _summary()
        missing["available_files"]["genome_gff"] = {"file_count": 18}
        with self.assertRaises(module.Refusal):
            module.validate_download_summary(missing)

        errored = _summary()
        errored["errors"] = [{"code": "unavailable"}]
        with self.assertRaises(module.Refusal):
            module.validate_download_summary(errored)

    def test_summary_receipt_is_limited_to_validated_counts(self) -> None:
        module = _module()
        receipt = module._summary_shape_receipt(_summary(include_optional_fields=False))

        self.assertEqual(receipt["http_status"], 200)
        self.assertEqual(receipt["record_count"], 19)
        self.assertEqual(receipt["assembly_count"], 19)
        self.assertEqual(receipt["errors"], {"present": False, "count": 0})
        self.assertEqual(receipt["messages"], {"present": False, "count": 0})
        self.assertEqual(
            receipt["available_file_counts"],
            {
                "all_genomic_fasta": 19,
                "genome_gff": 19,
                "sequence_report": 19,
            },
        )

    def test_exact_009_and_012_triples_are_required(self) -> None:
        module = _module()
        current = [_current_row(*triple) for triple in module.FROZEN_TRIPLES]
        pairing = [_pairing_row(*triple) for triple in module.FROZEN_TRIPLES]

        self.assertEqual(module.validate_frozen_rows(current, pairing), module.FROZEN_TRIPLES)
        pairing[0]["genome_identity_status"] = "versioned_assembly_identity_unresolved"
        with self.assertRaises(module.Refusal):
            module.validate_frozen_rows(current, pairing)

    def test_preflight_is_local_only(self) -> None:
        module = _module()

        class NoNetwork:
            def open(self, *args: object, **kwargs: object) -> object:
                raise AssertionError("preflight must not make a network request")

        module._OPENER = NoNetwork()
        module.preflight()

    def test_network_sequence_is_transaction_bound_and_one_shot(self) -> None:
        module = _module()

        with self.assertRaises(module.Refusal):
            module.retrieve_current19_package()

        with self.assertRaises(module.Refusal):
            module._NetworkSequence("a" * 64)

        prior = module._ACTIVE_OUTPUT_ROOT_FD
        module._ACTIVE_OUTPUT_ROOT_FD = 0
        try:
            sequence = module._NetworkSequence("a" * 64)
            sequence.reserve(module.ENDPOINTS[0])
            with self.assertRaises(module.Refusal):
                sequence.reserve(module.ENDPOINTS[0])
            sequence.accept_summary()
            sequence.reserve(module.ENDPOINTS[1])
            with self.assertRaises(module.Refusal):
                sequence.reserve(module.ENDPOINTS[1])
            self.assertEqual(sequence.request_count, 2)
        finally:
            module._ACTIVE_OUTPUT_ROOT_FD = prior


class PackageValidationTest(unittest.TestCase):
    def test_valid_minimal_current19_package_has_exact_assets(self) -> None:
        module = _module()
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package.zip"
            _write_package(package, module)
            result = module.inspect_package(package, module.FROZEN_TRIPLES)

        self.assertEqual(result["assembly_count"], 19)
        self.assertEqual(set(result["assemblies"]), set(module.REQUEST_ACCESSIONS))
        self.assertTrue(all(entry["md5_verified"] for entry in result["assets"]))

    def test_zip_slip_symlink_and_unknown_member_fail_closed(self) -> None:
        module = _module()
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package.zip"
            _write_package(package, module, extra_member=("../escape", b"x"))
            with self.assertRaises(module.Refusal):
                module.inspect_package(package, module.FROZEN_TRIPLES)

            _write_package(package, module, extra_genomic_fasta=True)
            with self.assertRaises(module.Refusal):
                module.inspect_package(package, module.FROZEN_TRIPLES)

            _write_package(package, module, symlink_member=True)
            with self.assertRaises(module.Refusal):
                module.inspect_package(package, module.FROZEN_TRIPLES)

    def test_package_validation_cannot_substitute_another_19_item_scope(self) -> None:
        module = _module()
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package.zip"
            _write_package(package, module)
            with self.assertRaises(module.Refusal):
                module.inspect_package(package, tuple(reversed(module.FROZEN_TRIPLES)))

    def test_duplicate_json_keys_fail_closed(self) -> None:
        module = _module()
        with self.assertRaises(module.Refusal):
            module._json_object(b'{"accession":"first","accession":"second"}', "fixture")

    def test_gff_fasta_sequence_report_and_report_identity_mismatches_fail(self) -> None:
        module = _module()
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package.zip"
            for kwargs in (
                {"gff_accession": "GCA_000000000.1"},
                {"gff_seqid": "CM999999.1"},
                {"fasta_accession": "CM999999.1"},
                {"extra_sequence_accession": "CM999998.1"},
                {"report_biosample": "SAMN00000000"},
                {"report_organism_tax_id": 1438691},
                {"corrupt_md5": True},
            ):
                _write_package(package, module, **kwargs)
                with self.assertRaises(module.Refusal):
                    module.inspect_package(package, module.FROZEN_TRIPLES)


if __name__ == "__main__":
    unittest.main()
