# Week 4a — 远端 linear predictor 迁移 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans(本计划远端执行,inline 最稳)。Steps 用 checkbox(`- [ ]`)。

**Goal:** 在远端 GPU(zkyd@10.102.106.53,virtualcell conda 环境)把 donor 的 `linear_additive` 从 ckpt 加载、包成 praxis `predictors/ml/` 适配,复现其 Norman ΔPearson(anchor 0.5886)并证"praxis 包装预测 == donor 原预测"。

**Architecture:** torch **只在远端 `predictors/ml/`**;复用 donor `/home/zkyd/data1/mzy/Virtual cell` 的 `predictors.linear_additive` / `bench.vcbench.loader` / `coordinator.eval_agent`(sys.path 注入,不 vendor)。Mac 端 Week 2/3 的 48 测试零回归(ml 测试标 `remote`,Mac skip)。

**Tech Stack:** 远端 conda `virtualcell`(torch+lightning+numpy/scipy/pint/pyyaml/jsonschema)、6× A100、pytest。

**Spec:** [docs/superpowers/specs/2026-06-12-week4a-remote-linear-migration-design.md](../specs/2026-06-12-week4a-remote-linear-migration-design.md)

**远端约定(全计划复用)**:
- donor 根:`/home/zkyd/data1/mzy/Virtual cell`(**含空格,务必引号**)
- 远端 praxis 仓:`/home/zkyd/data1/mzy/PRAXIS-virtualcell`(Task 1 clone)
- `RUN='ssh -o BatchMode=yes zkyd@10.102.106.53'`
- 远端 conda init:`source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh`

---

## Task 1:M0 — 远端建 virtualcell 环境 + clone 仓 + recon

**Files:** 无本地代码(远端操作 + recon 记录)。

- [ ] **Step 1: 探 CUDA + donor ckpt + checkpoint API**

```bash
ssh -o BatchMode=yes zkyd@10.102.106.53 '
nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1
echo "=== norman ckpt 目录 ==="; ls "/home/zkyd/data1/mzy/Virtual cell/runs"/full_bench_*/checkpoints/norman_2019/linear_additive.* 2>/dev/null
echo "=== anchor json ==="; cat "/home/zkyd/data1/mzy/Virtual cell/runs/full_bench_20260521_060815/checkpoints/norman_2019/linear_additive.json" 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(\"kwargs\",d[\"kwargs\"]);print(\"anchor delta_pearson\",d[\"meta\"].get(\"delta_pearson\"))"
echo "=== checkpoint.py load API ==="; grep -nE "def (save|load)_predictor|torch.save|torch.load" "/home/zkyd/data1/mzy/Virtual cell/scripts/checkpoint.py" | head
echo "=== full_bench 默认 eval 设置(max_perts/max_cells/split)==="; grep -nE "add_argument.*(max-perts|max-cells|split)" "/home/zkyd/data1/mzy/Virtual cell/scripts/run_full_bench.py" | head
'
```
记录:driver 版本、ckpt 绝对路径、anchor `delta_pearson`(记为 `S0`)、`load_predictor` 是否存在、full_bench eval 默认参数。**Gate**:拿到 ckpt 路径 + S0。

- [ ] **Step 2: 建 virtualcell 环境**

```bash
ssh -o BatchMode=yes zkyd@10.102.106.53 '
source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh
conda create -n virtualcell python=3.11 -y
conda activate virtualcell
pip install -q "torch>=2.2" lightning numpy scipy pint pyyaml jsonschema
python -c "import torch,lightning,scipy,pint; print(\"torch\",torch.__version__,\"cuda\",torch.cuda.is_available())"
'
```
**Gate**:打印 `cuda True`。若 False/装不上 → 看 Step 1 driver 选对应 cuXXX 的 `--index-url https://download.pytorch.org/whl/cuXXX`,或用 `/home/zkyd/data1/mzy/torch_gpu_pkgs` 缓存;仍不行**停下报告**(P2-B:不硬凑)。

- [ ] **Step 3: clone praxis 仓到远端**

```bash
ssh -o BatchMode=yes zkyd@10.102.106.53 '
cd /home/zkyd/data1/mzy
git clone git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git PRAXIS-virtualcell 2>&1 | tail -3 || (cd PRAXIS-virtualcell && git pull)
ls PRAXIS-virtualcell/praxis_virtualcell/predictors
'
```
**Gate**:远端有 `PRAXIS-virtualcell/praxis_virtualcell/`。(后续每次改代码:Mac commit+push → 远端 `git pull`。)

- [ ] **Step 4: 记录** 把 Step 1-3 结果写 `docs/findings/finding_w4a_env.md`(driver/torch 版本/ckpt 路径/S0/eval 设置)。**commit(Mac)**:`git add docs/findings/finding_w4a_env.md && git commit -m "docs(w4a): remote env + ckpt recon"`。

---

## Task 2:M1 — 复现 donor linear Norman(锚定 S0)

**Files:** Create `praxis_virtualcell/benchmarks/__init__.py`、`praxis_virtualcell/benchmarks/_anchor_donor_linear.py`(远端跑的独立脚本,不进 Mac 测试)

- [ ] **Step 1: 写远端锚定脚本** `praxis_virtualcell/benchmarks/__init__.py`(空)+ `praxis_virtualcell/benchmarks/_anchor_donor_linear.py`:

```python
"""M1:远端加载 donor linear ckpt,EvalAgent 在 Norman test 上算 ΔPearson,对照 ckpt 记录的 S0。
仅远端 virtualcell 环境跑(import torch + donor)。用法:python -m praxis_virtualcell.benchmarks._anchor_donor_linear <ckpt_stem>"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import torch

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


def main(ckpt_stem: str) -> None:
    cfg = json.loads(Path(ckpt_stem + ".json").read_text())
    from bench.vcbench.loader import load_vcbench_split
    from coordinator.eval_agent import EvalAgent
    from predictors.linear_additive import LinearAdditivePredictor

    model = LinearAdditivePredictor(**cfg["kwargs"])
    state = torch.load(ckpt_stem + ".pt", map_location="cpu")
    state = state.get("state_dict", state) if isinstance(state, dict) and "state_dict" in state else state
    model.load_state_dict(state)

    ds = load_vcbench_split("norman_2019", "test", rng_seed=1)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    rep = EvalAgent(batch_size=64, device=dev).evaluate(model, ds)
    print("S0_recorded =", cfg["meta"].get("delta_pearson"))
    print("S_eval delta_pearson =", rep.metrics.delta_pearson)
    print("cosine =", rep.metrics.cosine, "n =", rep.n_samples)


if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 2: commit + push(Mac)** `git add praxis_virtualcell/benchmarks && git commit -m "feat(w4a): donor linear anchor script (remote)" && git push -q origin main`

- [ ] **Step 3: 远端跑锚定**(ckpt_stem 用 Task1 确认的路径)

```bash
ssh -o BatchMode=yes zkyd@10.102.106.53 '
source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh && conda activate virtualcell
cd /home/zkyd/data1/mzy/PRAXIS-virtualcell && git pull -q
python -m praxis_virtualcell.benchmarks._anchor_donor_linear "/home/zkyd/data1/mzy/Virtual cell/runs/full_bench_20260521_060815/checkpoints/norman_2019/linear_additive"
'
```
**Gate**:`S_eval delta_pearson` 与 `S0_recorded` 接近(同 ckpt+数据;若 split/采样默认不同会略偏,记差异)。把数字写 `docs/findings/finding_w4a_norman_anchor.md`(committed)。记 `S_anchor = S_eval`(M2 对照真值)。

---

## Task 3:donor_bridge(rich↔torch 适配基础)

**Files:** Create `praxis_virtualcell/predictors/ml/__init__.py`、`praxis_virtualcell/predictors/ml/donor_bridge.py`、`praxis_virtualcell/tests/test_ml_donor_bridge.py`

- [ ] **Step 1: 写远端测试** `tests/test_ml_donor_bridge.py`

```python
import os

import pytest

pytestmark = pytest.mark.remote


def test_build_linear_from_ckpt_shapes():
    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt
    stem = os.environ["W4A_LINEAR_CKPT"]  # 远端跑时由 env 给 ckpt stem
    model, cfg = build_predictor_from_ckpt(stem)
    assert cfg["class_name"] == "LinearAdditivePredictor"
    assert model.pert_dim == cfg["kwargs"]["pert_dim"]
    assert model.n_genes == cfg["kwargs"]["n_genes"]


def test_load_norman_has_genes_and_pertdim():
    from praxis_virtualcell.predictors.ml.donor_bridge import load_norman
    ds = load_norman(split="test")
    assert ds.n_genes > 0 and ds.pert_dim > 0
```

- [ ] **Step 2: 实现** `predictors/ml/__init__.py`(空)+ `predictors/ml/donor_bridge.py`:

```python
"""rich↔torch 适配基础:复用 donor 代码(sys.path 注入)加载 predictor + Norman。
仅远端 virtualcell 环境 import(import torch + donor)。Mac 不 import(测试标 remote)。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import torch

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)

_CLASSES: dict[str, Any] = {}


def _cls(name: str):
    if not _CLASSES:
        from predictors.linear_additive import LinearAdditivePredictor
        _CLASSES["LinearAdditivePredictor"] = LinearAdditivePredictor
    return _CLASSES[name]


def build_predictor_from_ckpt(ckpt_stem: str):
    """ckpt_stem = .../norman_2019/linear_additive(无扩展)。读 .json 重建 + load .pt。返回 (model, cfg)。"""
    cfg = json.loads(Path(ckpt_stem + ".json").read_text(encoding="utf-8"))
    model = _cls(cfg["class_name"])(**cfg["kwargs"])
    state = torch.load(ckpt_stem + ".pt", map_location="cpu")
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]
    model.load_state_dict(state)
    model.eval()
    return model, cfg


def load_norman(split: str = "test", *, max_perts: int | None = None,
                max_cells: int | None = None, seed: int = 1):
    from bench.vcbench.loader import load_vcbench_split
    kw: dict[str, Any] = {"rng_seed": seed}
    if max_perts is not None:
        kw["max_perts"] = max_perts
    if max_cells is not None:
        kw["max_cells_per_pert"] = max_cells
    return load_vcbench_split("norman_2019", split, **kw)
```

- [ ] **Step 3: commit + push(Mac)**;**远端跑测试**:

```bash
ssh ... 'source ...&& conda activate virtualcell && cd .../PRAXIS-virtualcell && git pull -q
export W4A_LINEAR_CKPT="/home/zkyd/data1/mzy/Virtual cell/runs/full_bench_20260521_060815/checkpoints/norman_2019/linear_additive"
python -m pytest praxis_virtualcell/tests/test_ml_donor_bridge.py -q -p no:cacheprovider'
```
**Gate**:2 passed(远端)。

---

## Task 4:LinearAdditivePredictorAgent(praxis 包装 + 等价证明)

**Files:** Create `praxis_virtualcell/predictors/ml/linear_additive_agent.py`、`praxis_virtualcell/tests/test_ml_linear_agent.py`

- [ ] **Step 1: 写远端测试** `tests/test_ml_linear_agent.py`

```python
import os

import pytest

pytestmark = pytest.mark.remote


def test_agent_prediction_equals_donor():
    import torch

    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt, load_norman
    from praxis_virtualcell.predictors.ml.linear_additive_agent import LinearAdditivePredictorAgent

    model, _ = build_predictor_from_ckpt(os.environ["W4A_LINEAR_CKPT"])
    ds = load_norman(split="test", max_perts=3, max_cells=8)
    item = ds[0]  # 含 pert_emb / control / perturbation
    from predictors.base import Context, Perturbation  # donor
    name = item["perturbation"]
    kind = "control" if name == "control" else ("gene_combo" if "+" in name else "gene_ko")
    targets = () if kind == "control" else (tuple(name.split("+")) if kind == "gene_combo" else (name,))
    ctx = Context(control=item["control"])
    pert = Perturbation(kind=kind, targets=targets, meta={"pert_emb": item["pert_emb"]})
    donor_mean = model.predict(ctx, pert).mean

    agent = LinearAdditivePredictorAgent(model)
    agent_mean = agent.predict_tensor(item["control"], item["pert_emb"], kind=kind, targets=targets)
    assert torch.allclose(agent_mean, donor_mean, atol=1e-6), "包装后预测应与 donor 逐元素一致"
```

- [ ] **Step 2: 实现** `predictors/ml/linear_additive_agent.py`:

```python
"""把 donor LinearAdditivePredictor 包成 praxis predictor-agent(rich↔torch 适配)。
predict_tensor:给 control+pert_emb,经 donor Context/Perturbation 调 donor.predict,返回 mean。
（bus 级 PredictorAgent 集成在 Coordinator 迁移时接;本期只证预测等价 + 可在 EvalAgent 复用。）"""
from __future__ import annotations

import sys

import torch

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


class LinearAdditivePredictorAgent:
    name = "MLLinearAdditive"

    def __init__(self, donor_model) -> None:
        self.model = donor_model.eval()

    def predict_tensor(self, control: torch.Tensor, pert_emb: torch.Tensor, *,
                       kind: str = "gene_ko", targets: tuple = ()) -> torch.Tensor:
        from predictors.base import Context, Perturbation
        ctx = Context(control=control)
        pert = Perturbation(kind=kind, targets=targets, meta={"pert_emb": pert_emb})
        return self.model.predict(ctx, pert).mean

    def as_donor_predictor(self):
        """返回底层 donor Predictor,供 EvalAgent.evaluate 复用(Task 5)。"""
        return self.model
```

- [ ] **Step 3: commit+push;远端跑测试**(同 Task 3 SSH 模板,跑 `test_ml_linear_agent.py`)。**Gate**:1 passed —— 包装预测与 donor 逐元素一致。

---

## Task 5:norman_eval — praxis 复用 EvalAgent 复现分数

**Files:** Create `praxis_virtualcell/benchmarks/norman_eval.py`、`praxis_virtualcell/tests/test_ml_norman_score.py`

- [ ] **Step 1: 写远端测试** `tests/test_ml_norman_score.py`

```python
import os

import pytest

pytestmark = pytest.mark.remote


def test_praxis_linear_norman_matches_donor():
    from praxis_virtualcell.benchmarks.norman_eval import score_linear_ckpt
    stem = os.environ["W4A_LINEAR_CKPT"]
    s_praxis = score_linear_ckpt(stem, split="test")
    s_anchor = float(os.environ["W4A_ANCHOR"])  # Task 2 记录的 S_anchor
    # 同 ckpt+loader+EvalAgent → 应逐位一致(浮点容差)
    assert abs(s_praxis["delta_pearson"] - s_anchor) < 1e-4, (s_praxis, s_anchor)
    assert s_praxis["n"] > 0
```

- [ ] **Step 2: 实现** `benchmarks/norman_eval.py`:

```python
"""praxis 侧:经 ml 适配加载 donor linear,复用 donor EvalAgent 在 Norman 上算分。
证迁移到 praxis_virtualcell 后分数与 donor 一致(同 ckpt/loader/metric)。仅远端跑。"""
from __future__ import annotations

import sys
from typing import Any

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


def score_linear_ckpt(ckpt_stem: str, *, split: str = "test", seed: int = 1) -> dict[str, Any]:
    import torch

    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt, load_norman
    from coordinator.eval_agent import EvalAgent

    model, _ = build_predictor_from_ckpt(ckpt_stem)
    ds = load_norman(split=split, seed=seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    rep = EvalAgent(batch_size=64, device=dev).evaluate(model, ds)
    return {"delta_pearson": rep.metrics.delta_pearson, "cosine": rep.metrics.cosine,
            "n": rep.n_samples}
```

- [ ] **Step 3: commit+push;远端跑**(SSH:export `W4A_LINEAR_CKPT` + `W4A_ANCHOR`=Task2 的 S_anchor,跑 `test_ml_norman_score.py`)。**Gate**:1 passed —— praxis 复现分数 == anchor。

---

## Task 6:conftest remote marker + Mac 零回归 + push

**Files:** Modify `praxis_virtualcell/tests/conftest.py`(加 `remote` marker + 默认 skip)

- [ ] **Step 1: 改 conftest** —— 在现有 `pytest_configure` 加一行 marker,在 `pytest_collection_modifyitems` 加 remote skip(无 torch 即 Mac):

`pytest_configure` 增:
```python
    config.addinivalue_line("markers", "remote: 需远端 GPU + torch + donor(Mac 无 torch 时 skip)")
```
`pytest_collection_modifyitems` 末尾增:
```python
    try:
        import torch  # noqa: F401
        has_torch = True
    except Exception:
        has_torch = False
    if not has_torch:
        skip_remote = pytest.mark.skip(reason="无 torch(Mac 本地),跳过 remote 标记测试")
        for item in items:
            if "remote" in item.keywords:
                item.add_marker(skip_remote)
```

- [ ] **Step 2: Mac 全套零回归**

```bash
cd /Volumes/T7/PRAXIS-virtualcell && find praxis_virtualcell -name '._*' -delete
.venv/bin/python -m pytest praxis_virtualcell/tests -q -p no:cacheprovider 2>&1 | tail -5
```
Expected:Week 2/3 的 48 + offline ml 测试全 pass;ml 的 `remote` 测试 **skipped**(Mac 无 torch);0 failed。

- [ ] **Step 3: commit + push** `git add praxis_virtualcell/tests/conftest.py && git commit -m "test(w4a): remote marker (skip ml tests without torch)" && git push -q origin main`

- [ ] **Step 4: 远端全 ml 套确认** SSH 跑 `pytest praxis_virtualcell/tests/test_ml_*.py -q`(export 两个 env),应全 pass。

---

## 验收(DoD)
1. 远端 `virtualcell` 环境 `torch.cuda.is_available()` True。
2. M1:donor linear Norman ΔPearson 复现,记 anchor(≈ ckpt 记录的 S0)。
3. M2:`predictors/ml/{donor_bridge,linear_additive_agent}` + `benchmarks/norman_eval` 在远端跑通;包装预测逐元素 == donor;praxis 复现分数 == anchor(<1e-4)。
4. Mac 端 48 + offline 测试零回归;ml `remote` 测试 Mac skip、远端 pass。
5. 只读复用 donor `Virtual cell`(不写它的 runs);torch 不进 Mac。
6. Week 4b(留):latent/cpa/gnn/decoder + Coordinator + ~0.70。
