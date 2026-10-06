"""版本冻结的 AMRFinderPlus 基因族 → SIR 规则基线(G2 对照方,不得漂移)。

命中任一收录基因族即判 R,否则 S(基因族前缀匹配:blaKPC 命中 blaKPC-3)。
db_version 记入快照;规则表未收录的药物显式抛错(不静默判 S,避免虚假 100% 敏感)。
NCBI 便捷入口 predict_one_genotype 直接吃 ncbi_amr_genotypes 串(剥离 =POINT/=MISTRANSLATION 修饰)。
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

_RULES_PATH = Path(__file__).resolve().parent / "rules" / "amrfinder_sir_rules.yaml"
_RULES_DOCUMENT_UNSET = object()


def _gene_names_from_genotype(genotype_str: str) -> list[str]:
    """从 NCBI ncbi_amr_genotypes 串取基因/突变基名(剥离 =POINT/=MISTRANSLATION 等修饰)。"""
    names: list[str] = []
    for raw in (genotype_str or "").split(","):
        base = raw.split("=", 1)[0].strip()
        if base:
            names.append(base)
    return names


class RuleBaselineSIR:
    """基于冻结版 AMRFinderPlus 规则的 SIR 预测,作为学习模型的对照基线。"""

    def __init__(
        self,
        db_version: str,
        rules_path: Path | None = None,
        rules_doc: Mapping[str, Any] | None | object = _RULES_DOCUMENT_UNSET,
    ) -> None:
        self.db_version = db_version
        self._rules_path = rules_path or _RULES_PATH
        if rules_doc is _RULES_DOCUMENT_UNSET:
            with open(self._rules_path, encoding="utf-8") as fh:
                doc = yaml.safe_load(fh)
        elif rules_doc is None:
            # A captured context saw no rules document.  Do not re-open the
            # path and accidentally consume a newer file under the old digest.
            raise FileNotFoundError("captured AMRFinder rules document is missing")
        else:
            # The execution context has already read and content-addressed this
            # document.  Copy it so downstream callers cannot mutate the
            # captured governance input in place.
            doc = deepcopy(dict(rules_doc))
        self._schema_version = doc["schema_version"]
        self._rules = doc["rules"]

    def predict_one(self, drug: str, amr_genes: list[str]) -> str:
        """基因名列表 → R/S;未收录药物抛 KeyError。"""
        if drug not in self._rules:
            raise KeyError(f"规则基线未收录药物 {drug!r};须先在 amrfinder_sir_rules.yaml 定义")
        families = self._rules[drug]["resistant_if_any"].get("gene_family", [])
        for g in (amr_genes or []):
            for fam in families:
                if g.startswith(fam):
                    return "R"
        return "S"

    def predict_one_genotype(self, drug: str, genotype_str: str) -> str:
        """便捷入口:直接吃 NCBI ncbi_amr_genotypes 串。"""
        return self.predict_one(drug, _gene_names_from_genotype(genotype_str))

    def predict(self, drug: str, amr_gene_lists: list[list[str]]) -> list[str]:
        return [self.predict_one(drug, gs) for gs in amr_gene_lists]

    def snapshot(self) -> dict:
        return {
            "amrfinder_db_version": self.db_version,
            "rules_schema_version": self._schema_version,
            "rules_path": str(self._rules_path),
        }
