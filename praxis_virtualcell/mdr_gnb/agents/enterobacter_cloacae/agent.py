"""Enterobacter Cloacae 物种 agent。"""
from __future__ import annotations

from praxis_virtualcell.mdr_gnb.agents.base_species_agent import BaseSpeciesAgent


class EclAgent(BaseSpeciesAgent):
    name = "EclAgent"
    species = "enterobacter_cloacae"


# 兼容旧名(M0 __init__ 引用)
EnterobacterCloacaeAgent = EclAgent
