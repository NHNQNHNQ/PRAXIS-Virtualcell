"""Stenotrophomonas Maltophilia 物种 agent(固有耐药,诚实降级)。"""
from __future__ import annotations

from praxis_virtualcell.mdr_gnb.agents.base_species_agent import BaseSpeciesAgent


class SmaAgent(BaseSpeciesAgent):
    name = "SmaAgent"
    species = "stenotrophomonas_maltophilia"


# 兼容旧名(M0 __init__ 引用)
StenotrophomonasMaltophiliaAgent = SmaAgent
