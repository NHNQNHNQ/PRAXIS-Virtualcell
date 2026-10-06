"""Pseudomonas Aeruginosa 物种 agent。"""
from __future__ import annotations

from praxis_virtualcell.mdr_gnb.agents.base_species_agent import BaseSpeciesAgent


class PaeAgent(BaseSpeciesAgent):
    name = "PaeAgent"
    species = "pseudomonas_aeruginosa"


# 兼容旧名(M0 __init__ 引用)
PseudomonasAeruginosaAgent = PaeAgent
