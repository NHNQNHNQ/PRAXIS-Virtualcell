"""药物 agent:按药物类特征化 + 调用对应预测器,产出 DrugTestResult。"""
from __future__ import annotations

from praxis_virtualcell.mdr_gnb.drug_agent.drug_schema import DrugTestRequest, DrugTestResult


class DrugAgent:
    """接收 DrugTestRequest,分发到抗菌肽/小分子/规则等特征与模型。M4/M5 实现。"""

    def predict(self, request: DrugTestRequest) -> list[DrugTestResult]:
        raise NotImplementedError("M4/M5 实现:药物类分发 + 特征化 + 预测/弃权")
