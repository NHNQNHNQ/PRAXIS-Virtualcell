"""Focused fail-closed checks for the 017 current-19 package retriever."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

DRIVER = (
    Path(__file__).resolve().parents[3] / "research/mdr_gnb/mic_discovery/"
    "2026-08-17-m1b1-ncbi-datasets-fresh-retrieval-current19-ecoli-meropenem/"
    "derived/retrieve_current19_ncbi_genome_gff3_fresh_retrieval_v1.py"
)


def _module():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("ncbi_current19_genome_package", DRIVER)
    if spec is None or spec.loader is None:
        raise RuntimeError("017 package retrieval driver cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _summary(
    *,
    include_assembly_count: bool = False,
    include_events: bool = False,
    include_documented_extras: bool = True,
) -> dict[str, object]:
    summary: dict[str, object] = {
        "record_count": 19,
        "available_files": {
            "all_genomic_fasta": {"file_count": 19},
            "genome_gff": {"file_count": 19},
            "sequence_report": {"file_count": 19},
        },
    }
    if include_assembly_count:
        summary["assembly_count"] = 19
    if include_events:
        summary.update({"errors": [], "messages": []})
    if include_documented_extras:
        summary.update(
            {
                "resource_updated_on": "2026-08-17T00:00:00Z",
                "hydrated": {},
                "dehydrated": {},
            }
        )
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

    def test_summary_accepts_the_observed_optional_shape_and_rejects_ambiguity(self) -> None:
        module = _module()
        module.validate_download_summary(_summary())
        module.validate_download_summary(_summary(include_assembly_count=True, include_events=True))

        bad_assembly = _summary(include_assembly_count=True)
        bad_assembly["assembly_count"] = 18
        with self.assertRaises(module.Refusal):
            module.validate_download_summary(bad_assembly)
        for malformed_value in (True, "19"):
            malformed_assembly = _summary(include_assembly_count=True)
            malformed_assembly["assembly_count"] = malformed_value
            with self.assertRaises(module.Refusal):
                module.validate_download_summary(malformed_assembly)

        missing = _summary()
        missing["available_files"]["genome_gff"] = {"file_count": 18}
        with self.assertRaises(module.Refusal):
            module.validate_download_summary(missing)

        errored = _summary()
        errored["errors"] = [{"code": "unavailable"}]
        with self.assertRaises(module.Refusal):
            module.validate_download_summary(errored)

        warned = _summary()
        warned["messages"] = [{"severity": "warning"}]
        with self.assertRaises(module.Refusal):
            module.validate_download_summary(warned)

        malformed_event = _summary()
        malformed_event["errors"] = "not an array"
        with self.assertRaises(module.Refusal):
            module.validate_download_summary(malformed_event)

        malformed_message = _summary()
        malformed_message["messages"] = "not an array"
        with self.assertRaises(module.Refusal):
            module.validate_download_summary(malformed_message)

        malformed_documented = _summary()
        malformed_documented["hydrated"] = "not an object"
        with self.assertRaises(module.Refusal):
            module.validate_download_summary(malformed_documented)

        unknown = _summary()
        unknown["new_provider_field"] = {}
        with self.assertRaises(module.Refusal):
            module.validate_download_summary(unknown)

    def test_summary_receipt_is_limited_to_validated_counts(self) -> None:
        module = _module()
        receipt = module._summary_shape_receipt(_summary())

        self.assertEqual(receipt["http_status"], 200)
        self.assertEqual(receipt["record_count"], 19)
        self.assertEqual(receipt["assembly_count"], {"present": False})
        self.assertEqual(receipt["unknown_top_level_key_count"], 0)
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
            module._NetworkSequence(object())

        prior = module._ACTIVE_OUTPUT_ROOT_FD
        prior_token = module._ACTIVE_ATTEMPT_TOKEN
        prior_created = module._ACTIVE_SEQUENCE_CREATED
        try:
            module._ACTIVE_OUTPUT_ROOT_FD = 0
            token = object()
            module._ACTIVE_ATTEMPT_TOKEN = token
            module._ACTIVE_SEQUENCE_CREATED = False
            reservation = module._AttemptReservation("a" * 64, token)
            with mock.patch.object(module, "_verify_attempt_reservation"):
                sequence = module._NetworkSequence(reservation)
                sequence.reserve(module.ENDPOINTS[0])
                with self.assertRaises(module.Refusal):
                    sequence.reserve(module.ENDPOINTS[0])
                sequence.accept_summary()
                sequence.reserve(module.ENDPOINTS[1])
                with self.assertRaises(module.Refusal):
                    sequence.reserve(module.ENDPOINTS[1])
                self.assertEqual(sequence.request_count, 2)
                with self.assertRaises(module.Refusal):
                    module._NetworkSequence(reservation)
        finally:
            module._ACTIVE_OUTPUT_ROOT_FD = prior
            module._ACTIVE_ATTEMPT_TOKEN = prior_token
            module._ACTIVE_SEQUENCE_CREATED = prior_created

    def test_durable_reservation_precedes_the_capability_and_blocks_a_second_one(self) -> None:
        module = _module()
        prior_root = module.OUTPUT_ROOT
        prior_fd = module._ACTIVE_OUTPUT_ROOT_FD
        prior_token = module._ACTIVE_ATTEMPT_TOKEN
        prior_created = module._ACTIVE_SEQUENCE_CREATED
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            try:
                module.OUTPUT_ROOT = root
                module._ACTIVE_OUTPUT_ROOT_FD = descriptor
                module._ACTIVE_ATTEMPT_TOKEN = None
                module._ACTIVE_SEQUENCE_CREATED = False
                identities = {
                    "authorization": {"sha256": "a" * 64},
                    "prerequisites": {},
                    "driver": {"sha256": "b" * 64},
                    "inputs": {},
                }
                with mock.patch.object(module, "_require_active_authorization"):
                    reservation = module._create_attempt_reservation(
                        identities, (), persistent_created=[], incomplete_created=[]
                    )
                    self.assertTrue((root / module.ATTEMPT_RESERVATION_PATH).is_file())
                    self.assertTrue((root / f"{module.ATTEMPT_RESERVATION_PATH}.sha256").is_file())
                    with self.assertRaises(module.Refusal):
                        module._create_attempt_reservation(
                            identities, (), persistent_created=[], incomplete_created=[]
                        )
                    sequence = module._NetworkSequence(reservation)
                    sequence.reserve(module.ENDPOINTS[0])
            finally:
                module.OUTPUT_ROOT = prior_root
                module._ACTIVE_OUTPUT_ROOT_FD = prior_fd
                module._ACTIVE_ATTEMPT_TOKEN = prior_token
                module._ACTIVE_SEQUENCE_CREATED = prior_created
                os.close(descriptor)

    def test_incomplete_persistent_pair_is_cleaned_before_retention(self) -> None:
        module = _module()
        prior_root = module.OUTPUT_ROOT
        prior_fd = module._ACTIVE_OUTPUT_ROOT_FD
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            try:
                module.OUTPUT_ROOT = root
                module._ACTIVE_OUTPUT_ROOT_FD = descriptor
                original_write = module._write_new_bytes

                def fail_sidecar(
                    relative: str, content: bytes, *, created: list[str] | None = None
                ) -> str:
                    if relative.endswith(".sha256"):
                        raise OSError("fixture sidecar failure")
                    return original_write(relative, content, created=created)

                persistent_created: list[str] = []
                incomplete_created: list[str] = []
                with (
                    mock.patch.object(module, "_require_active_authorization"),
                    mock.patch.object(module, "_write_new_bytes", side_effect=fail_sidecar),
                ):
                    with self.assertRaises(OSError):
                        module._write_persistent_with_sidecar(
                            module.MANIFEST_PATH,
                            b"{}",
                            persistent_created=persistent_created,
                            incomplete_created=incomplete_created,
                        )
                self.assertEqual(persistent_created, [])
                self.assertEqual(incomplete_created, [module.MANIFEST_PATH])
                self.assertTrue(module._cleanup_created(incomplete_created))
                self.assertFalse((root / module.MANIFEST_PATH).exists())
            finally:
                module.OUTPUT_ROOT = prior_root
                module._ACTIVE_OUTPUT_ROOT_FD = prior_fd
                os.close(descriptor)

    def test_staging_appledouble_is_disposed_before_staging_is_untracked(self) -> None:
        module = _module()
        data_created = [module.STAGING_ZIP_PATH]
        observed: list[Path] = []

        def record_disposal(paths: tuple[Path, ...], *, label: str) -> None:
            self.assertEqual(label, "output")
            observed.extend(paths)

        with (
            mock.patch.object(module, "_unlink_relative"),
            mock.patch.object(module, "_trash_verified_appledouble", side_effect=record_disposal),
        ):
            module._dispose_staging_zip(data_created, [])
        self.assertIn(
            module.OUTPUT_ROOT / "derived/._current19-ncbi-genome-gff3-download.zip.part",
            observed,
        )
        self.assertEqual(data_created, [])

        data_created = [module.STAGING_ZIP_PATH]
        with (
            mock.patch.object(module, "_unlink_relative"),
            mock.patch.object(
                module,
                "_trash_verified_appledouble",
                side_effect=module.Refusal("fixture disposal failure"),
            ),
        ):
            with self.assertRaises(module.Refusal):
                module._dispose_staging_zip(data_created, [])
        self.assertEqual(data_created, [module.STAGING_ZIP_PATH])

        data_created = [module.STAGING_ZIP_PATH]
        with (
            mock.patch.object(module, "_unlink_relative"),
            mock.patch.object(module, "_trash_verified_appledouble"),
            mock.patch.object(module, "_created_paths_are_absent", return_value=False),
        ):
            with self.assertRaises(module.Refusal):
                module._dispose_staging_zip(data_created, [])
        self.assertEqual(data_created, [module.STAGING_ZIP_PATH])

    def test_cleanup_requires_safe_and_verified_absence(self) -> None:
        module = _module()
        with mock.patch.object(
            module, "_open_output_dir", side_effect=module.Refusal("fixture unsafe directory")
        ):
            with self.assertRaises(module.Refusal):
                module._unlink_relative("derived/unsafe")

        prior_root = module.OUTPUT_ROOT
        prior_fd = module._ACTIVE_OUTPUT_ROOT_FD
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "derived").mkdir()
            (root / "derived/object").write_bytes(b"fixture")
            descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            try:
                module.OUTPUT_ROOT = root
                module._ACTIVE_OUTPUT_ROOT_FD = descriptor
                with mock.patch.object(module, "_unlink_relative"):
                    self.assertFalse(module._cleanup_created(["derived/object"]))
            finally:
                module.OUTPUT_ROOT = prior_root
                module._ACTIVE_OUTPUT_ROOT_FD = prior_fd
                os.close(descriptor)


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
        targets = result["normalized_member_paths"]
        self.assertIsNone(targets["README.md"])
        self.assertIsNone(targets["ncbi_dataset/dataset_catalog.json"])
        self.assertEqual(sum(target is not None for target in targets.values()), 59)

    def test_success_allowlist_excludes_transient_and_unneeded_package_files(self) -> None:
        module = _module()
        allowed = module._allowed_postwrite_files()

        self.assertNotIn(module.STAGING_ZIP_PATH, allowed)
        self.assertFalse(any(path.startswith("raw/") for path in allowed))
        self.assertNotIn("package/README.md", allowed)
        self.assertNotIn("package/dataset_catalog.json", allowed)
        self.assertIn("package/md5sum.txt", allowed)
        self.assertIn("package/assembly_data_report.jsonl", allowed)

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
