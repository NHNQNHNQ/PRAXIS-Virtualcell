"""能力声明式 Predictor 注册表(替代硬编码候选表)。

每个 predictor 用 PredictorSpec 声明其能力边界:支持哪些 species / drug_class /
output_kind、版本、artifact 路径、依赖。router 与 coordinator 只经 discover() 按能力
发现候选,绝不硬编码模型名。output_kind ∈ {mic_scalar, sir_class, synergy, peptide_activity,
sm_activity, mechanism_state},决定下游 ensembler 的聚合语义。

species / drug_class 支持通配 "*"(如 RuleBaselineSIR 覆盖全物种全药类作 fallback)。
discover 结果按 name 排序,保证 trace 确定性 replay。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

OUTPUT_KINDS = frozenset({
    "mic_scalar", "sir_class", "synergy",
    "peptide_activity", "sm_activity", "mechanism_state",
})


@dataclass
class PredictorSpec:
    name: str
    version: str
    species: list[str]            # 具体物种目录名列表,或 ["*"] 通配
    drug_class: list[str]         # beta_lactams/carbapenems/... 或 ["*"]
    output_kind: str              # OUTPUT_KINDS 之一
    artifact_path: str            # data/mdr_gnb/models/<species>/... (相对仓库根)
    requires: list[str] = field(default_factory=list)  # 需要的输入字段/上游能力
    # predict(ctx) -> dict:确定性纯函数;ctx 含 request/features/brain_context。
    # 由 registry 使用方在注册时绑定;registry 本身不加载 artifact(懒加载留给 spec.predict)。
    predict: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    # readiness(ctx) -> (ready, reason_code):声明存在不等于当前 artifact 可安全执行。
    # 为空时用于测试/无工件纯规则对象，按 ready 保持向后兼容。
    readiness: Callable[[dict[str, Any]], tuple[bool, str]] | None = None

    def supports(self, species: str, drug_class: str, output_kind: str) -> bool:
        sp_ok = "*" in self.species or species in self.species
        dc_ok = "*" in self.drug_class or drug_class in self.drug_class
        return sp_ok and dc_ok and self.output_kind == output_kind

    def __post_init__(self) -> None:
        if self.output_kind not in OUTPUT_KINDS:
            raise ValueError(f"未知 output_kind={self.output_kind};合法={sorted(OUTPUT_KINDS)}")

    def check_readiness(self, ctx: dict[str, Any]) -> tuple[bool, str]:
        """运行时就绪度门；任何检查异常均 fail-closed，而不是继续路由。"""
        if self.readiness is None:
            return True, "ready"
        try:
            ready, reason_code = self.readiness(ctx)
        except Exception:  # noqa: BLE001 - readiness probe must never make routing permissive
            return False, "readiness_check_failed"
        return bool(ready), str(reason_code)


class PredictorRegistry:
    def __init__(self) -> None:
        self._by_name: dict[str, PredictorSpec] = {}

    def register(self, spec: PredictorSpec) -> None:
        key = f"{spec.name}@{spec.version}"
        if key in self._by_name:
            raise ValueError(f"重复注册:{key}")
        self._by_name[key] = spec

    def get(self, name: str, version: str | None = None) -> PredictorSpec:
        if version is not None:
            return self._by_name[f"{name}@{version}"]
        # 无版本:取该 name 下版本号字典序最大者(确定性)
        cands = sorted((s for s in self._by_name.values() if s.name == name),
                       key=lambda s: s.version)
        if not cands:
            raise KeyError(name)
        return cands[-1]

    def discover(self, *, species: str, drug_class: str,
                 output_kind: str) -> list[PredictorSpec]:
        hit = [s for s in self._by_name.values()
               if s.supports(species, drug_class, output_kind)]
        return sorted(hit, key=lambda s: (s.name, s.version))

    def all_specs(self) -> list[PredictorSpec]:
        return sorted(self._by_name.values(), key=lambda s: (s.name, s.version))
