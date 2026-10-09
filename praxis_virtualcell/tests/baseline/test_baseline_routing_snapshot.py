"""Phase 0 基线:pin 当前 4 物种代表请求的路由决策。
Phase 3 引入 module router 后,这些底层路由决策必须保持不变(module 是外层视图,
不改 engine 级路由)。若变=真实回归,停下排查。"""
import pytest

from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request

# (input, 期望 engine, 期望 disposition)—— 均为 route() 实跑锚点值
_SNAPSHOT = [
    ({"species": "human", "perturbation_object": "gene", "target_output": "expression",
      "perturbation_targets": ["AHR"]}, "donor_predictor", "accept"),
    ({"species": "mouse", "perturbation_object": "gene", "target_output": "expression",
      "perturbation_targets": ["Gata1"]}, "donor_predictor", "caution"),
    ({"species": "bacteria", "perturbation_object": "gene", "target_output": "growth",
      "perturbation_targets": ["b0720"]}, "gem_fba", "accept"),
    ({"species": "yeast", "perturbation_object": "gene", "target_output": "growth",
      "perturbation_targets": ["YBR166C"]}, "gem_fba", "accept"),
    ({"species": "bacteria", "perturbation_object": "gene", "target_output": "expression",
      "perturbation_targets": ["b0720"]}, "reject", "abstain"),
    ({"species": "yeast", "perturbation_object": "gene", "target_output": "expression",
      "perturbation_targets": ["YBR166C"]}, "reject", "abstain"),
]


@pytest.mark.parametrize("inp,engine,disp", _SNAPSHOT,
                         ids=[f"{c[0]['species']}_{c[0]['target_output']}" for c in _SNAPSHOT])
def test_routing_snapshot(inp, engine, disp):
    dec = route(normalize_request(inp))
    assert dec.engine == engine, f"engine 漂移: {dec.engine} != {engine}"
    assert dec.disposition == disp, f"disposition 漂移: {dec.disposition} != {disp}"


def test_four_species_snapshot_covered():
    assert {c[0]["species"] for c in _SNAPSHOT} == {"human", "mouse", "yeast", "bacteria"}
