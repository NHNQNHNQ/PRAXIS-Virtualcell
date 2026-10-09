"""SelfTrainedWrapper:自训模型收编为 ModelWrapper 插件。第一个真实样板 = norman_mean_baseline
(mean-perturbation naive baseline,donor benchmarks/mean_baseline.py 已在 .53 真跑出
per-cell ΔPearson 0.4615)。

与 GemWrapper/ScgptWrapper 同构:extends ModelWrapper(拿 fail-closed + retrieve-before-predict 门)。
真推理复用 donor benchmarks.mean_baseline(compute_mean_delta / _build_mean_predictor),lazy import
(donor 顶层 import torch → 缺 torch 即抛 → 继承 handle 归 failed,fail-closed)。本地无 torch →
run_prediction 缺依赖 fail-closed;真训 + 真推理(load donor + mean_delta ckpt)是 .53(Task 7.5 gated)。

锚点(mean_baseline.py 实测):per-cell ΔPearson 0.4615 / cosine 0.9850 / n 18874(donor norman
test split,同表 A 口径,与 donor base 可比)。诚实:naive lower-bound baseline,低于 trained
predictors(base 0.6183~0.6716)by design —— perturbation-agnostic 无法捕捉扰动特异效应。
"""
from __future__ import annotations

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


class SelfTrainedWrapper(ModelWrapper):
    name = "SelfTrainedWrapper"

    def __init__(self, spec_name: str | None = None, ckpt_stem: str | None = None) -> None:
        # 不在构造载 torch/donor(允许无 torch 环境查 scope/provenance/契约);真推理时 lazy import。
        self._spec_name = spec_name or "norman_mean_baseline"
        self._ckpt_stem = ckpt_stem

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],                    # norman 训练域;扩其他物种留 v1.3 待确认
            "module": "genetic_hub",                 # 对齐 registry.yaml norman_mean_baseline.module
            "task": ["predict_delta_expression"],
            "perturbation": ["gene", "gene_combination"],
        }

    def declare_provenance(self) -> dict:
        return {
            "model": "norman_mean_baseline",
            "type": "self_trained",
            "training_data": "donor norman_2019 (Perturb-seq K562); mean_delta over non-control cells",
            "architecture": "mean-perturbation naive baseline (perturbation-agnostic: control + mean_delta)",
            "metrics": {
                # mean_baseline.py 实测:per-cell ΔPearson(同表 A 口径,与 donor base 可比)
                "delta_pearson": 0.4615,
                "cosine": 0.9850,
                "n": 18874,
                "n_train": 25463,
                "metric_note": "per-cell delta_pearson on donor norman test split (train seed 0/test seed 1)",
            },
            # 诚实:这是 naive 下界 baseline,低于 trained predictors(base 0.6183~0.6716)by design
            "is_naive_lower_bound_baseline": True,
            "baseline_note": "perturbation-agnostic; cannot capture pert-specific effects — "
                             "intentional same-protocol lower bound (>=3 baseline invariant)",
            "remote_env": {                            # 数据/env/脚本坐标(挪出硬编码 → 声明式)
                "host": "zkyd@10.102.106.53",
                "conda_env": "virtualcell (torch 2.6+cu124)",
                "data": "/home/zkyd/data1/mzy/gears_data/norman_donor/perturb_processed.h5ad",
                "donor_src": "/home/zkyd/data1/mzy/Virtual cell",
                "training_script": "praxis_virtualcell.benchmarks.mean_baseline",
            },
            "distributable": False,                    # 需 torch + donor loader;缺则 fail-closed
            "status_note": "capability real on .53 (mean_baseline scored 0.4615); ckpt fetch gated",
        }

    def estimate_uncertainty(self, model_input: dict, prediction: dict | None) -> dict:
        # mean baseline 是确定性点估计(mean_delta 固定)→ 诚实 available=False(不假造 CI)
        return {"available": False, "reason": "mean_baseline_is_point_estimate",
                "method": "point_estimate"}

    def run_prediction(self, model_input: dict) -> dict:
        """真推理:lazy import donor benchmarks.mean_baseline(顶层链 import torch → 缺则抛)→
        重建 mean predictor(load 落盘 mean_delta ckpt)→ 预测 control + mean_delta。
        缺 torch/未声明 ckpt(未训)→ 抛 → 继承 handle 归 failed(fail-closed,不静默返回假 delta)。
        本地无 torch → 此处即抛;.53 上真跑(Task 7.5 gated)。"""
        if not self._ckpt_stem:
            raise RuntimeError(
                "self_trained ckpt 未声明(mean_delta 未训/未落盘;registry assets requires_manual_fetch);"
                "fail-closed —— 不静默返回假 delta")
        # donor mean_baseline 顶层链 import torch;本地无 torch → ModuleNotFoundError(fail-closed 触发点)
        import torch  # noqa: F401 — 缺 torch 即抛

        from praxis_virtualcell.benchmarks.mean_baseline import _build_mean_predictor

        # 1) load 落盘 mean_delta(.53 训练产物;torch.load 小 tensor ≈ 8KB)
        mean_delta = torch.load(self._ckpt_stem, weights_only=False)
        if hasattr(mean_delta, "mean_delta"):        # 若存的是 state_dict/dict,取 mean_delta buffer
            mean_delta = mean_delta["mean_delta"] if isinstance(mean_delta, dict) else mean_delta.mean_delta
        predictor = _build_mean_predictor(mean_delta)

        # 2) 构造 control 上下文 + perturbation(donor 数据侧;真推理在 .53 由 Task 7.5 补全 ctx/pert 对照)
        #    这里走 donor predictor.predict(ctx, pert);缺 donor 数据 → 抛 → fail-closed。
        from predictors.base import Context, Perturbation  # donor(sys.path 由 mean_baseline 注入)

        targets = list(model_input.get("targets") or [])
        if not targets:
            raise ValueError("self_trained run_prediction 需 model_input['targets'];fail-closed")
        ctx = model_input.get("_context")            # .53 Task 7.5 注入真 control 张量
        if ctx is None:
            raise RuntimeError("缺 control 上下文(需 donor norman control tensor);fail-closed —— "
                               ".53 gated 真推理在 Task 7.5 注入")
        pert = Perturbation(kind="gene_ko", targets=tuple(targets))
        out = predictor.predict(Context(control=ctx), pert)

        # 3) 诚实包装:mean baseline delta(点估计,标 naive_lower_bound)
        delta = (out.mean - ctx).squeeze(0)
        return {
            "prediction": {
                "delta": delta.tolist(),
                "n_genes": int(delta.numel()),
                "value_type": "mean_baseline_delta",
                "is_naive_lower_bound_baseline": True,
            },
            "uncertainty": self.estimate_uncertainty(model_input, None),  # 点估计诚实标注
        }
