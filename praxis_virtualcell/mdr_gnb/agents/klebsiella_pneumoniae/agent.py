"""Klebsiella pneumoniae 物种 agent(锚点物种之一,G2)。"""
from __future__ import annotations

from praxis_virtualcell.mdr_gnb.agents.base_species_agent import BaseSpeciesAgent


class KpnAgent(BaseSpeciesAgent):
    name = "KpnAgent"
    species = "klebsiella_pneumoniae"


# 兼容旧名(M0 stub 曾用 KlebsiellaPneumoniaeAgent)
KlebsiellaPneumoniaeAgent = KpnAgent
