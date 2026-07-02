"""GAP-E2E harness 纯逻辑单测。"""
import importlib.util
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("e2e_skill_matrix", _REPO / "scripts" / "e2e_skill_matrix.py")
esm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(esm)


def test_done_real_when_ok_and_contract_keys():
    tr = {"ok": True, "value": {"ok": True, "poses": [{"rank": 1}], "best_pose": {"rank": 1}}, "error": None}
    assert esm.classify_verdict(tr, ["poses", "best_pose"]) == "DONE_real"


def test_na_when_simulated():
    tr = {"ok": True, "value": {"ok": True, "poses": [1], "diagnostics": {"simulated": True}}, "error": None}
    assert esm.classify_verdict(tr, ["poses"]) == "N-A"


def test_na_when_error_marks_not_applicable():
    tr = {"ok": False, "value": {"ok": False, "error": "N/A: composite skill 需上层编排"}, "error": None}
    assert esm.classify_verdict(tr, ["poses"]) == "N-A"


def test_red_when_software_missing():
    tr = {"ok": True, "value": {"ok": False, "error": "gnina 未在 PATH;请走 praxis-dock env"}, "error": None}
    assert esm.classify_verdict(tr, ["poses"]) == "RED"


def test_red_when_env_activate_failed():
    tr = {"ok": False, "value": {}, "error": "ssh/远端命令失败(rc=1) conda activate praxis-x"}
    assert esm.classify_verdict(tr, ["poses"]) == "RED"


def test_error_when_ok_but_no_contract_keys():
    tr = {"ok": True, "value": {"ok": True, "unexpected": 1}, "error": None}
    assert esm.classify_verdict(tr, ["poses", "best_pose"]) == "ERROR"


def test_error_when_timeout():
    tr = {"ok": False, "value": {}, "error": "命令超时(>600s),已 kill"}
    assert esm.classify_verdict(tr, ["poses"]) == "ERROR"


import csv  # noqa: E402


def test_load_inputs_filters_by_green(tmp_path, monkeypatch):
    (tmp_path / "_audit").mkdir()
    (tmp_path / "_audit" / "green_skills.json").write_text(
        '{"dock": ["vina_gnina_dock", "redock_benchmark"]}', encoding="utf-8")
    (tmp_path / "_audit" / "e2e_inputs").mkdir()
    (tmp_path / "_audit" / "e2e_inputs" / "docking.json").write_text(
        '{"vina_gnina_dock": {"brain": "dock", "inputs": {"simulate": false}, "contract_keys": ["poses"]}}',
        encoding="utf-8")
    monkeypatch.setattr(esm, "AUDIT", tmp_path / "_audit")
    monkeypatch.setattr(esm, "GREEN_SKILLS", tmp_path / "_audit" / "green_skills.json")
    loaded = esm.load_inputs("docking", green_archetype="dock")
    assert "vina_gnina_dock" in loaded
    assert loaded["vina_gnina_dock"]["contract_keys"] == ["poses"]
    assert loaded["vina_gnina_dock"]["inputs"]["simulate"] is False


def test_update_inventory_csv_promotes_done_real(tmp_path, monkeypatch):
    csvp = tmp_path / "inv.csv"
    csvp.write_text("brain,skill,archetype,status\ndock,vina_gnina_dock,docking,TODO\ndock,redock_benchmark,docking,TODO\n", encoding="utf-8")  # noqa: E501
    monkeypatch.setattr(esm, "INVENTORY_CSV", csvp)
    esm.update_inventory_csv({("dock", "vina_gnina_dock"): "DONE_real", ("dock", "redock_benchmark"): "RED"})
    rows = list(csv.DictReader(csvp.open(encoding="utf-8")))
    by = {(r["brain"], r["skill"]): r["status"] for r in rows}
    assert by[("dock", "vina_gnina_dock")] == "DONE_real"
    assert by[("dock", "redock_benchmark")] == "TODO"


def test_update_inventory_csv_idempotent(tmp_path, monkeypatch):
    csvp = tmp_path / "inv.csv"
    csvp.write_text("brain,skill,archetype,status\ndock,vina_gnina_dock,docking,DONE_real\n", encoding="utf-8")
    monkeypatch.setattr(esm, "INVENTORY_CSV", csvp)
    esm.update_inventory_csv({("dock", "vina_gnina_dock"): "DONE_real"})
    assert csvp.read_text(encoding="utf-8").count("DONE_real") == 1


import asyncio  # noqa: E402


def test_run_archetype_with_fake_executor(tmp_path, monkeypatch):
    async def fake_exec(name, brain, inputs):
        if name == "vina_gnina_dock":
            return {"ok": True, "value": {"ok": True, "poses": [1], "best_pose": {"rank": 1}}, "error": None}
        if name == "induced_fit_docking":
            return {"ok": False, "value": {"ok": False, "error": "N/A: Schrödinger 商业软件未装"}, "error": None}
        return {"ok": True, "value": {"ok": False, "error": "gnina 未在 PATH"}, "error": None}

    aud = tmp_path / "_audit"
    (aud / "e2e_inputs").mkdir(parents=True)
    (aud / "green_skills.json").write_text('{"dock":["vina_gnina_dock","induced_fit_docking","covalent_docking"]}', encoding="utf-8")  # noqa: E501
    (aud / "e2e_inputs" / "docking.json").write_text(json.dumps({
        "vina_gnina_dock": {"brain": "dock", "inputs": {"simulate": False}, "contract_keys": ["poses", "best_pose"]},
        "induced_fit_docking": {"brain": "dock", "inputs": {"simulate": False}, "contract_keys": ["poses"], "skip": False},  # noqa: E501
        "covalent_docking": {"brain": "dock", "inputs": {"simulate": False}, "contract_keys": ["poses"]},
    }), encoding="utf-8")
    (aud / "skill_real_impl_inventory.csv").write_text(
        "brain,skill,archetype,status\ndock,vina_gnina_dock,docking,TODO\ndock,induced_fit_docking,docking,TODO\ndock,covalent_docking,docking,TODO\n", encoding="utf-8")  # noqa: E501
    monkeypatch.setattr(esm, "AUDIT", aud)
    monkeypatch.setattr(esm, "GREEN_SKILLS", aud / "green_skills.json")
    monkeypatch.setattr(esm, "INVENTORY_CSV", aud / "skill_real_impl_inventory.csv")

    results = asyncio.run(esm.run_archetype("docking", green_archetype="dock", executor=fake_exec))
    by = {r["skill"]: r["verdict"] for r in results}
    assert by["vina_gnina_dock"] == "DONE_real"
    assert by["induced_fit_docking"] == "N-A"
    assert by["covalent_docking"] == "RED"
    rep = json.loads((aud / "e2e_results_docking.json").read_text(encoding="utf-8"))
    assert len(rep) == 3
    rows = list(csv.DictReader((aud / "skill_real_impl_inventory.csv").open(encoding="utf-8")))
    assert {(r["skill"], r["status"]) for r in rows} >= {("vina_gnina_dock", "DONE_real"), ("covalent_docking", "TODO")}


def test_run_archetype_skip_branch(tmp_path, monkeypatch):
    """skip:True 的 skill 不调 executor,verdict=SKIPPED,evidence/error 为 None,CSV 不升。"""
    async def fake_exec(name, brain, inputs):
        raise AssertionError("skip 的 skill 不应调 executor")

    aud = tmp_path / "_audit"
    (aud / "e2e_inputs").mkdir(parents=True)
    (aud / "green_skills.json").write_text('{"dock":["af3_complex_predict"]}', encoding="utf-8")
    (aud / "e2e_inputs" / "docking.json").write_text(json.dumps({
        "af3_complex_predict": {"brain": "dock", "inputs": {"simulate": False}, "contract_keys": ["x"], "skip": True},
    }), encoding="utf-8")
    (aud / "skill_real_impl_inventory.csv").write_text(
        "brain,skill,archetype,status\ndock,af3_complex_predict,docking,TODO\n", encoding="utf-8")
    monkeypatch.setattr(esm, "AUDIT", aud)
    monkeypatch.setattr(esm, "GREEN_SKILLS", aud / "green_skills.json")
    monkeypatch.setattr(esm, "INVENTORY_CSV", aud / "skill_real_impl_inventory.csv")

    results = asyncio.run(esm.run_archetype("docking", green_archetype="dock", executor=fake_exec))
    assert len(results) == 1
    assert results[0]["verdict"] == "SKIPPED"
    assert results[0]["evidence"] is None and results[0]["error"] is None
    rows = list(csv.DictReader((aud / "skill_real_impl_inventory.csv").open(encoding="utf-8")))
    assert rows[0]["status"] == "TODO"  # SKIPPED 非 DONE_real,不回写


# --- SkillExec 真跑 value 形态(staging 实测):{execution_plan, ok, result, exec_via},
# run.py 输出嵌在 value["result"]。classify_verdict 须解到 result 层。---

def test_done_real_with_skillexec_wrapper_shape():
    tr = {"ok": True, "value": {
        "execution_plan": {"skill": "vina_gnina_dock"},
        "ok": True, "exec_via": "ssh zkyd@host",
        "result": {"ok": True, "poses": [1], "best_pose": {"rank": 1}, "redock_self_test": {}},
    }, "error": None}
    assert esm.classify_verdict(tr, ["poses", "best_pose", "redock_self_test"]) == "DONE_real"


def test_na_with_wrapper_simulated():
    tr = {"ok": True, "value": {"ok": True, "exec_via": "ssh",
          "result": {"ok": True, "poses": [1], "diagnostics": {"simulated": True}}}, "error": None}
    assert esm.classify_verdict(tr, ["poses"]) == "N-A"


def test_red_with_wrapper_software_missing():
    tr = {"ok": True, "value": {"ok": True, "exec_via": "ssh",
          "result": {"ok": False, "error": "gnina 未在 PATH"}}, "error": None}
    assert esm.classify_verdict(tr, ["poses"]) == "RED"


def test_incomplete_when_input_not_provided():
    """策展输入没给齐数据文件 → INCOMPLETE(非 skill 缺陷,与真崩 ERROR 区分)。"""
    tr = {"ok": True, "value": {"ok": True, "exec_via": "ssh",
          "result": {"ok": False, "error": "ligand_sdf 不存在: None"}}, "error": None}
    assert esm.classify_verdict(tr, ["poses"]) == "INCOMPLETE"


def test_error_when_genuine_crash():
    """真跑崩(non-zero exit,stderr 无 env 坏库线索)→ ERROR。"""
    tr = {"ok": True, "value": {"ok": True, "exec_via": "ssh",
          "result": {"ok": False, "error": "non-zero exit 1", "stderr": "Traceback ... ValueError: bad pose"}}, "error": None}  # noqa: E501
    assert esm.classify_verdict(tr, ["poses"]) == "ERROR"


def test_red_when_env_broken_in_stderr():
    """env 装坏(torch/CUDA import 报错在 stderr,error 只有 non-zero exit)→ RED 而非 ERROR。"""
    tr = {"ok": True, "value": {"ok": True, "exec_via": "ssh", "result": {
        "ok": False, "error": "non-zero exit 1",
        "stderr": "ImportError: .../torch/lib/libcusparse.so.12: undefined symbol: __nvJitLinkComplete_12_4",
    }}, "error": None}
    assert esm.classify_verdict(tr, ["model_path"]) == "RED"
