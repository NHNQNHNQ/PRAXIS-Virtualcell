"""Small, offline contracts for the current-19 annotation observation builder."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

DRIVER = (
    Path(__file__).resolve().parents[3]
    / (
        "research/mdr_gnb/mic_discovery/"
        "2026-08-17-m1b1-current19-local-gene-feature-observation-ecoli-meropenem"
    )
    / "derived/build_current19_gene_feature_observations_v1.py"
)


def _module():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("current19_gene_feature_observation", DRIVER)
    if spec is None or spec.loader is None:
        raise RuntimeError("feature observation driver cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Current19GeneFeatureObservationTest(unittest.TestCase):
    def test_circular_origin_feature_is_preserved_as_two_segments(self) -> None:
        module = _module()
        status, segments = module._coordinate(8, 13, 10, True)

        self.assertEqual(status, "origin_spanning_circular_valid")
        self.assertEqual(segments, [{"start": 8, "end": 10}, {"start": 1, "end": 3}])

    def test_non_circular_out_of_range_feature_is_not_silently_normalized(self) -> None:
        module = _module()
        status, segments = module._coordinate(8, 13, 10, False)

        self.assertEqual(status, "out_of_range_observed")
        self.assertEqual(segments, [])

    def test_parser_keeps_gene_and_pseudogene_but_not_cds(self) -> None:
        module = _module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fasta = root / "genome.fna"
            gff = root / "genome.gff3"
            fasta.write_text(">CP000001.1 synthetic\nAAAAAAAAAA\n", encoding="utf-8")
            gff.write_text(
                "##gff-version 3\n"
                "CP000001.1\tNCBI\tregion\t1\t10\t.\t+\t.\tID=region;Is_circular=true\n"
                "CP000001.1\tNCBI\tgene\t8\t13\t.\t+\t.\tID=gene-a;locus_tag=A\n"
                "CP000001.1\tNCBI\tpseudogene\t2\t4\t.\t-\t.\tID=gene-b;locus_tag=B\n"
                "CP000001.1\tNCBI\tCDS\t8\t13\t.\t+\t0\tID=cds-a;Parent=gene-a\n",
                encoding="utf-8",
            )

            circular, features = module._parse_gff(
                gff, "GCA_000000001.1", module._parse_fasta(fasta)
            )

        self.assertEqual(circular, {"CP000001.1": True})
        self.assertEqual([row["feature_type"] for row in features], ["gene", "pseudogene"])
        self.assertEqual(features[0]["coordinate_status"], "origin_spanning_circular_valid")

    def test_builder_has_no_network_client_or_negative_call_language(self) -> None:
        source = DRIVER.read_text(encoding="utf-8")

        for forbidden in ("urllib", "requests", "socket", "http.client", "negative_gene_call"):
            self.assertNotIn(forbidden, source)
        self.assertIn("source_annotation_observed_not_negative_call", source)


if __name__ == "__main__":
    unittest.main()
