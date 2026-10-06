"""Focused local-only checks for the 016 sanitized summary-shape probe."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

DRIVER = (
    Path(__file__).resolve().parents[3] / "research/mdr_gnb/mic_discovery/"
    "2026-08-17-m1b1-ncbi-summary-schema-probe-current19-ecoli-meropenem/"
    "derived/probe_current19_ncbi_download_summary_shape_v1.py"
)


def _module():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("ncbi_current19_summary_probe", DRIVER)
    if spec is None or spec.loader is None:
        raise RuntimeError("016 summary-schema probe driver cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _summary(*, messages: object = None) -> dict[str, object]:
    value: dict[str, object] = {
        "record_count": 19,
        "available_files": {
            "all_genomic_fasta": {"file_count": 19},
            "genome_gff": {"file_count": 19},
            "sequence_report": {"file_count": 19},
        },
    }
    if messages is not None:
        value["messages"] = messages
    return value


class SummaryShapeTest(unittest.TestCase):
    def test_optional_assembly_count_and_empty_events_are_observed_without_relaxing_counts(
        self,
    ) -> None:
        module = _module()
        shape = module._summary_shape(_summary(messages=[]))

        self.assertEqual(shape["record_count"]["value"], 19)
        self.assertEqual(shape["assembly_count"], {"present": False})

    def test_warning_text_is_never_projected_and_blocks_next_retry_gate(self) -> None:
        module = _module()
        shape = module._summary_shape(
            {
                **_summary(messages=[{"severity": "warning", "message": "private remote text"}]),
                "unexpected_provider_field": {"opaque": "content"},
            }
        )
        rendered = json.dumps(shape, sort_keys=True)

        self.assertNotIn("private remote text", rendered)
        self.assertNotIn("unexpected_provider_field", rendered)
        self.assertEqual(shape["unknown_top_level_key_count"], 1)
        self.assertTrue(shape["messages"]["contains_warning"])

    def test_probe_and_network_budget_require_explicit_transaction_state(self) -> None:
        module = _module()

        with self.assertRaises(module.Refusal):
            module.probe()
        with self.assertRaises(module.Refusal):
            module._NetworkBudget(None)

    def test_only_one_budget_can_reserve_under_one_active_attempt_token(self) -> None:
        module = _module()
        previous_token = module._ACTIVE_ATTEMPT_TOKEN
        previous_used = module._ACTIVE_ATTEMPT_USED
        token = object()
        first = object.__new__(module._NetworkBudget)
        second = object.__new__(module._NetworkBudget)
        first._token = token
        first.used = False
        second._token = token
        second.used = False
        try:
            module._ACTIVE_ATTEMPT_TOKEN = token
            module._ACTIVE_ATTEMPT_USED = False
            first.reserve()
            with self.assertRaises(module.Refusal):
                second.reserve()
        finally:
            module._ACTIVE_ATTEMPT_TOKEN = previous_token
            module._ACTIVE_ATTEMPT_USED = previous_used

    def test_output_directory_entries_are_fsynced_after_create_and_remove(self) -> None:
        module = _module()
        previous_root_fd = module._ACTIVE_ROOT_FD
        original_fsync = os.fsync
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reports = root / "reports"
            reports.mkdir()
            (reports / "entry.json").write_text("{}", encoding="utf-8")
            root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            module._ACTIVE_ROOT_FD = root_fd
            try:
                fsynced_inodes: list[int] = []

                def record_fsync(descriptor: int) -> None:
                    fsynced_inodes.append(os.fstat(descriptor).st_ino)
                    original_fsync(descriptor)

                with mock.patch.object(module.os, "fsync", side_effect=record_fsync):
                    derived_fd = module._open_output_dir(("derived",), create=True)
                    try:
                        self.assertIn(os.fstat(root_fd).st_ino, fsynced_inodes)
                    finally:
                        os.close(derived_fd)

                    fsynced_inodes.clear()
                    reports_fd = os.open(reports, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
                    try:
                        reports_inode = os.fstat(reports_fd).st_ino
                    finally:
                        os.close(reports_fd)
                    with mock.patch.object(module, "_trash_verified_appledouble"):
                        self.assertTrue(module._unlink_created(["reports/entry.json"]))
                    self.assertIn(reports_inode, fsynced_inodes)
            finally:
                module._ACTIVE_ROOT_FD = previous_root_fd
                os.close(root_fd)

    def test_preflight_is_local_only(self) -> None:
        module = _module()

        class NoNetwork:
            def open(self, *args: object, **kwargs: object) -> object:
                raise AssertionError("016 preflight must not make a network request")

        module._OPENER = NoNetwork()
        module._preflight()


if __name__ == "__main__":
    unittest.main()
