"""外膜通透性模型(衔接用户 MaSIF 膜作用资产,M5 探查后接入)。"""
from __future__ import annotations


class MembranePermeabilityModel:
    """预测化合物穿越革兰阴性菌外膜的通透性。M5 实现。"""

    def predict(self, mol_features: dict, species: str):
        raise NotImplementedError("M5 实现:外膜通透性,衔接 MaSIF")
