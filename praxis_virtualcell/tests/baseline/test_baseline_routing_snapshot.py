"""Tests for baseline routing snapshot."""
import pytest

from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request

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
    assert dec.engine == engine, f"engine drift:  {dec.engine} != {engine}"
    assert dec.disposition == disp, f"disposition drift:  {dec.disposition} != {disp}"


def test_four_species_snapshot_covered():
    assert {c[0]["species"] for c in _SNAPSHOT} == {"human", "mouse", "yeast", "bacteria"}
