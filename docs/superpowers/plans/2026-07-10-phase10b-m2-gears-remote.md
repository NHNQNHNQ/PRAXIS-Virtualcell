# P10.B M2 基因枢纽 GEARS 远端 .53 真实接入实现 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: 用 superpowers:subagent-driven-development 逐 task 执行(每 task fresh implementer[sonnet] + spec 合规审 + 代码质量审两审)。**例外:.53 SSH 验证任务(Task 5)由控制器亲自执行,不派 subagent 跑远端。** 步骤用 checkbox 跟踪。

**Goal:** 让 genetic_hub 的 human gene→expression 请求在 .53(GPU+torch+GEARS_CKPT)上走**真实 GEARS**(产 GEARS-内部 delta=扰动−对照,明标非 donor 可比),Mac/无 ckpt 时 **fail-closed 回退现有 mock**(本地 OFFLINE 字节等价完全不变),达 M2 真实接入。

**Architecture:** env(GEARS_CKPT)门控的真实 CaseRunner(扩 B1-B3 的 `REAL_ENGINES + CaseRunner` 分诊模式,新增 ckpt-aware 维度)。`gears_available()` 门控 → ModelApplicability 分诊(Mac→mock、.53→CaseRunner)→ `dispatch_runner` 的 donor_predictor 分支 → GEARS runner(`predictors/ml/gears_case.py`,复用 GearsWrapper 新增的 `run_delta`)产 7 部分 CaseReport(raw_output 判别键 `gears_delta` + 诚实标注)→ `map_case_delta` 映射。**不碰 reliability/critic/route()/REAL_ENGINES 本体/registry status;不破坏 GearsWrapper 现有 run_prediction 契约。**

**Tech Stack:** Python;既有 CaseReport/CaseRunnerPredictorAgent/case_dispatch/ModelApplicability/route_table;GearsWrapper(model_zoo);pytest(Mac mock/结构层 + `pytest.mark.remote` .53 真实);GEARS(torch GNN,.53 only)。

---

## 权威依据(spec)与设计基线
- spec:`docs/superpowers/specs/2026-07-10-phase10b-m2-gears-remote-design.md`(commit b745b15,用户已批准)。4 项决策:A env 门控 CaseRunner / 只接 GEARS / 含 .53 SSH 验证 / Option B GEARS 自算 delta(扰动−对照非 donor 可比明标)。
- **勘察坐实**(写 plan 前已核对):
  - `dispatch_runner(engine, raw_req)` 返回 runner callable `(raw_req)→(CaseReport, RouteDecision)`;`map_case_delta(engine, report)` 读 `report.raw_output` 判别键。末尾 `raise UnsupportedEngine`。
  - `REAL_ENGINES = {"gem_fba","pathway_scoring","embedding","state_scoring"}`(donor_predictor 不在内)。
  - ModelApplicability:`if engine in REAL_ENGINES:` → `applicable=["CaseRunner"]`;否则 mock 枚举(_CANDIDATES=MockLinear/MockCPA/MockGEARS)。
  - CaseReport 7 部分(`agents/case_report.py`):case_id/structured_input/object_normalization/models_tools_selected/raw_output/baseline_comparison/reliability_decision/provenance_boundary,全非空(validate_case_report)。范例 `gem_model.py:run_growth_case`。
  - GearsWrapper(`model_zoo/wrappers/gears_wrapper.py`):`run_prediction(model_input["targets"])` lazy import torch+gears,返回绝对表达(既有契约 + test_public_models_remote.py::test_gears_wrapper_real_inference_structure,**不破坏**);`declare_scope`=human/genetic_hub/perturbation_response/gene+gene_combination;基因须∈g.pert_list(9853)。
  - 远端测试惯例:`test_public_models_remote.py` `pytestmark=pytest.mark.remote`(conftest 检测无 torch→Mac skip);ckpt 从 `os.environ["GEARS_CKPT"]` 取。
  - .53 就绪(实测):ssh 免密;conda base `/home/zkyd/miniconda3` env `virtualcell`(torch+gears 装好);ckpt `/home/zkyd/data1/mzy/gears_ckpt/norman_2019/{model.pt,config.pkl}`;data `/home/zkyd/data1/mzy/gears_data/norman_donor2`;repo `/home/zkyd/data1/mzy/PRAXIS-virtualcell`;非交互 shell GEARS_CKPT 未设(运行时显式 export)。

## Mac 可测 vs .53 验证(本单元与 B1-B4 的关键不同)
GEARS 需 GPU+torch,**Mac 不可用**。故:
- **Mac 可完整测**:`gears_available()`(monkeypatch)、ModelApplicability ckpt-aware 分诊、dispatch_runner donor_predictor 守卫、map_case_delta(手搓 CaseReport)、runner 在无 torch 时 fail-closed、全量 mock 路径字节等价。
- **仅 .53 可测(Task 5 控制器 SSH)**:GEARS 真实 delta 数值、run_delta 的 GEARS 控制态 API、端到端 remote 测试。
- **GEARS 数值非确定性**(no_fixed_seed)→ .53 测试只断言**结构 + 诚实标注 + delta 类型/非 mock**,不作字节等价断言(spec §六 确定性红线细化)。

**测试口径(铁律)**:Mac 全量永远 `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider`(GEARS remote 测试 Mac 自动 skip);.53 `... -m remote`。绝不裸跑 pytest。**测试新增 import 一律放文件顶部(防 E402)。**

## File Structure
- **Modify** `praxis_virtualcell/predictors/case_dispatch.py`:新增 `gears_available()` + dispatch_runner donor_predictor 分支 + map_case_delta donor_predictor 分支。
- **Modify** `praxis_virtualcell/agents/model_applicability.py`:分诊加 `engine=="donor_predictor" and gears_available()` → CaseRunner。
- **Modify** `praxis_virtualcell/model_zoo/wrappers/gears_wrapper.py`:新增 `run_delta(model_input)` 方法(不动 run_prediction)。
- **Create** `praxis_virtualcell/predictors/ml/gears_case.py`:`run_gears_case(raw_req)→(CaseReport, RouteDecision)`。
- **Test(扩)** `praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py`:M2 段(gears_available/分诊/dispatch 守卫/map/fail-closed,Mac 层)。
- **Test(新)** `praxis_virtualcell/tests/test_public_models_remote.py`:追加 M2 端到端 remote 测试(`pytest.mark.remote`,.53 跑)。

---

## Task 1:`gears_available()` ckpt 门控 helper

**Files:** Modify `praxis_virtualcell/predictors/case_dispatch.py`;Test 追加 `test_t10_2_module_contracts.py` M2 段。

- [ ] **Step 1:写失败测试**(追加;import `from praxis_virtualcell.predictors import case_dispatch as CD` 放文件顶部 import 块)

```python
# ==================== P10.B M2:GEARS 远端 .53 真实接入 ====================
def test_m2_gears_available_false_without_ckpt(monkeypatch):
    monkeypatch.delenv("GEARS_CKPT", raising=False)
    assert CD.gears_available() is False


def test_m2_gears_available_false_when_gears_not_importable(monkeypatch):
    monkeypatch.setenv("GEARS_CKPT", "/fake/ckpt")
    monkeypatch.setattr(CD, "_gears_importable", lambda: False)
    assert CD.gears_available() is False


def test_m2_gears_available_true_when_ckpt_and_importable(monkeypatch):
    monkeypatch.setenv("GEARS_CKPT", "/fake/ckpt")
    monkeypatch.setattr(CD, "_gears_importable", lambda: True)
    assert CD.gears_available() is True
```

- [ ] **Step 2:运行确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k m2_gears_available -p no:cacheprovider`
Expected: FAIL(`AttributeError: ... gears_available`)。

- [ ] **Step 3:实现**(加到 `case_dispatch.py`,`REAL_ENGINES` 定义之后)

```python
import os


def _gears_importable() -> bool:
    """torch + gears 是否可 import(轻量探测,不载 ckpt/不跑推理)。Mac 无 torch → False。"""
    import importlib.util
    return (importlib.util.find_spec("torch") is not None
            and importlib.util.find_spec("gears") is not None)


def gears_available() -> bool:
    """donor_predictor 是否可走真实 GEARS:GEARS_CKPT 环境变量非空 且 torch+gears 可 import。
    确定性、无副作用。Mac(无 torch)恒 False → donor_predictor 落回 mock;.53(ckpt+torch)→ True。"""
    return bool(os.environ.get("GEARS_CKPT")) and _gears_importable()
```

- [ ] **Step 4:运行确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k m2_gears_available -p no:cacheprovider`
Expected: PASS(3 passed)。

- [ ] **Step 5:ruff + commit**

Run: `.venv/bin/ruff check praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py`
```bash
git add praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "$(cat <<'EOF'
feat(phase10b-m2): Task 1 gears_available() ckpt 门控(GEARS_CKPT+torch/gears 可 import;Mac 恒 False)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2:ModelApplicability ckpt-aware 分诊

**Files:** Modify `praxis_virtualcell/agents/model_applicability.py`;Test 追加 M2 段。

- [ ] **Step 1:写失败测试**(追加;helper 复用既有 `ModelApplicabilityAgent`;import 放顶部)

```python
def _m2_applicable(req, brain_context=None, monkeypatch=None, gears=False):
    """跑 ModelApplicabilityAgent,返回 applicable 列表。gears=是否 monkeypatch gears_available。"""
    from praxis_virtualcell.agents import model_applicability as MA
    if monkeypatch is not None:
        monkeypatch.setattr(MA, "gears_available", lambda: gears, raising=False)
    bus = MessageBus()
    bc = brain_context or {"model_applicability": {}, "object_vocabulary": {"genes": []}}
    MA.ModelApplicabilityAgent().handle(AgentMessage(
        message_id="m1", sender="s", receiver="ModelApplicability",
        message_type="applicability", payload={"request": req, "brain_context": bc},
        timestamp="t1"), bus)
    return bus.latest("applicability_decided").payload["applicable"]


_M2_REQ = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}


def test_m2_donor_predictor_mac_falls_back_to_mock(monkeypatch):
    # Mac(gears_available False):donor_predictor → mock 枚举,不进 CaseRunner
    app = _m2_applicable(dict(_M2_REQ), monkeypatch=monkeypatch, gears=False)
    assert app != ["CaseRunner"]                       # 走 mock 分支(具体 mock 名由 brain_context 决定)
    assert "CaseRunner" not in app


def test_m2_donor_predictor_gated_routes_to_case_runner(monkeypatch):
    # .53 模拟(gears_available True):donor_predictor → CaseRunner 单一候选
    app = _m2_applicable(dict(_M2_REQ), monkeypatch=monkeypatch, gears=True)
    assert app == ["CaseRunner"]
```

（注:`_m2_applicable` 的 brain_context 需含 human MockLinear/CPA/GEARS 的 model_applicability 才能让 mock 分支产出非空 applicable;若空 brain_context 使 mock 全 reject 也可——断言只要求"非 CaseRunner"。实现 subagent 按实际 brain_context 结构调 helper 使 gears=False 分支真实反映 mock 行为,不为凑绿伪造。)

- [ ] **Step 2:运行确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "m2_donor_predictor" -p no:cacheprovider`
Expected: FAIL(gated 分支未实现,gears=True 时仍走 mock)。

- [ ] **Step 3:实现**(改 `model_applicability.py`)

顶部 import 区把
```python
from praxis_virtualcell.predictors.case_dispatch import REAL_ENGINES
```
改为
```python
from praxis_virtualcell.predictors.case_dispatch import REAL_ENGINES, gears_available
```
把分诊判断
```python
        if engine in REAL_ENGINES:
```
改为
```python
        # donor_predictor 经 ckpt 门控:.53(GEARS_CKPT+torch)→ 真实 CaseRunner;Mac→落回 mock 枚举。
        # REAL_ENGINES 本体不改(donor_predictor 不进 REAL_ENGINES,避免 Mac 无 GEARS 时误判 abstain)。
        if engine in REAL_ENGINES or (engine == "donor_predictor" and gears_available()):
```
（其余不动——`real_engine` note 记 engine 名即可;donor_predictor 时 real_engine="donor_predictor"。）

- [ ] **Step 4:运行确认通过 + Mac 分诊回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "m2_donor_predictor" praxis_virtualcell/tests/test_model_applicability*.py -p no:cacheprovider`
Expected: PASS(gated=CaseRunner、Mac=mock;既有 model_applicability 测试全绿——donor_predictor 现有行为在 gears_available False 时不变)。**若既有测试 FAIL:停止 BLOCKED**(Mac 分诊行为被改,违背"字节等价不变")。

- [ ] **Step 5:ruff + commit**

```bash
.venv/bin/ruff check praxis_virtualcell/agents/model_applicability.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git add praxis_virtualcell/agents/model_applicability.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "$(cat <<'EOF'
feat(phase10b-m2): Task 2 ModelApplicability ckpt-aware 分诊(donor_predictor+gears_available→CaseRunner,Mac 回 mock 不变)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3:GEARS runner + dispatch/map 分支 + GearsWrapper.run_delta

**Files:** Create `praxis_virtualcell/predictors/ml/gears_case.py`;Modify `case_dispatch.py`(dispatch+map 分支)、`gears_wrapper.py`(run_delta);Test 追加 M2 段。

- [ ] **Step 1:写失败测试**(Mac 层:dispatch 守卫 + map + runner fail-closed;追加)

```python
from praxis_virtualcell.core.exceptions import UnsupportedEngine as _UnsupportedEngine
from praxis_virtualcell.agents.case_report import CaseReport as _CaseReport


def test_m2_dispatch_donor_predictor_human_gene_returns_runner():
    from praxis_virtualcell.predictors.ml.gears_case import run_gears_case
    raw = {"species": "human", "perturbation_object": "gene",
           "target_output": "expression", "perturbation_targets": ["AHR"]}
    assert CD.dispatch_runner("donor_predictor", raw) is run_gears_case


def test_m2_dispatch_donor_predictor_non_human_unsupported():
    raw = {"species": "mouse", "perturbation_object": "gene",
           "target_output": "expression", "perturbation_targets": ["Ahr"]}
    with pytest.raises(_UnsupportedEngine):
        CD.dispatch_runner("donor_predictor", raw)


def test_m2_dispatch_donor_predictor_non_gene_unsupported():
    raw = {"species": "human", "perturbation_object": "drug",
           "target_output": "expression", "perturbation_targets": ["vorinostat"]}
    with pytest.raises(_UnsupportedEngine):
        CD.dispatch_runner("donor_predictor", raw)


def test_m2_map_case_delta_gears_reads_gears_delta():
    # 手搓一个带 gears_delta 判别键的 CaseReport,验证 map 读它(不需 torch)
    rep = _CaseReport(case_id="c", structured_input={"x": 1},
                      object_normalization={"species": "human"},
                      models_tools_selected={"engine": "donor_predictor"},
                      raw_output={"gears_delta": [0.12, -0.34], "targets": ["AHR"],
                                  "value_type": "gears_internal_delta"},
                      baseline_comparison={"baseline": "gears ctrl"},
                      reliability_decision={"disposition": "accept", "caution_flags": [], "data_gated": False},
                      provenance_boundary={"rules_hit": ["r"], "boundary": "b"})
    assert CD.map_case_delta("donor_predictor", rep) == [0.12, -0.34]


def test_m2_gears_runner_fail_closed_without_torch():
    # Mac 无 torch:run_gears_case 内 GearsWrapper.run_delta lazy import torch → 抛(fail-closed,不静默 mock)
    from praxis_virtualcell.predictors.ml.gears_case import run_gears_case
    raw = {"species": "human", "perturbation_object": "gene",
           "target_output": "expression", "perturbation_targets": ["AHR"]}
    with pytest.raises((ModuleNotFoundError, ImportError, RuntimeError)):
        run_gears_case(raw)
```

- [ ] **Step 2:运行确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "m2_dispatch or m2_map_case_delta_gears or m2_gears_runner_fail" -p no:cacheprovider`
Expected: FAIL(`ModuleNotFoundError: ... gears_case` / dispatch 无 donor_predictor 分支)。

- [ ] **Step 3a:GearsWrapper 新增 `run_delta`**(`gears_wrapper.py`,不动 run_prediction)

在 `GearsWrapper` 类内、`run_prediction` 之后新增:
```python
    def run_delta(self, model_input: dict) -> dict:
        """P10.B M2:GEARS-内部 delta = 扰动态 − 对照态(均 mean-over-cells)。真 delta 且类型与
        模块一致,但属 GEARS-内部、**非 donor 可比**(明标)。绝不冒充 donor delta、绝不填绝对表达进 delta 槽。
        缺 torch/GEARS/ckpt → 抛 → fail-closed(不静默 mock)。真跑是 .53 的事(Task 5 gated),
        对照态 API 以 .53 实测确认:GEARS ctrl 预测 vs PertData ctrl 均值。"""
        import os

        import torch  # noqa: F401 — 缺 torch 即抛(fail-closed 触发点)
        import pandas as _pd
        _pd.Series.nonzero = lambda self: self.to_numpy().nonzero()
        from gears import GEARS, PertData

        if not self._ckpt_stem:
            raise RuntimeError("gears ckpt 未声明;fail-closed")
        targets = list(model_input.get("targets") or [])
        if not targets:
            raise ValueError("gears run_delta 需 model_input['targets'];fail-closed")

        data_root = os.environ.get("GEARS_DATA_ROOT", self._GEARS_DATA_ROOT)
        data_name = os.environ.get("GEARS_DATA_NAME", self._GEARS_DATA_NAME)
        pert_data = PertData(data_root)
        pert_data.load(data_path=os.path.join(data_root, data_name))
        pert_data.prepare_split(split="simulation", seed=1)
        pert_data.get_dataloader(batch_size=32, test_batch_size=64)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        g = GEARS(pert_data, device=device)
        g.load_pretrained(self._ckpt_stem)

        for gene in targets:
            if gene not in g.pert_list:
                raise ValueError(f"{gene} 不在 GEARS.pert_list;fail-closed")

        # 扰动态:GEARS predict([[gene]]) mean-over-cells 绝对表达
        perturbed = g.predict([targets])["_".join(targets)]
        # 对照态:PertData ctrl 细胞的 mean 表达(与 perturbed 同基因序)。
        #   .53 实测确认:pert_data.ctrl_adata / adata[obs.condition=='ctrl'] 的 X.mean(0);
        #   若 GEARS 有原生 ctrl 预测 API 亦可,以 .53 当场确认为准(Task 5)。
        import numpy as _np
        ctrl_adata = pert_data.adata[pert_data.adata.obs["condition"] == "ctrl"]
        control = _np.asarray(ctrl_adata.X.mean(axis=0)).ravel()
        delta = (_np.asarray(perturbed).ravel() - control)

        return {
            "prediction": {
                "delta": [round(float(x), 4) for x in delta],
                "n_genes": int(len(delta)),
                "condition": "_".join(targets),
                "value_type": "gears_internal_delta",       # 明标:GEARS 自算 delta,非 donor 可比
                "not_comparable_to_donor_base": True,
                "non_deterministic": True,                   # GEARS no_fixed_seed
            },
            "uncertainty": self.estimate_uncertainty(model_input, None),
        }
```
（对照态提取的 `pert_data.adata.obs["condition"]=="ctrl"` 是 norman PertData 惯例;**Task 5 在 .53 当场确认真实字段/API,若不符按实调**——这是 spec §四.3 明示的"对照 API 待 .53 坐实",本单元含 .53 验证。）

- [ ] **Step 3b:GEARS runner `gears_case.py`**(新建)

```python
"""P10.B M2:GEARS 真实预测 → offline 主链 CaseReport adapter(.53 gated)。

复用 GearsWrapper.run_delta(GEARS-内部 delta=扰动−对照),产 7 部分 CaseReport。诚实:
delta 明标 gears_internal / not_comparable_to_donor_base / non_deterministic,不冒充 donor delta;
基因不在 GEARS vocab / 缺 torch → fail-closed(GearsWrapper 抛 → 此处不吞,由既有 handle 归 failed)。
真跑是 .53 的事(Mac 无 torch → GearsWrapper.run_delta 即抛)。
"""
from __future__ import annotations

import os

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request


def run_gears_case(raw_req: dict):
    """human gene→expression GEARS case → (CaseReport, RouteDecision)。GEARS-内部 delta,非 donor 可比。"""
    from praxis_virtualcell.model_zoo.wrappers.gears_wrapper import GearsWrapper

    norm = normalize_request(raw_req)
    dec = route(norm)
    targets = norm["perturbation_targets"]

    wrapper = GearsWrapper(ckpt_stem=os.environ.get("GEARS_CKPT"))
    out = wrapper.run_delta({"targets": targets})       # 缺 torch/ckpt/vocab → 抛(fail-closed)
    pred = out["prediction"]

    report = CaseReport(
        case_id=raw_req.get("case_id", "M2_gears_delta"),
        structured_input=dict(raw_req),
        object_normalization={
            "species": norm["species"], "perturbation_object": norm["perturbation_object"],
            "normalized_targets": targets, "target_output": norm["target_output"],
        },
        models_tools_selected={"engine": dec.engine, "model": "gears",
                               "method": "GEARS GNN (norman_2019)", "reason": dec.reason},
        raw_output={
            "gears_delta": pred["delta"],
            "targets": targets,
            "condition": pred["condition"],
            "value_type": pred["value_type"],                 # gears_internal_delta
            "not_comparable_to_donor_base": pred["not_comparable_to_donor_base"],
            "non_deterministic": pred["non_deterministic"],
        },
        baseline_comparison={
            "baseline": "GEARS ctrl condition (mean-over-cells)",
            "value_type": "gears_internal_delta",
            "not_comparable_to_donor_base": True,             # 与 donor base 指标/split 不同,不同表
        },
        reliability_decision={"disposition": "accept", "caution_flags": ["gears_internal_delta",
                              "not_comparable_to_donor_base", "non_deterministic"], "data_gated": False},
        provenance_boundary={
            "model": "gears", "type": "public_model", "training_data": "norman_2019 (Perturb-seq, K562)",
            "no_fixed_seed": True, "non_deterministic": True,
            "rules_hit": [dec.reason],
            "boundary": ("GEARS 真实预测(.53);delta=扰动−对照 GEARS-内部,非 donor 可比(指标/split 不同,"
                         "不同表对比);GEARS 无固定 seed,数值非确定性。"),
        },
    )
    return report, dec
```

- [x] **Step 3c:case_dispatch.py 加 dispatch + map 分支(实际实现 = Option B,见下方实现记录)**

`dispatch_runner` 末尾 `raise UnsupportedEngine` **之前**加(**Option B:守卫含 `and gears_available()`**):
```python
    elif engine == "donor_predictor":
        # M2:human gene→expression 真实 GEARS(.53 gated)。dispatch 层也校验 gears_available()
        # (Option B / defense-in-depth:GEARS 不可用即诚实 UnsupportedEngine,不声称 applicable 后失败)。
        if (species == "human" and obj in _GENE_LIKE
                and raw_req.get("target_output") == "expression" and gears_available()):
            from praxis_virtualcell.predictors.ml.gears_case import run_gears_case
            return run_gears_case
        # 非 human/非 gene/非 expression/GEARS 不可用 → 落末尾 UnsupportedEngine → 诚实 abstain/reject
```
`map_case_delta` 里 `if engine == "state_scoring":` 分支**之后**、末尾 `raise` 之前加(**防御式,对齐同函数其他分支**):
```python
    if engine == "donor_predictor":
        if "gears_delta" in raw:   # GEARS-内部 delta(已在 wrapper round 定点)
            return list(raw["gears_delta"])
        raise UnsupportedEngine(f"donor_predictor map_case_delta 未支持 raw_output 形状: {sorted(raw)}")
```

> **⚠️ 实现记录(2026-07-10 Task 3 收官,commit 88bd8df):Option B 决策来龙。**
> Task 3 实现中发现 plan 原设(dispatch donor_predictor 分支**不**含 `gears_available()`)与 B1 遗留测试 `test_case_runner_assess_applicability_reject_unsupported` 冲突——该测试**绕过 ModelApplicability 直调 CaseRunner**,原设 donor_predictor 无 runner→reject;加了 dispatch 分支后它会误判 applicable。implementer 正确报 BLOCKED 挡下。**用户拍板 Option B**:dispatch 层守卫**加 `and gears_available()`**(defense-in-depth 双门控:ModelApplicability 已门控,dispatch 再门控一次;GEARS 不可用即诚实 `UnsupportedEngine`,不声称 applicable 后失败)。配套:①旧 B1 测试改 `monkeypatch.setattr(CD, "gears_available", lambda: False)` 显式锁,保持 reject 语义、使 env 无关;②M2 dispatch 测试相应 `monkeypatch` gears_available(True 测返回 runner / False 测 raise),且 non_human/non_gene 测试用 `gears=True` 隔离验证是 species/obj 守卫而非门控本身拒绝。
> **代码质量审两处 fix(amend 到本 commit)**:①`test_m2_gears_runner_fail_closed_without_torch` 加 `@pytest.mark.skipif(_HAS_TORCH,...)` 守卫(对齐 `test_gears_wrapper.py` 既有约定,防 .53 残留 GEARS_CKPT 时误跑);②`map_case_delta` donor_predictor 分支加防御(先判 `gears_delta` 键存在、否则诊断式 `raise UnsupportedEngine`,对齐同函数惯例)。两审(spec 合规审 APPROVED + 代码质量审 CHANGES_REQUESTED→修→复审 APPROVED),全量 770/39/0。

- [ ] **Step 4:运行确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "m2_dispatch or m2_map_case_delta_gears or m2_gears_runner_fail" -p no:cacheprovider`
Expected: PASS(dispatch 守卫 + map + Mac fail-closed 全绿)。

- [ ] **Step 5:回归既有 case_dispatch/gears_wrapper 测试(GearsWrapper 契约不破)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -k "case_dispatch or gears or t10_2" -p no:cacheprovider`
Expected: 全 PASS(GEARS remote 测试仍 skip;run_prediction 契约不变)。

- [ ] **Step 6:ruff + commit**

```bash
.venv/bin/ruff check praxis_virtualcell/predictors/ml/gears_case.py praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/model_zoo/wrappers/gears_wrapper.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git add praxis_virtualcell/predictors/ml/gears_case.py praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/model_zoo/wrappers/gears_wrapper.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "$(cat <<'EOF'
feat(phase10b-m2): Task 3 GEARS runner + dispatch/map donor_predictor 分支 + GearsWrapper.run_delta(GEARS-内部 delta 扰动−对照,明标非 donor 可比)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4:Mac 全量回归字节等价 + 端到端 mock 不变

**Files:** Test 追加 M2 段(Mac 端到端 mock 不变);无源码改动。

- [ ] **Step 1:写测试**(Mac:human gene→expression 经 run_query 仍走 mock、字节等价;追加)

```python
def test_m2_mac_genetic_hub_still_mock_e2e(monkeypatch):
    # Mac(无 torch,gears_available False):human gene→expression 仍走 mock,不含 GEARS/CaseRunner
    monkeypatch.delenv("GEARS_CKPT", raising=False)
    out = run_query(dict(_M2_REQ), config=_CFG)
    used = out["structured_report"]["provenance"]["models_used"]
    assert "CaseRunner" not in used                       # 未走 GEARS 真实通道
    assert "gears" not in _json.dumps(used, default=str).lower()


def test_m2_mac_genetic_hub_deterministic_byte_equal(monkeypatch):
    monkeypatch.delenv("GEARS_CKPT", raising=False)
    outs = [run_query(dict(_M2_REQ), config=_CFG) for _ in range(3)]
    assert len({_canon(o["structured_report"]) for o in outs}) == 1
```

- [ ] **Step 2:运行 + 全量回归**

Run(定向):`PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "m2_mac" -p no:cacheprovider` → PASS。
Run(全量):`PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider` → **相较 B4 基线 758/39/0 净增 M2 Mac 测(约 +12),0 failed**;GEARS remote 测试仍 skip(skip 数不变或按 remote 测试增加)。**Mac genetic_hub mock 行为字节不变。**

- [ ] **Step 3:ruff + commit**

```bash
.venv/bin/ruff check praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git add praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "$(cat <<'EOF'
test(phase10b-m2): Task 4 Mac 端到端 mock 不变 + 字节等价(GEARS 路径 Mac 不触发,OFFLINE 确定性保留)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5(.53 验证,**控制器亲自执行,不派 subagent**)

**Files:** Test 追加 `test_public_models_remote.py`(remote e2e);控制器 SSH .53 验证。

- [ ] **Step 1:控制器写 remote 端到端测试**(追加到 `test_public_models_remote.py`,`pytest.mark.remote`)

```python
def test_m2_gears_case_real_delta_e2e():
    """.53:human gene→expression 经 run_gears_case → GEARS-内部 delta(扰动−对照,非 mock 0.3、非绝对表达)。
    GEARS 非确定性 → 只验结构 + 诚实标注 + delta 类型,不作字节等价断言。"""
    from praxis_virtualcell.predictors.ml.gears_case import run_gears_case
    raw = {"species": "human", "perturbation_object": "gene",
           "target_output": "expression", "perturbation_targets": ["AHR"]}   # AHR∈norman vocab(如非则换 vocab 内基因)
    report, dec = run_gears_case(raw)
    assert dec.engine == "donor_predictor"
    ro = report.raw_output
    assert ro["value_type"] == "gears_internal_delta"
    assert ro["not_comparable_to_donor_base"] is True
    assert ro["non_deterministic"] is True
    assert isinstance(ro["gears_delta"], list) and len(ro["gears_delta"]) > 0
    # 非 mock 铁证:delta 非全 0.3(mock ensemble 值),且有非零分量
    assert any(abs(x) > 1e-9 for x in ro["gears_delta"])
    assert ro["gears_delta"] != [0.3] * len(ro["gears_delta"])
    assert report.reliability_decision["disposition"] == "accept"
    assert "not_comparable_to_donor_base" in report.reliability_decision["caution_flags"]
```

- [ ] **Step 2:控制器 SSH .53 跑 remote 测试**(亲自执行)

```bash
ssh zkyd@10.102.106.53 'bash -lc "
  source /home/zkyd/miniconda3/etc/profile.d/conda.sh && conda activate virtualcell &&
  cd /home/zkyd/data1/mzy/PRAXIS-virtualcell && git fetch && git checkout <M2 分支/commit> &&
  export GEARS_CKPT=/home/zkyd/data1/mzy/gears_ckpt/norman_2019 &&
  export GEARS_DATA_ROOT=/home/zkyd/data1/mzy/gears_data GEARS_DATA_NAME=norman_donor2 &&
  PYTHONPATH=\$PWD python -m pytest praxis_virtualcell/tests -m remote -p no:cacheprovider -q
"'
```
（**注**:.53 需先能 git 拉到本地 M2 分支的 commit——若 .53 走 origin,可能需先 push 或用 patch 传;本单元红线"不 push",故用 `git format-patch` / rsync 传 diff 或在 .53 直接 apply。控制器执行时按实处理,**不因验证而 push origin**。若对照态字段 API 与 Step 3a 假设不符,当场按实调 GearsWrapper.run_delta 并回 Mac 复测 fail-closed 不破。）
Expected:新增 `test_m2_gears_case_real_delta_e2e` + 既有 2 条 remote 测试 **passed**。

- [ ] **Step 3:控制器独立核实**(一次性脚本,亲验非 mock)

在 .53 上跑一次性脚本:`run_gears_case(AHR)` 打印 delta 前 5 分量 + value_type + reliability caution_flags;人工确认 delta 是 GEARS 真值(非 0.3、非绝对表达量级)、诚实标注齐。

- [ ] **Step 4:commit remote 测试 + 报告控制器**

```bash
git add praxis_virtualcell/tests/test_public_models_remote.py
git commit -m "$(cat <<'EOF'
test(phase10b-m2): Task 5 .53 GEARS 端到端 remote 测试(真实 GEARS-内部 delta,非 mock;控制器 SSH 亲验)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
输出:.53 remote 测试 passed 截图/日志、独立核实的 delta 样本、Mac 全量回归数、各 commit hash、`git status` 干净、确认 core/根 tests/reliability/critic/REAL_ENGINES 本体/registry status 零改。

---

## Self-Review(对照 spec)

- **spec §一 4 决策**:A env 门控(Task 1-2)✅ / 只接 GEARS(全程仅 GEARS)✅ / 含 .53 验证(Task 5 控制器 SSH)✅ / Option B GEARS 自算 delta 扰动−对照明标(Task 3 run_delta + gears_case)✅。
- **spec §四 架构**:gears_available ckpt 门控(T1)、ckpt-aware 分诊(T2)、dispatch donor_predictor 分支 + GEARS runner + run_delta + map 分支(T3)✅。
- **spec §六 确定性红线细化**:Mac mock 字节等价(T4)+ GEARS 非确定性只验结构不字节等价(T5)✅。
- **spec §七 .53 验证流程**:Task 5 SSH+conda+env+pytest -m remote,对照 API 当场确认 ✅。
- **spec §九 红线**:不碰 reliability/critic/route/REAL_ENGINES 本体/registry status(各 task commit 范围受限);GearsWrapper run_prediction 契约不破(只加 run_delta,T3 Step5 回归);GEARS delta 明标非 donor 可比不张冠李戴(T3 raw_output/reliability caution/provenance);Mac fail-closed 回 mock(T2/T4);不 push(T5 用 patch/rsync 传 .53,不 push origin);trailer Opus4.8 ✅。
- **类型一致性**:`gears_available()->bool`(T1)在 T2 分诊、`run_gears_case(raw)->(CaseReport,dec)`(T3)在 dispatch/T5、`run_delta(model_input)->{"prediction":{"delta":...}}`(T3a)被 gears_case 消费、`map_case_delta("donor_predictor",report)` 读 `raw_output["gears_delta"]`(T3c 产 / map 读)一致 ✅。
- **占位符扫描**:无 TBD;唯一 .53-确认项(对照态 API)是 spec 明示的本单元含验证项,Task 3a/5 明确当场确认路径,非占位 ✅。

## 收官后控制器职责(不在 task 内)
1. **opus final review**——重点审:①GEARS delta 是否真明标非 donor 可比、无绝对表达冒充 delta;②Mac 字节等价确实不变(donor_predictor gears_available False 路径);③ckpt 门控是否有 Mac 误触发 GEARS 的缝(gears_available 双条件);④GearsWrapper run_prediction 契约确未破;⑤.53 remote 测试确证非 mock。
2. 台账 + 记忆勾账(M2 从 mock → .53 真实 GEARS-内部 delta 可运行;真实覆盖 M2/M3/M4/M7+微生物)。
3. **AskUserQuestion 问是否 FF 合并 main**(与 B4 一并或单独,由用户定)。
