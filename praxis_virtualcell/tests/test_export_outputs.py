import json

from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def test_export_writes_three_files(tmp_path):
    rt = build_runtime()
    report = rt.run_workflow(VirtualCellRequest.from_dict(_HUMAN))
    rt.export_outputs(str(tmp_path), report)
    for fn in ("trace.json", "prediction_report.json", "provenance.json"):
        assert (tmp_path / fn).is_file()
    trace = json.loads((tmp_path / "trace.json").read_text(encoding="utf-8"))
    assert len(trace) >= 10  # 完整通讯链
