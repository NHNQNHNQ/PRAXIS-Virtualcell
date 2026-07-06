"""model_zoo 自训模型训练契约基建(Phase 7)。SelfTrainingSpec:声明式训练卡 + fail-closed 校验。
真训脚本在 .53(donor benchmarks/);本包只声明契约 + 派生 registry training_card(单一真相源)。"""
from praxis_virtualcell.model_zoo.training.spec import SelfTrainingSpec

__all__ = ["SelfTrainingSpec"]
