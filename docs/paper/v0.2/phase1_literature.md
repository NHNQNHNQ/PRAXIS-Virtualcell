# Phase 1 — Literature Search Report (v0.2 rewrite)

> ARS academic-paper `full` mode, Phase 1 deliverable. Evidence base for Phases 2–7.
> **All DOIs verified via CrossRef REST API or official publisher/proceedings pages** (anti-fabrication
> IRON RULE). Verification status marked per entry. Internal project evidence (the *results* of this
> paper) lives in `docs/findings/` + `docs/RELEASE-v0.1.0.md` and is NOT a literature source.

## Search strategy

- **Engine** (literature MCP servers unavailable this session): CrossRef REST API
  (`api.crossref.org/works?query.bibliographic=…&select=…`) via WebFetch for deterministic metadata + DOI;
  WebSearch for discovery of the exact paper; publisher/proceedings pages for conference/JMLR works without
  CrossRef DOIs.
- **Concepts** (methods/systems paper): virtual cell program · single-cell perturbation prediction ·
  perturbation data/Perturb-seq · single-cell foundation models + their limits · selective prediction /
  reject option / abstention · QSAR applicability domain · multi-agent LLM systems & AI agents for science ·
  trustworthy AI for science · reproducible computational research.
- **Currency**: foundational works (Chow 1970; El-Yaniv 2010) + recent (≥2019 for the perturbation field;
  STATE 2025 captures the current SOTA). Peer-reviewed majority; 3 preprints/conference works flagged.

## Annotated bibliography (20 sources, by theme)

### Theme A — Virtual-cell vision & program
- **Bunne 2024** — Bunne, C. et al. *How to build the virtual cell with artificial intelligence: priorities and opportunities.* **Cell** 187(25):7045–7063 (2024). DOI 10.1016/j.cell.2024.11.015. [CrossRef-verified] · positions the trustworthy-prediction gap the paper targets.
- **Rood 2024** — Rood, J. E., Hupalowska, A. & Regev, A. *Toward a foundation model of causal cell and tissue biology with a Perturbation Cell and Tissue Atlas.* **Cell** 187(17):4520–4545 (2024). DOI 10.1016/j.cell.2024.07.035. [CrossRef-verified] · second vision anchor; perturbation atlas + causal modeling.

### Theme B — Perturbation data & benchmarks
- **Dixit 2016** — Dixit, A. et al. *Perturb-Seq: Dissecting Molecular Circuits with Scalable Single-Cell RNA Profiling of Pooled Genetic Screens.* **Cell** 167(7):1853–1866.e17 (2016). DOI 10.1016/j.cell.2016.11.038. [CrossRef-verified] · introduces the Perturb-seq paradigm.
- **Replogle 2022** — Replogle, J. M. et al. *Mapping information-rich genotype-phenotype landscapes with genome-scale Perturb-seq.* **Cell** 185(14):2559–2575.e28 (2022). DOI 10.1016/j.cell.2022.05.013. [CrossRef-verified] · genome-scale perturbation landscapes.
- **Norman 2019** — Norman, T. M. et al. *Exploring genetic interaction manifolds constructed from rich single-cell phenotypes.* **Science** 365(6455):786–793 (2019). DOI 10.1126/science.aax4438. [CrossRef-verified] · the benchmark dataset used here.

### Theme C — Perturbation-prediction models
- **Lotfollahi 2019 (scGen)** — Lotfollahi, M., Wolf, F. A. & Theis, F. J. *scGen predicts single-cell perturbation responses.* **Nat. Methods** 16(8):715–721 (2019). DOI 10.1038/s41592-019-0494-8. [CrossRef-verified] · early generative perturbation predictor.
- **Lotfollahi 2023 (CPA)** — Lotfollahi, M. et al. *Predicting cellular responses to complex perturbations in high-throughput screens.* **Mol. Syst. Biol.** 19(6):e11517 (2023). DOI 10.15252/msb.202211517. [CrossRef-verified] · compositional perturbation autoencoder; a base predictor lineage.
- **Roohani 2024 (GEARS)** — Roohani, Y., Huang, K. & Leskovec, J. *Predicting transcriptional outcomes of novel multigene perturbations with GEARS.* **Nat. Biotechnol.** 42(6):927–935 (2024). DOI 10.1038/s41587-023-01905-6. [CrossRef-verified] · task-specific graph model; external-integration sanity check.
- **Adduri 2025 (STATE)** — Adduri, A. K. et al. *Predicting cellular responses to perturbation across diverse contexts with State.* **bioRxiv** (2025). DOI 10.1101/2025.06.26.661135. [CrossRef-verified] **· PREPRINT** · current SOTA perturbation foundation model (Arc Institute); cite as preprint.

### Theme D — Single-cell foundation models & their limits
- **Cui 2024 (scGPT)** — Cui, H. et al. *scGPT: toward building a foundation model for single-cell multiomics using generative AI.* **Nat. Methods** 21(8):1470–1480 (2024). DOI 10.1038/s41592-024-02201-0. [CrossRef-verified] · foundation model integrated here as a predictor.
- **Theodoris 2023 (Geneformer)** — Theodoris, C. V. et al. *Transfer learning enables predictions in network biology.* **Nature** 618(7965):616–624 (2023). DOI 10.1038/s41586-023-06139-9. [CrossRef-verified] · transfer-learning foundation model.
- **Kedzierska 2023** — Kedzierska, K. Z., Crawford, L., Amini, A. P. & Lu, A. X. *Assessing the limits of zero-shot foundation models in single-cell biology.* **bioRxiv** (2023). DOI 10.1101/2023.10.16.561085. [CrossRef-verified] **· PREPRINT** · evidence that scale ≠ task performance; supports "not a silver bullet".

### Theme E — Selective prediction / reject option / abstention
- **Chow 1970** — Chow, C. K. *On optimum recognition error and reject tradeoff.* **IEEE Trans. Inf. Theory** 16(1):41–46 (1970). DOI 10.1109/TIT.1970.1054406. [CrossRef-verified] · foundational error–reject tradeoff.
- **El-Yaniv 2010** — El-Yaniv, R. & Wiener, Y. *On the foundations of noise-free selective classification.* **J. Mach. Learn. Res.** 11:1605–1641 (2010). [WebSearch-only — JMLR has no CrossRef DOI; jmlr.org/papers/v11/el-yaniv10a.html] · risk–coverage theory.
- **Geifman 2017** — Geifman, Y. & El-Yaniv, R. *Selective classification for deep neural networks.* **Adv. Neural Inf. Process. Syst. (NeurIPS)** 30:4878–4887 (2017). arXiv:1705.08500. [WebSearch-only — NeurIPS proceedings, no CrossRef DOI] · selective prediction for DNNs.
- **Hendrickx 2024** — Hendrickx, K., Perini, L., Van der Plas, D., Meert, W. & Davis, J. *Machine learning with a reject option: a survey.* **Mach. Learn.** 113(5):3073–3110 (2024). DOI 10.1007/s10994-024-06534-x. [CrossRef-verified] · modern survey; situates the abstain mechanism.

### Theme F — Applicability domain
- **Sahigara 2012** — Sahigara, F. et al. *Comparison of different approaches to define the applicability domain of QSAR models.* **Molecules** 17(5):4791–4810 (2012). DOI 10.3390/molecules17054791. [CrossRef-verified] · QSAR applicability-domain analogue for the species-aware applicability rules.

### Theme G — Multi-agent LLM systems & AI agents for science
- **Wu 2024 (AutoGen)** — Wu, Q. et al. *AutoGen: enabling next-gen LLM applications via multi-agent conversation.* **Conf. on Language Modeling (COLM)** (2024). arXiv:2308.08155. [WebSearch-only — COLM 2024, no CrossRef DOI] · multi-agent LLM conversation framework.
- **Boiko 2023** — Boiko, D. A., MacKnight, R., Kline, B. & Gomes, G. *Autonomous chemical research with large language models.* **Nature** 624(7992):570–578 (2023). DOI 10.1038/s41586-023-06792-0. [CrossRef-verified] · autonomous LLM science agent.
- **Bran 2024 (ChemCrow)** — Bran, A. M. et al. *Augmenting large language models with chemistry tools.* **Nat. Mach. Intell.** 6(5):525–535 (2024). DOI 10.1038/s42256-024-00832-8. [CrossRef-verified] · tool-augmented LLM agent.

### Theme H — Trustworthy AI for science & reproducibility
- **Wang 2023** — Wang, H. et al. *Scientific discovery in the age of artificial intelligence.* **Nature** 620(7972):47–60 (2023). DOI 10.1038/s41586-023-06221-2. [CrossRef-verified] · macro framing of trustworthy AI-for-science.
- **Sandve 2013** — Sandve, G. K., Nekrutenko, A., Taylor, J. & Hovig, E. *Ten simple rules for reproducible computational research.* **PLoS Comput. Biol.** 9(10):e1003285 (2013). DOI 10.1371/journal.pcbi.1003285. [CrossRef-verified] · reproducibility norms (offline-reproducible claim).

## Literature matrix (source × theme)

| Source | VirtualCell | PerturbData | PredModels | FoundationLimits | SelectivePred | MultiAgent | Quality |
|---|---|---|---|---|---|---|---|
| Bunne 2024 | main | | x | | | | High |
| Rood 2024 | main | x | | | | | High |
| Dixit 2016 | | main | | | | | High |
| Replogle 2022 | | main | | | | | High |
| Norman 2019 | | main | x | | | | High |
| scGen 2019 | | | main | | | | High |
| CPA 2023 | | | main | | | | High |
| GEARS 2024 | | | main | | | | High |
| STATE 2025 | x | | main | | | | High (preprint) |
| scGPT 2024 | | | x | main | | | High |
| Geneformer 2023 | | | x | main | | | High |
| Kedzierska 2023 | | | | main | | | Med (preprint) |
| Chow 1970 | | | | | main | | Seminal |
| El-Yaniv 2010 | | | | | main | | High |
| Geifman 2017 | | | | | main | | High |
| Hendrickx 2024 | | | | | main | | High |
| Sahigara 2012 | | | | | x(AD) | | High |
| AutoGen 2024 | | | | | | main | High |
| Boiko 2023 | | | | | | main | High |
| Bran 2024 | | | | | | main | High |
| Wang 2023 | x | | | | | x | High |
| Sandve 2013 | | | | | | | High |

## Identified research gaps (→ contribution statement)

1. **No applicability/abstention layer in perturbation predictors** — scGen/CPA/GEARS/scGPT/STATE all return a number for any input; none carries a reject option (Theme C/D vs Theme E/F). PRAXIS adds species-aware applicability + abstention as enforced control flow.
2. **Reliability machinery is per-model, not systemic** — no auditable message bus / provenance / trace-critic spanning heterogeneous predictors. Multi-agent LLM work (Theme G) is about task automation, not trustworthy perturbation prediction.
3. **Foundation-model scale ≠ task performance** (Kedzierska 2023; our scGPT 0.4407) — motivates keeping task-specific predictors with a routing/governance layer rather than a single large model.

## Recommended sources by section

| Section | Key sources |
|---|---|
| Introduction | Bunne 2024, Rood 2024, Norman 2019, Wang 2023, Kedzierska 2023 |
| Related Work | scGen 2019, CPA 2023, GEARS 2024, scGPT 2024, Geneformer 2023, STATE 2025; Chow 1970, El-Yaniv 2010, Geifman 2017, Hendrickx 2024, Sahigara 2012; AutoGen 2024, Boiko 2023, Bran 2024 |
| Methods | Norman 2019, Dixit 2016, Replogle 2022, Sandve 2013 |
| Discussion | STATE 2025, Kedzierska 2023, Wang 2023, Bunne 2024 |

## Coverage / honesty notes
- 3 non-journal sources flagged: STATE (bioRxiv preprint), Kedzierska (bioRxiv preprint), Geifman/AutoGen (conference, no CrossRef DOI), El-Yaniv (JMLR, no CrossRef DOI). All have a verifiable stable identifier.
- DISTRIBUTIONAL_SKEW_ADVISORY: venue tier — Nature-family concentration is high but substantively justified for a methods/systems paper; not a defect.
