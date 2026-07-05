"""ScgptWrapper:把 .53 上真跑的 scGPT(frozen backbone 53.8M + 轻 head 2.47M)收编为 ModelWrapper。

与 GemWrapper/GearsWrapper 同构。scGPT 接口已同构 donor(finding_w4c_scgpt:
MLPredictorAgent(scgpt).predict_tensor == donor predict,atol 1e-6),故真推理**复用**
predictors/ml 的 build_predictor_from_ckpt + MLPredictorAgent,不重写 ML 内核。
lazy import(donor_bridge 顶层 import torch → 缺 torch 即抛 → 继承 handle 归 failed,fail-closed)。
本地无 torch → run_prediction 缺依赖 fail-closed;真推理(load 196MB ckpt)是 .53(Task 6.5 gated)。

锚点(finding_w4c_scgpt):ΔPearson 0.4407 / cosine 0.9808 / n 7290(donor norman test split,
同表 A 口径,与 donor base 可比);frozen backbone + 轻 head 在 norman 饱和 → 明显低于 base(诚实)。
ckpt:/home/zkyd/data1/mzy/scgpt_ckpt/norman_2019/pretrained_backbone.{pt,json}(pt≈196MB)。
"""
from __future__ import annotations

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


class ScgptWrapper(ModelWrapper):
    name = "ScgptWrapper"

    def __init__(self, ckpt_stem: str | None = None) -> None:
        # 不在构造时载 torch/ckpt(允许无 torch 环境查 scope/provenance);真推理时 lazy import。
        self._ckpt_stem = ckpt_stem

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],                    # norman 域;扩 mouse 留 v1.3 待确认
            "module": "genetic_hub",
            "task": ["predict_delta_expression"],
            "perturbation": ["gene"],
        }

    def declare_provenance(self) -> dict:
        return {
            "model": "scgpt",
            "type": "public_model",
            "training_data": "donor norman_2019 (frozen scGPT encoder + light head)",
            "architecture": "frozen scGPT backbone 53.8M + head 2.47M (train_loss 0.045->0.044 saturated)",
            "metrics": {
                # 同表 A 口径的 per-cell ΔPearson(与 donor base 可比)
                "delta_pearson": 0.4407,
                "cosine": 0.9808,
                "n": 7290,
                "metric_note": "per-cell delta_pearson on donor norman test split (comparable to base)",
            },
            "not_comparable_to_donor_base": False,    # 同口径可比(与 GEARS 不同)
            "frozen_backbone_underperforms": True,     # 诚实:0.4407 明显低于 base(cpa 0.6716 等)
            "underperform_reason": "frozen foundation encoder + light head saturates on norman; "
                                   "SOTA needs fine-tune (unfreeze 53.8M + flash_attn) — backlog",
            "remote_env": {
                "host": "zkyd@10.102.106.53",
                "conda_env": "vc-scgpt (torch 2.3+cu121)",
                "donor_src": "/home/zkyd/data1/mzy/Virtual cell",
                "ckpt": "/home/zkyd/data1/mzy/scgpt_ckpt/norman_2019/pretrained_backbone.{pt,json}",
            },
            "distributable": False,                    # 196MB ckpt + torch;缺则 fail-closed
            "status_note": "integration pipeline fully verified on .53; frozen baseline honest-low",
        }

    def estimate_uncertainty(self, model_input: dict, prediction: dict | None) -> dict:
        return {"available": False, "reason": "model_reports_no_calibrated_uncertainty",
                "method": "point_estimate"}

    def run_prediction(self, model_input: dict) -> dict:
        """真推理:lazy import donor_bridge(顶层 import torch → 缺则抛)→ build_predictor_from_ckpt
        重建 scgpt backbone + load head → MLPredictorAgent 真跑。缺 torch/ckpt → 抛 → handle 归 failed
        (fail-closed,不静默返回假 delta)。本地无 torch → 此处即抛;.53 真跑(Task 6.5 gated)。"""
        if not self._ckpt_stem:
            raise RuntimeError("scgpt ckpt 未声明(registry assets requires_manual_fetch);fail-closed")
        # donor_bridge 顶层 import torch;本地无 torch → ModuleNotFoundError(fail-closed 触发点)
        from praxis_virtualcell.predictors.ml.agent_adapter import make_ml_agent
        from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt

        model, _cfg = build_predictor_from_ckpt(self._ckpt_stem)  # 重建 scgpt backbone + load head
        # 真推理复用 MLBackedPredictorAgent(scGPT 接口已同构 donor,finding_w4c_scgpt);
        # control baseline + pert_table 由 norman test ds 提供(make_ml_agent 默认加载)。
        agent = make_ml_agent(model, name="scgpt")
        targets = list(model_input.get("targets", []))
        # prepare_input 读 request.perturbation_targets → esm2 pert_emb + norman control。
        mi = agent.prepare_input({"perturbation_targets": targets}, {})
        # run_prediction 走 MLPredictorAgent.predict_tensor(== donor predict);返回 delta/n_genes/uncertainty。
        return agent.run_prediction(mi)
