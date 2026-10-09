# Project provenance

PRAXIS-VirtualCell builds on the reusable PRAXIS-2 agent runtime imported at commit `b124d66`
on 11 June 2026. The `praxis2` Python namespace is retained for the agent framework and tool
interfaces. The virtual-cell scientific runtime is implemented in `praxis_virtualcell`.

The public source tree contains the virtual-cell platform, its scientific inputs and protocols,
the generic agent framework, and their tests. Historical account, billing, administration, and
HPC service components are outside the public platform scope.

For the framework's scientific description, see Zhenyu Ma and Xukai Jiang,
[PRAXIS-VirtualCell: A Programmable and Trustworthy Framework for Agentic Virtual Cell Experiments](https://arxiv.org/abs/2609.29221v1),
arXiv:2609.29221, 2026. Citation metadata is provided in `CITATION.cff` and `CITATION.bib`.
