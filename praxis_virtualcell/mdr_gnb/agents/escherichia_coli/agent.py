"""Escherichia coli 物种 agent(锚点物种之一,G2)。"""
from __future__ import annotations

from praxis_virtualcell.mdr_gnb.agents.base_species_agent import BaseSpeciesAgent


class EColiAgent(BaseSpeciesAgent):
    name = "EColiAgent"
    species = "escherichia_coli"


# 兼容旧名(M0 stub 曾用 EscherichiaColiAgent)
EscherichiaColiAgent = EColiAgent
