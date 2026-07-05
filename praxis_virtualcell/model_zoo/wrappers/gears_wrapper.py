"""GearsWrapper:把 .53 上真跑的 GEARS(GNN,norman)收编为 ModelWrapper 插件。

与 GemWrapper 同构:extends ModelWrapper(拿 fail-closed + retrieve-before-predict 门)。
GEARS 接口 `predict([['gene']])` 与 donor predictor 不同构(finding_w4c_gears),故真推理
**不复用 MLPredictorAgent/donor_bridge**,走 GEARS 原生 API,lazy import(缺 torch/GEARS → 抛 →
继承 handle 归 failed,fail-closed)。本地无 torch → run_prediction 缺依赖 fail-closed;
真推理(load ckpt + GEARS predict)是 .53 的事(Task 6.5 gated)。

锚点(finding_w4c_gears):GEARS native pearson_de 0.8392(simulation split,含 baseline 的
absolute-expression pearson),⚠与 donor base 的 per-cell ΔPearson 不可比;同表 ΔPearson 是 backlog。
"""
from __future__ import annotations

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


class GearsWrapper(ModelWrapper):
    name = "GearsWrapper"

    def __init__(self, ckpt_stem: str | None = None) -> None:
        # 不在构造时载 torch/GEARS(允许无 torch 环境实例化以查 scope/provenance/契约);
        # 真推理时 lazy import,缺依赖 → 抛 → fail-closed。
        self._ckpt_stem = ckpt_stem

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],                    # norman 训练域(finding);扩 mouse 留 v1.3 待确认
            "module": "genetic_hub",                 # 对齐 registry.yaml gears.module
            "task": ["perturbation_response"],
            "perturbation": ["gene", "gene_combination"],
        }

    def declare_provenance(self) -> dict:
        return {
            "model": "gears",
            "type": "public_model",
            "training_data": "norman_2019 (Perturb-seq, K562)",
            "architecture": "GEARS GNN (hidden=64), 5 epoch",
            "metrics": {
                # GEARS 原生 compute_metrics(simulation split,absolute-expression pearson)
                "pearson": 0.9834,
                "pearson_de": 0.8392,
                "mse": 0.0068,
                # 同表 A 可比的 per-cell ΔPearson 未做(需 .53 GearsDonorAdapter,见 L4 runbook)
                "comparable_delta_pearson": None,
                "metric_note": "GEARS native pearson on absolute expression; NOT donor delta_pearson",
            },
            "not_comparable_to_donor_base": True,     # ADR-W4c-1:指标+split 不同,不可同表对比
            "no_fixed_seed_note": "GEARS retrain noise 0.8392->0.8461",
            "remote_env": {                            # 挪出硬编码 → 声明式
                "host": "zkyd@10.102.106.53",
                "conda_env": "virtualcell (torch 2.6+cu124)",
                "donor_src": "/home/zkyd/data1/mzy/Virtual cell",
            },
            "distributable": False,                    # 需 torch+GPU+GEARS 包;缺则 fail-closed
            "status_note": "capability real on .53; comparable-table ΔPearson is backlog",
        }

    def estimate_uncertainty(self, model_input: dict, prediction: dict | None) -> dict:
        # GEARS 输出点估计,无标定不确定性 → 诚实 available=False(不假造 CI)
        return {"available": False, "reason": "model_reports_no_calibrated_uncertainty",
                "method": "point_estimate"}

    # .53 上已处理并缓存的 norman PertData 目录(perturb_processed.h5ad + data_pyg + splits);
    # 与 gears_norman.py 训练同源(new_data_process("norman_donor2"))。可用 env 覆盖便于迁移。
    _GEARS_DATA_ROOT = "/home/zkyd/data1/mzy/gears_data"
    _GEARS_DATA_NAME = "norman_donor2"

    def run_prediction(self, model_input: dict) -> dict:
        """真推理:lazy import torch + GEARS,重建 PertData 上下文,load_pretrained,GEARS predict([[gene]])。
        缺 torch/GEARS/ckpt → 抛 → 继承 handle 归 failed(fail-closed,不静默返回 mock)。
        本地无 torch → 此处即抛;.53 上真跑(Task 6.5 gated)。

        GEARS.predict 返回 absolute expression(mean over cells),**非 donor delta**;此处诚实
        包成 {"prediction": {"expression": <array>, ...}, "uncertainty": {...}},并标注
        gears_native / not_comparable_to_donor_base(finding_w4c_gears),不冒充 donor delta。"""
        import os

        import torch  # noqa: F401 — 缺 torch 即抛 ModuleNotFoundError(fail-closed 触发点)
        # GEARS 0.0.2 老包 + 新 pandas 兼容:predict 内部走 sparse_X[pandas_Series_mask] 需 .nonzero()。
        import pandas as _pd
        _pd.Series.nonzero = lambda self: self.to_numpy().nonzero()
        from gears import GEARS, PertData  # 缺 GEARS 包即抛

        if not self._ckpt_stem:
            raise RuntimeError("gears ckpt 未声明(registry assets requires_manual_fetch);fail-closed")

        targets = list(model_input.get("targets") or [])
        if not targets:
            raise ValueError("gears run_prediction 需 model_input['targets'](扰动基因列表);fail-closed")

        # 1) 重建 PertData 上下文(载已处理缓存数据 + 复用 split;与训练脚本同参)。
        data_root = os.environ.get("GEARS_DATA_ROOT", self._GEARS_DATA_ROOT)
        data_name = os.environ.get("GEARS_DATA_NAME", self._GEARS_DATA_NAME)
        pert_data = PertData(data_root)
        pert_data.load(data_path=os.path.join(data_root, data_name))
        pert_data.prepare_split(split="simulation", seed=1)
        pert_data.get_dataloader(batch_size=32, test_batch_size=64)

        # 2) 建 GEARS 实例并 load_pretrained(从 save_model 落盘的 config.pkl + model.pt 目录)。
        device = "cuda" if torch.cuda.is_available() else "cpu"
        g = GEARS(pert_data, device=device)
        g.load_pretrained(self._ckpt_stem)

        # 3) 扰动基因须∈ vocab;不在则 fail-closed(不静默改测试凑绿)。GEARS.predict 自身也校验。
        for gene in targets:
            if gene not in g.pert_list:
                raise ValueError(f"{gene} 不在 GEARS.pert_list(vocab 9853);fail-closed(建议换 vocab 内真实 norman 扰动基因)")

        # 4) predict([[gene]]) → {'_'.join(pert): absolute-expression array}。key 为下划线拼接。
        res = g.predict([targets])
        cond_key = "_".join(targets)
        expr = res[cond_key]  # np.ndarray,mean-over-cells 的 absolute transcriptome

        # 5) 诚实包装:absolute expression(非 donor delta),标注 gears_native + 不可比。
        return {
            "prediction": {
                "expression": expr,
                "n_genes": int(len(expr)),
                "condition": cond_key,
                "value_type": "gears_native_absolute_expression",
                "not_comparable_to_donor_base": True,  # finding_w4c_gears:指标/split 不同,不同表
            },
            "uncertainty": self.estimate_uncertainty(model_input, None),  # 点估计诚实标注
        }
