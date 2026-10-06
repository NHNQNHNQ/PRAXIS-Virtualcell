"""Offline contract tests for the 019 NCBI package validator."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import unittest
import zipfile
from pathlib import Path

DRIVER_PATH = (
    Path(__file__).parents[1]
    / "mic_discovery/"
    "2026-08-17-m1b1-ncbi-datasets-schema-corrected-fresh-retrieval-current19-ecoli-meropenem/"
    "derived/retrieve_current19_ncbi_genome_gff3_schema_corrected_fresh_retrieval_v1.py"
)
SPEC = importlib.util.spec_from_file_location("current19_retrieval", DRIVER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load 019 retrieval driver")
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)


def _package(*, omit_checksum: str | None = None, extra_member: str | None = None) -> io.BytesIO:
    files: dict[str, bytes] = {
        "README.md": b"transient packaging text\n",
        "ncbi_dataset/data/dataset_catalog.json": b"{}\n",
    }
    report_rows = []
    for _, biosample, assembly in DRIVER.FROZEN_TRIPLES:
        base = f"ncbi_dataset/data/{assembly}"
        sequence = "NZ_CP000001.1"
        files[f"{base}/{assembly}_genomic.fna"] = f">{sequence}\nA\n".encode()
        files[f"{base}/genomic.gff"] = (
            f"#!genome-build-accession {assembly}\n"
            f"{sequence}\tRefSeq\tgene\t1\t1\t.\t+\t.\tID=g1\n"
        ).encode()
        files[f"{base}/sequence_report.jsonl"] = _json_line(
            {"assemblyAccession": assembly, "genbankAccession": sequence}
        )
        report_rows.append(
            {
                "accession": assembly,
                "assemblyInfo": {
                    "assemblyStatus": "current",
                    "biosample": {"accession": biosample},
                },
                "checkmInfo": {"checkmSpeciesTaxId": 562},
                "organism": {"taxId": 562},
                "sourceDatabase": "SOURCE_DATABASE_GENBANK",
            }
        )
    files["ncbi_dataset/data/assembly_data_report.jsonl"] = b"".join(
        _json_line(row) for row in report_rows
    )
    if extra_member is not None:
        files[extra_member] = b"unexpected\n"
    checksummed = sorted(name for name in files if name != omit_checksum and name != "README.md")
    files["md5sum.txt"] = b"".join(
        f"{hashlib.md5(files[name]).hexdigest()}  {name}\n".encode() for name in checksummed
    )
    package = io.BytesIO()
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            archive.writestr(name, files[name])
    package.seek(0)
    return package


def _json_line(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


class PackageContractTest(unittest.TestCase):
    def test_frozen_triples_match_both_local_ledgers(self) -> None:
        triples, _ = DRIVER._load_frozen_inputs()
        self.assertEqual(triples, DRIVER.FROZEN_TRIPLES)

    def test_accepts_current_catalog_and_unchecksummed_readme(self) -> None:
        result = DRIVER.inspect_package(_package(), DRIVER.FROZEN_TRIPLES)
        self.assertEqual(result["assembly_count"], 19)
        self.assertIsNone(result["normalized_member_paths"]["ncbi_dataset/data/dataset_catalog.json"])
        self.assertNotIn("ncbi_dataset/dataset_catalog.json", result["normalized_member_paths"])

    def test_rejects_missing_checksum_for_data_member(self) -> None:
        member = "ncbi_dataset/data/dataset_catalog.json"
        with self.assertRaises(DRIVER.Refusal):
            DRIVER.inspect_package(_package(omit_checksum=member), DRIVER.FROZEN_TRIPLES)

    def test_rejects_old_catalog_location(self) -> None:
        with self.assertRaises(DRIVER.Refusal):
            DRIVER.inspect_package(
                _package(extra_member="ncbi_dataset/dataset_catalog.json"), DRIVER.FROZEN_TRIPLES
            )

    def test_rejects_unrequested_tsv_member(self) -> None:
        with self.assertRaises(DRIVER.Refusal):
            DRIVER.inspect_package(
                _package(extra_member="ncbi_dataset/data/data_summary.tsv"), DRIVER.FROZEN_TRIPLES
            )

    def test_request_body_explicitly_excludes_tsv(self) -> None:
        self.assertIs(DRIVER.REQUEST_BODY["include_tsv"], False)


if __name__ == "__main__":
    unittest.main()
