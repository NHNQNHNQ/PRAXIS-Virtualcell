"""Salmonella Enterica 物种 agent。"""
from __future__ import annotations

from praxis_virtualcell.mdr_gnb.agents.base_species_agent import BaseSpeciesAgent


class SenAgent(BaseSpeciesAgent):
    name = "SenAgent"
    species = "salmonella_enterica"


# 兼容旧名(M0 __init__ 引用)
SalmonellaEntericaAgent = SenAgent
