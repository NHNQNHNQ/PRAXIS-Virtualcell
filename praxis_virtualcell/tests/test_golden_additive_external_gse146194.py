from __future__ import annotations

import csv
import gzip
from pathlib import Path

import numpy as np
import pytest

from scripts.evaluate_golden_additive_external_gse146194 import (
    StressError,
    _features,
    _paired_bootstrap,
    _parser,
    _selected_counts,
    _selected_groups,
    _truth,
)

_ROOT = Path(__file__).parents[2]
_EVALUATOR = _ROOT / "scripts/evaluate_golden_additive_external_gse146194.py"


def test_selected_groups_applies_frozen_target_and_control_filters(
    tmp_path: Path,
) -> None:
    columns = [
        "cell_barcode",
        "good_coverage",
        "num_guides",
        "number_of_cells",
        "gene",
        "target",
        "sgID_A",
        "type",
        "rank_A",
        "rank_B",
        "sgID_B",
    ]
    target = {
        "cell_barcode": "target-kept",
        "good_coverage": "True",
        "num_guides": "2",
        "number_of_cells": "1",
        "gene": "IRF1",
        "target": "ENSG_TEST_IRF1",
        "sgID_A": "IRF1-guide",
        "type": "1_control",
        "rank_A": "1",
        "rank_B": "NegCtrl11",
        "sgID_B": "NegCtrl11_posB",
    }
    control = {
        "cell_barcode": "control-kept",
        "good_coverage": "True",
        "num_guides": "2",
        "number_of_cells": "1",
        "gene": "Non-Targeting",
        "target": "",
        "sgID_A": "NegCtrl1_posA",
        "type": "control_posB",
        "rank_A": "",
        "rank_B": "",
        "sgID_B": "NegCtrl11_posB",
    }
    rows = [
        target,
        control,
        target | {"cell_barcode": "target-filtered", "good_coverage": "False"},
        control | {"cell_barcode": "control-filtered", "type": "wrong"},
        target
        | {
            "cell_barcode": "other-eligible-target",
            "gene": "OTHER",
            "target": "ENSG_OTHER",
            "sgID_A": "OTHER-guide",
        },
    ]
    path = tmp_path / "identities.csv.gz"
    with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    selection = {
        "required_cell_identity_columns": columns,
        "target_common_filters": {
            "good_coverage": True,
            "num_guides": 2,
            "number_of_cells": 1,
            "type": "1_control",
            "rank_A": "1",
            "rank_B": "NegCtrl11",
            "sgID_B": "NegCtrl11_posB",
        },
        "control_common_filters": {
            "good_coverage": True,
            "num_guides": 2,
            "number_of_cells": 1,
            "gene": "Non-Targeting",
            "type": "control_posB",
            "rank_A": "",
            "rank_B": "",
            "sgID_B": "NegCtrl11_posB",
        },
        "targets": [
            {
                "symbol": "IRF1",
                "ensembl_id": "ENSG_TEST_IRF1",
                "sgID_A": "IRF1-guide",
                "expected_cells": 1,
            }
        ],
        "controls": [{"sgID_A": "NegCtrl1_posA", "expected_cells": 1}],
        "expected_target_cells": 1,
        "expected_control_cells": 1,
    }

    groups, receipt = _selected_groups(
        path,
        selection,
        expected_rows=5,
        eligible_target_ids={"ENSG_TEST_IRF1"},
    )

    assert groups == {"IRF1": ["target-kept"], "__control__": ["control-kept"]}
    assert receipt == {
        "metadata_rows": 5,
        "unique_metadata_barcodes": 5,
        "target_cells": 1,
        "control_cells": 1,
        "eligible_metadata_target_count": 1,
        "target_cell_counts": {"IRF1": 1},
        "control_cell_counts": {"NegCtrl1_posA": 1},
    }
    with pytest.raises(StressError, match="eligible target set changed"):
        _selected_groups(
            path,
            selection,
            expected_rows=5,
            eligible_target_ids={"ENSG_TEST_IRF1", "ENSG_OTHER"},
        )


def _write_matrix(path: Path, dimensions: str, coordinates: str) -> None:
    with gzip.open(path, "wb") as stream:
        stream.write(b"%%MatrixMarket matrix coordinate integer general\n")
        stream.write(b"% synthetic fixture\n")
        stream.write(f"{dimensions}\n{coordinates}".encode())


def test_feature_types_are_frozen_and_guide_capture_is_not_expression(
    tmp_path: Path,
) -> None:
    path = tmp_path / "features.tsv.gz"
    with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
        stream.write("ENSG1\tGENE1\tGene Expression\n")
        stream.write("guide-1\tguide-1\tCRISPR Guide Capture\n")
        stream.write("ENSG2\tGENE2\tGene Expression\n")

    identifiers, symbols, expression_rows = _features(
        path,
        expected_count=3,
        expected_type_counts={"Gene Expression": 2, "CRISPR Guide Capture": 1},
    )

    assert identifiers == ["ENSG1", "guide-1", "ENSG2"]
    assert symbols == ["GENE1", "guide-1", "GENE2"]
    np.testing.assert_array_equal(expression_rows, [True, False, True])
    with pytest.raises(StressError, match="feature identity or type counts changed"):
        _features(
            path,
            expected_count=3,
            expected_type_counts={"Gene Expression": 3},
        )


def test_matrix_market_streams_projection_and_excludes_guides_from_library_sizes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "matrix.mtx.gz"
    _write_matrix(
        path,
        "3 3 6",
        "1 1 2\n2 1 3\n3 1 5\n1 2 7\n2 3 11\n3 3 13",
    )

    counts, library_sizes, parsed = _selected_counts(
        path,
        expected_shape=[3, 3],
        expected_entries=6,
        feature_rows=[2, 0],
        library_feature_rows=[0, 2],
        selected_columns=[2, 0],
    )

    np.testing.assert_array_equal(counts, [[13.0, 5.0], [0.0, 2.0]])
    np.testing.assert_array_equal(library_sizes, [13.0, 7.0])
    assert parsed == 6


def test_matrix_market_rejects_shape_drift_and_malformed_coordinate_rows(
    tmp_path: Path,
) -> None:
    wrong_shape = tmp_path / "wrong-shape.mtx.gz"
    _write_matrix(wrong_shape, "3 4 1", "1 1 1\n")
    with pytest.raises(StressError, match="shape changed"):
        _selected_counts(
            wrong_shape,
            expected_shape=[3, 3],
            expected_entries=1,
            feature_rows=[0],
            library_feature_rows=[0, 1, 2],
            selected_columns=[0],
        )

    malformed = tmp_path / "malformed.mtx.gz"
    _write_matrix(malformed, "3 3 2", "1 1\n2 2 3 4\n")
    with pytest.raises(StressError, match="coordinate row is malformed"):
        _selected_counts(
            malformed,
            expected_shape=[3, 3],
            expected_entries=2,
            feature_rows=[0, 1],
            library_feature_rows=[0, 1, 2],
            selected_columns=[0, 2],
        )


def test_truth_uses_per_cell_log_normalisation_before_group_means() -> None:
    result = _truth(
        counts=np.asarray([[0.0, 1.0, 3.0], [4.0, 1.0, 1.0]]),
        library_sizes=np.full(3, 10000.0),
        group_positions={"IRF1": [0], "__control__": [1, 2]},
    )

    np.testing.assert_allclose(
        result["IRF1"],
        [-(np.log(2.0) + np.log(4.0)) / 2.0, np.log(5.0) - np.log(2.0)],
        rtol=0.0,
        atol=1e-15,
    )


def test_paired_bootstrap_is_the_frozen_seven_target_pcg64_kat() -> None:
    result = _paired_bootstrap([-7.0, -6.0, -5.0, -4.0, -3.0, -2.0, -1.0])

    assert result == {
        "estimate": -4.0,
        "low": -5.428571428571429,
        "high": -2.5714285714285716,
        "unit": "external_target_condition",
        "method": "paired_percentile",
        "rng": "numpy.PCG64",
        "seed": 0,
        "replicates": 2000,
        "interval": [0.025, 0.975],
        "quantile_method": "linear",
    }
    assert _paired_bootstrap([-7.0, -6.0, -5.0, -4.0, -3.0, -2.0, -1.0]) == result
    with pytest.raises(StressError, match="requires seven finite values"):
        _paired_bootstrap([0.0] * 6)


def test_cli_has_no_pack_or_test_input_and_result_claims_remain_bounded() -> None:
    options = {option for action in _parser()._actions for option in action.option_strings}
    assert options == {
        "-h",
        "--help",
        "--protocol",
        "--input-dir",
        "--candidate-root",
        "--comparator-root",
        "--output",
    }

    source = _EVALUATOR.read_text(encoding="utf-8")
    evaluate_body = source[source.index("def evaluate(") : source.index("\ndef _parser(")]
    for boundary in (
        '"record_role": "prospective_external_stress_result_not_p16_not_scientific_evidence"',
        '"golden_test_expression_used": False',
        '"golden_test_outcomes_used": False',
        '"p16_exact_external_gate_satisfied": False',
        '"benchmark_status": "NOT_RUN"',
        '"benchmark_passed": None',
        '"scientifically_validated": False',
        '"promotion_eligible": False',
        '"production_promoted": False',
        '"registry_or_default_route_changed": False',
    ):
        assert boundary in evaluate_body
