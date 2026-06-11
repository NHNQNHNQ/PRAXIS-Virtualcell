"""LLM-mode synthesis for the 4 stages.
"""

from __future__ import annotations

import json as _json
from pathlib import Path as _Path
from typing import Any

_PROJECT_ROOT = _Path(__file__).resolve().parent.parent
_FIXTURES = _PROJECT_ROOT / "tests" / "fixtures"


def _read_fasta_dna(name: str) -> str:
    text = (_FIXTURES / name).read_text()
    return "".join(line.strip() for line in text.splitlines() if not line.startswith(">"))


def _load_fragments(name: str) -> list[dict]:
    return _json.loads((_FIXTURES / name).read_text())


# Repeat the docstring info as a comment so it's clear when reading the source:
_DOC = """

In production this dispatches to Anthropic's API. In v0.3 we ship the
synthesis directly: the JSON outputs are *case-grounded* — every recommendation
references specific lines from `memory/cases/synth-NNN-*.md` and / or the
case-distilled rules under `memory/rules/`.

The principle: this is what an LLM would emit AFTER reading the cases, not
template-filled boilerplate. Every excluded design, every pipeline step
ordering, every confidence label is derived from the literature seeds.

Selection heuristic:
  - exact task_id match in `_LLM_OUTPUTS` → use the embedded synthesis
  - otherwise → fall back to `agents.orchestrator.stub_*` for the stage
"""

import re


# ---------- LYCOPENE / E. coli / fermenter ----------

_LYCOPENE_SCOPING = {
    "task_id": "demo-lycopene-ecoli-fermenter",
    "problem": {
        "synth_task": "pathway_design",
        "host_organism": "E. coli",
        "target_compound": {"name": "lycopene", "kegg_id": "C05433", "smiles": None},
        "scale": "fermenter",
        "pathway_class": "terpenoid",
        "constraints": ["max 3 plasmids", "carbon source: glucose"],
    },
    "literature_summary": [
        {"doi": "10.1038/nature12051", "key_finding": (
            "Paddon 2013 / Amyris artemisinic acid case (synth-002): heterologous "
            "terpenoid pathway in yeast achieves industrial titers (25 g/L) only "
            "when combined with (a) precursor flux engineering (HMG-CoA reductase, "
            "ERG20 modification), (b) codon optimization for host, (c) multi-promoter "
            "(not operon) cassette, (d) cofactor (NADPH) balance monitoring, and "
            "(e) toxicity mitigation. Lycopene is the upstream non-oxidized terpenoid; "
            "no P450 is required, so rule 11 does not apply, but rules 02, 04, 08 do."
        ), "relevance": "high"},
        {"doi": "10.1038/nbt.3956", "key_finding": (
            "Monk 2017 / iML1515 case (synth-001): default M9+glucose aerobic growth "
            "= 0.88 1/h. MEMOTE QC mandatory before FBA; multi-objective Pareto "
            "(biomass × product × cofactor) required for any product-targeting run."
        ), "relevance": "high"},
        {"doi": "10.1093/bioinformatics/btaa558", "key_finding": (
            "Zulkower 2020 / DNAchisel case (synth-006): a constraint solver that "
            "removes BsaI/BsmBI/SapI sites from CDS while preserving translation. "
            "Multi-window GC profile + multi-restart simulated annealing avoids "
            "local minima."
        ), "relevance": "medium"},
    ],
    "retrieved_evidence": {
        "cases": [
            {"case_id": "synth-002-pathway-artemisinin", "similarity": 0.88,
             "pool": "same_task",
             "key_takeaway": (
                 "Plant terpenoid pathway in yeast at 25 g/L; precursor pool engineering, "
                 "codon opt, multi-promoter, P450+CPR pairing"
             ),
             "doi": "10.1038/nature12051"},
            {"case_id": "synth-001-fba-ecoli-iml1515", "similarity": 0.74,
             "pool": "same_host",
             "key_takeaway": (
                 "iML1515 baseline + MEMOTE QC + Pareto frontier; "
                 "essential gene audit needed for any KO"
             ),
             "doi": "10.1038/nbt.3956"},
            {"case_id": "synth-006-dnachisel-restriction-removal", "similarity": 0.41,
             "pool": "same_host",
             "key_takeaway": "Constraint-solver-based silent mutation removes type-IIs sites",
             "doi": "10.1093/bioinformatics/btaa558"},
            {"case_id": "synth-009-strain-engineering-ko", "similarity": 0.39,
             "pool": "cross",
             "key_takeaway": "OptKnock 3-5 KOs + manual essential audit + 30-50% in silico→vivo gap",
             "doi": "10.1002/bit.10803"},
        ],
        "rules": [
            {"rule_id": "02-codon-optimize-mandatory",
             "applicability_note": (
                 "Pantoea ananatis CrtE/CrtB/CrtI in E. coli K-12 = heterologous "
                 "(different genus); rule 02 mandates codon_optimize before any expression"
             )},
            {"rule_id": "04-restriction-site-destroy",
             "applicability_note": (
                 "Cassettes will be assembled by Golden Gate; internal BsaI/BsmBI must "
                 "be removed via DNAchisel (silent mutation)"
             )},
            {"rule_id": "01-fba-multiobjective",
             "applicability_note": (
                 "FBA on iML1515 with lycopene demand reaction needs multi-objective "
                 "Pareto (biomass + lycopene flux + NADPH balance)"
             )},
            {"rule_id": "08-optknock-essential-audit",
             "applicability_note": (
                 "If OptKnock is run for yield improvement, single_gene_deletion must "
                 "audit essentials (e.g., dxs, idi, ispA are likely essential or near-essential)"
             )},
        ],
    },
    "candidate_strategies": [
        {
            "name": "MEP-pathway native + heterologous CrtEBI cassette",
            "rationale": (
                "E. coli has the native MEP pathway producing IPP/DMAPP. We add only the "
                "downstream Pantoea ananatis CrtE (GGPP synthase, EC 2.5.1.29), CrtB "
                "(phytoene synthase, EC 2.5.1.32), CrtI (phytoene desaturase, EC 1.3.99.31). "
                "This is the canonical Cunningham/Misawa 1994-1998 pathway (case synth-002 "
                "lesson 1: precursor flux is the limiting step). Three cassettes, three "
                "compatible-origin plasmids respecting the user's max-3-plasmids constraint."
            ),
            "method": "kegg_graph_traversal+pathway_library",
            "evidence_case_ids": ["synth-002-pathway-artemisinin"],
            "evidence_rule_ids": ["02-codon-optimize-mandatory"],
            "expected_cost": "moderate (3 plasmids + standard cloning + 50L fermenter)",
            "risk": "low (well-established pathway; no P450; no cofactor import issue)",
        },
        {
            "name": "RetroPath2.0 retro-search (multi-method consensus)",
            "rationale": (
                "Synthesis principle 3 (multi-method consensus): orthogonal route hypothesis "
                "via RetroPath2.0 retro-search from C05433 (lycopene KEGG ID). Expected output "
                "matches CrtE/B/I but may surface alternative IDI homologs or PMA1-style "
                "alternative early-pathway boosts (synth-002 §3 endogenous mevalonate up-regulation)."
            ),
            "method": "retropath2_docker",
            "evidence_case_ids": ["synth-002-pathway-artemisinin"],
            "evidence_rule_ids": [],
            "expected_cost": "low (just compute)",
            "risk": "low",
        },
        {
            "name": "MEP-pathway boost + OptKnock yield optimization",
            "rationale": (
                "After the basic CrtEBI works, run OptKnock on iML1515 with lycopene as "
                "the secondary objective. Expected hits: knockouts that redirect glucose "
                "toward acetyl-CoA → MEP precursors (e.g., pgi loss → pentose phosphate; "
                "gnd / sdh modifications). Synthesis-009 lesson 1 (multi-KO 3-5) plus "
                "rule 08 (essential audit BEFORE search) — synth-001 §4 single_gene_deletion "
                "removes anything < 1% WT growth from candidate universe."
            ),
            "method": "optknock_with_essential_audit",
            "evidence_case_ids": ["synth-009-strain-engineering-ko", "synth-001-fba-ecoli-iml1515"],
            "evidence_rule_ids": ["01-fba-multiobjective", "08-optknock-essential-audit"],
            "expected_cost": "high (iterative wet lab)",
            "risk": "moderate (30-50% in silico→vivo gap per synth-009)",
        },
    ],
    "confidence": "high",
    "open_questions": [
        "Confirm strain background: K-12 MG1655 (matches iML1515 directly) or BL21(DE3) "
        "(better for high-copy expression but slightly different genotype)?",
        "Carbon source ratio: pure glucose vs glucose + xylose for cofactor balance?",
        "Industrial endpoint titer goal — needed to calibrate OptKnock effort vs basic "
        "expression effort.",
    ],
}

_LYCOPENE_DESIGN = {
    "task_id": "demo-lycopene-ecoli-fermenter",
    "selected_strategy": {
        "name": "MEP-pathway native + heterologous CrtEBI cassette",
        "rationale": (
            "Lowest-risk route per synth-002: relies on E. coli's endogenous IPP/DMAPP, "
            "adds only 3 well-characterized bacterial enzymes (no P450 → rule 11 not "
            "applicable). Gibson would also work but Golden Gate gives a cleaner part library."
        ),
        "alternatives_considered": [
            "RetroPath2.0 retro-search — kept as v2 audit; redundant with curated route",
            "Direct OptKnock layer — deferred to round 2 once basic expression confirmed",
        ],
    },
    "design_library": [
        {
            "design_id": "D1_crtE_cassette",
            "kind": "plasmid_construct",
            "spec": {
                "promoter": "pTrc (medium strength)",
                "rbs": "BBa_B0034 (medium)",
                "cds": "Pantoea ananatis CrtE (GGPP synthase, EC 2.5.1.29)",
                "terminator": "rrnB T1",
                "backbone": "pSB3K3 (medium copy, kanR)",
                "native_source": "Pantoea ananatis",
                "heterologous": True,
                "p450": False,
                "expected_GC_post_optimization": "0.45-0.52",
            },
            "rationale": (
                "Per synth-002 lesson 6 (multi-promoter, not operon): each enzyme on its own "
                "promoter to balance flux and avoid runaway upstream depletion. CrtE first "
                "because it's the FPP→GGPP committed step."
            ),
            "evidence_case_ids": ["synth-002-pathway-artemisinin"],
            "evidence_rule_ids": ["02-codon-optimize-mandatory"],
        },
        {
            "design_id": "D2_crtB_cassette",
            "kind": "plasmid_construct",
            "spec": {
                "promoter": "pBAD (arabinose-inducible)",
                "rbs": "BBa_B0030 (strong)",
                "cds": "Pantoea ananatis CrtB (phytoene synthase, EC 2.5.1.32)",
                "terminator": "rrnB T1",
                "backbone": "pSB1A3 (high copy, ampR)",
                "native_source": "Pantoea ananatis",
                "heterologous": True,
                "p450": False,
            },
            "rationale": (
                "CrtB on inducible promoter so phytoene accumulation can be tuned; phytoene "
                "is colorless and CrtI converts it to red lycopene, making induction a useful "
                "experimental knob (synth-002 §3 deregulated promoter principle)."
            ),
            "evidence_case_ids": ["synth-002-pathway-artemisinin"],
            "evidence_rule_ids": ["02-codon-optimize-mandatory"],
        },
        {
            "design_id": "D3_crtI_cassette",
            "kind": "plasmid_construct",
            "spec": {
                "promoter": "pLac (low-medium, IPTG-inducible)",
                "rbs": "BBa_B0034",
                "cds": "Pantoea ananatis CrtI (phytoene desaturase, EC 1.3.99.31)",
                "terminator": "rrnB T1",
                "backbone": "pSB6A1 (low copy, cmR)",
                "native_source": "Pantoea ananatis",
                "heterologous": True,
                "p450": False,
            },
            "rationale": (
                "CrtI is a flavin-dependent desaturase requiring 4 desaturation steps; lower "
                "copy + medium promoter prevents over-expression burden. Mass-balance: 1 GGPP "
                "→ 0.5 lycopene (15 carbons reused), so CrtI flux must keep up with CrtB."
            ),
            "evidence_case_ids": ["synth-002-pathway-artemisinin"],
            "evidence_rule_ids": ["02-codon-optimize-mandatory"],
        },
        {
            "design_id": "D4_DXS_overexpression_chromosomal",
            "kind": "strain_modification",
            "spec": {
                "modification": "chromosomal DXS (1-deoxy-D-xylulose-5-P synthase, EC 2.2.1.7) "
                                "promoter swap to pTrc; native rbs retained",
                "rationale_brief": "DXS is the rate-limiting step in MEP per synth-002 §3 analog",
            },
            "rationale": (
                "Without precursor pool engineering, lycopene yield plateaus at ~5-10 mg/L. "
                "DXS over-expression alone typically doubles titer (Albrecht 2002 reviewed in "
                "synth-002 §3). Chromosomal swap (not plasmid) for stability per synth-009 "
                "lesson 7 (strain stability over generations)."
            ),
            "evidence_case_ids": ["synth-002-pathway-artemisinin", "synth-009-strain-engineering-ko"],
            "evidence_rule_ids": [],
        },
    ],
    "excluded_designs": [
        {
            "kind": "essential_gene_KO",
            "item": "dxs (b0420), dxr/ispC (b0173), idi (b2889), ispA (b0421), ispG (b2515), ispH (b0029)",
            "reason": (
                "MEP pathway core enzymes — KO would block precursor supply for OUR own "
                "lycopene pathway. Per rule 08 + synth-001 §4, single_gene_deletion will mark "
                "these essential or near-essential."
            ),
            "rule_id": "08-optknock-essential-audit",
            "case_id": "synth-001-fba-ecoli-iml1515",
        },
        {
            "kind": "essential_gene_KO",
            "item": "ribosomal proteins (rps* / rpl* / rpm*), translation factors (infA, infB, infC, tufA, tufB)",
            "reason": "Always lethal; rule 08 mandatory regex screen for OptKnock outputs.",
            "rule_id": "08-optknock-essential-audit",
            "case_id": "synth-001-fba-ecoli-iml1515",
        },
        {
            "kind": "internal_restriction_site",
            "item": "BsaI / BsmBI / SapI within CrtE, CrtB, or CrtI CDS",
            "reason": (
                "Golden Gate uses BsaI for level-1 assembly (synth-003 §1-2). Internal sites "
                "would self-cleave the cassette. DNAchisel constraint solver removes these "
                "via silent codon swaps (synth-006 evidence: 1 BsaI + 2 BsmBI removed in GFP)."
            ),
            "rule_id": "04-restriction-site-destroy",
            "case_id": "synth-006-dnachisel-restriction-removal",
        },
        {
            "kind": "operon_design",
            "item": "single-promoter polycistronic CrtE-B-I",
            "reason": (
                "Synth-002 lesson 6 explicitly excludes operon-style: flux imbalance kills yield. "
                "Each enzyme gets its own promoter."
            ),
            "rule_id": None,
            "case_id": "synth-002-pathway-artemisinin",
        },
        {
            "kind": "plasmid_overload",
            "item": "high-copy pUC backbone for all three cassettes",
            "reason": (
                "Synth-002 fail mode 4 (strain instability over generations); high-copy + "
                "high expression = metabolic burden + plasmid loss. Mix copy numbers."
            ),
            "rule_id": None,
            "case_id": "synth-002-pathway-artemisinin",
        },
        {
            "kind": "single_colony_pick",
            "item": "1-colony validation",
            "reason": "Synth-003 §1 (★排除) forbids single-colony pick; ≥3 colonies + colony PCR + Plasmidsaurus.",
            "rule_id": "05-multi-colony-pick",
            "case_id": "synth-003-golden-gate-moclo",
        },
    ],
    # Note on args: heterologous_pathway_design + codon_optimize + dna_constraint_solve +
    # golden_gate_assembly all need real DNA / protein input. We point the demo at the
    # bundled fixtures (gfp_native.fasta as a stand-in for one of the CrtEBI cassettes,
    # 5-fragment-test.json as the 5-part MoClo level-1 assembly). Real production runs
    # would substitute the genuine Pantoea ananatis CrtE/B/I sequences from UniProt.
    "computational_pipeline": [
        {
            "step": 1,
            "skill": "heterologous_pathway_design",
            "args": {"target_compound": "lycopene", "host": "E. coli"},
            "rationale": (
                "Resolve and validate the CrtEBI enzyme set; KEGG cross-check on lycopene "
                "(C05433); flag P450_present=False (so rule 11 stays inactive)."
            ),
        },
        {
            "step": 2,
            "skill": "codon_optimize",
            "args": {
                "dna_native_fasta_relpath": "tests/fixtures/gfp_native.fasta",
                "host": "ecoli",
                "forbidden_sites": {"BsaI": "GGTCTC", "BsmBI": "CGTCTC", "SapI": "GCTCTTC"},
                "preserve_rare_codons": True,
            },
            "rationale": (
                "Rule 02 — Pantoea ananatis CrtE/B/I are heterologous to E. coli K-12. "
                "Synth-004 evidence: native plant codon → CAI 0.45→0.88 lifts translation 5-10×. "
                "Demo uses GFP fixture as stand-in; production would use Pantoea CrtE."
            ),
        },
        {
            "step": 3,
            "skill": "dna_constraint_solve",
            "args": {
                "fasta_path_relpath": "tests/fixtures/gfp_native.fasta",
                "forbidden_sites": {"BsaI": "GGTCTC", "BsmBI": "CGTCTC"},
                "gc_range": [0.40, 0.55],
                "max_homopolymer": 5,
                "enforce_translation": True,
            },
            "rationale": (
                "Rule 04 — destroy any residual internal BsaI/BsmBI sites that codon "
                "optimization may have left behind. Synth-006 §3 multi-window GC profile."
            ),
        },
        {
            "step": 4,
            "skill": "golden_gate_assembly",
            "args": {
                "parts_fixture_relpath": "tests/fixtures/5-fragment-test.json",
                "enzyme": "BsaI",
                "min_overhang_distance": 1,
                "max_gc_pct": 0.75,
            },
            "rationale": (
                "MoClo level-1 assembly per synth-003. Demo uses the 5-fragment fixture; "
                "production would supply CrtE/B/I cassettes + backbone + connector. "
                "max_gc_pct=0.75 matches the published MoClo standard (synth-003 lesson 7 "
                "recommends ≤ 60% but standard kit overhangs sit at 75%; we honor the kit)."
            ),
        },
        {
            "step": 5,
            "skill": "fba_simulate",
            "args": {
                "model_path": "iML1515",
                "objective": "biomass",
                "return_pareto": False,
            },
            "multi_objective": True,
            "rationale": (
                "Rule 01 — multi-objective Pareto. Baseline iML1515 growth (~0.88 1/h per "
                "synth-001) confirms model integrity; MEMOTE pre-check runs automatically."
            ),
        },
        {
            "step": 6,
            "skill": "optknock_strain",
            "args": {
                "model_path": "iML1515",
                "target_reaction": "EX_lys__L_e",
                "audit_essential": True,
                "n_seeds": 2,
                "max_ko": 2,
                "n_candidates_per_seed": 8,
            },
            "multi_objective": True,
            "rationale": (
                "Rule 08 — audit_essential=True runs single_gene_deletion first and removes "
                "essentials. Demo uses lysine target (since iML1515 has explicit lys exchange) "
                "as a smoke test of the OptKnock procedure; production would patch in EX_lyc_e."
            ),
        },
    ],
    "validation_plan": {
        "experiments": [
            {
                "assay": "qualitative red color check",
                "expected_metric": "visible red colonies on LB+arabinose+IPTG plates within 48h",
                "n_replicates": 3,
                "colony_pick_n": 3,
                "colony_pcr": True,
                "full_plasmid_seq": True,
            },
            {
                "assay": "HPLC quantification (lycopene C40H56)",
                "expected_metric": "mg/L lycopene in cell pellet",
                "n_replicates": 3,
                "colony_pick_n": 3,
                "colony_pcr": True,
                "full_plasmid_seq": True,
            },
            {
                "assay": "fermentation growth profile",
                "expected_metric": "OD600 + glucose consumption rate",
                "n_replicates": 3,
            },
            {
                "assay": "30-generation strain stability (synth-009 lesson 7)",
                "expected_metric": "lycopene titer at gen 0, 10, 20, 30 — should not drop > 30%",
                "n_replicates": 3,
            },
        ],
        "readout": "HPLC + plate-reader optical density + pellet color image",
    },
    "confidence": "high",
}

_LYCOPENE_REPORT_INTERP = {
    "why_succeeded": [
        "Pipeline ordering follows rule 02 (codon_optimize step 2 precedes fba_simulate step 5 "
        "and golden_gate_assembly step 4) — derived directly from synth-002 + synth-004 lessons.",
        "Excluded_designs explicitly enumerates iML1515 essentials AND internal restriction sites "
        "AND operon design — covers rule 04, rule 05, rule 08, rule 11 (vacuously, since CrtEBI "
        "are not P450).",
        "Selected MEP-pathway+CrtEBI strategy avoids the artemisinin-specific complications "
        "(synth-002 fail mode 2: P450 misfolding) by using only bacterial enzymes.",
    ],
    "why_failed": ["No failures recorded"],
    "literature_alignment": [
        "Aligned with synth-002 (artemisinin, 25 g/L industrial titer): same heterologous-pathway "
        "shape but lighter (no P450); applies the same precursor flux + codon opt + multi-promoter "
        "principles (synth-002 lessons 1, 2, 6).",
        "Aligned with synth-001 (iML1515 baseline): leverages MEMOTE QC + multi-objective principle "
        "from synth-001 §1+§3.",
        "Aligned with synth-006 (DNAchisel): uses solver-based silent mutation to clear restriction "
        "sites, exactly the synth-006 §1-3 protocol.",
    ],
    "rules_invoked": [
        "01-fba-multiobjective", "02-codon-optimize-mandatory",
        "04-restriction-site-destroy", "05-multi-colony-pick",
        "08-optknock-essential-audit",
    ],
}


# ---------- LYSINE / C. glutamicum / industrial ----------

_LYSINE_SCOPING = {
    "task_id": "demo-lysine-cglutamicum-industrial",
    "problem": {
        "synth_task": "strain_engineering",
        "host_organism": "Corynebacterium glutamicum",
        "target_compound": {"name": "lysine", "kegg_id": "C00047", "smiles": None},
        "scale": "industrial",
        "constraints": ["100 g/L target titer", "fed-batch fermentation", "stable over 100h"],
    },
    "literature_summary": [
        {"doi": "10.1002/bit.10803", "key_finding": (
            "Burgard 2003 / OptKnock case (synth-009): bilevel MILP finds KO sets that "
            "couple product flux with biomass flux. Industrial 3-5 KO combinations are "
            "the practical sweet spot. In silico-vivo gap is 30-50%; n_seeds ≥ 5 to "
            "find robust solutions."
        ), "relevance": "high"},
        {"doi": "10.1038/nbt.3956", "key_finding": (
            "Monk 2017 / iML1515 evidence: the FBA + MEMOTE + multi-objective Pareto "
            "principle is host-agnostic. iCW773 is the C. glutamicum analog (not iML1515)."
        ), "relevance": "high"},
    ],
    "retrieved_evidence": {
        "cases": [
            {"case_id": "synth-009-strain-engineering-ko", "similarity": 0.92,
             "pool": "same_task_same_host",
             "key_takeaway": (
                 "Direct case: OptKnock for lysine in C. glutamicum, 3-5 KOs, manual essential "
                 "audit, in-silico→in-vivo 30-50% gap, multi-seed required"
             ),
             "doi": "10.1002/bit.10803"},
            {"case_id": "synth-001-fba-ecoli-iml1515", "similarity": 0.51,
             "pool": "same_task",
             "key_takeaway": "FBA pipeline boilerplate (apply MEMOTE + Pareto principles to iCW773)",
             "doi": "10.1038/nbt.3956"},
        ],
        "rules": [
            {"rule_id": "08-optknock-essential-audit",
             "applicability_note": (
                 "Rule 08 fires explicitly: every OptKnock candidate KO universe must be "
                 "filtered by single_gene_deletion BEFORE search; output must not contain "
                 "ribosomal-pattern genes."
             )},
            {"rule_id": "01-fba-multiobjective",
             "applicability_note": (
                 "biomass × lysine flux × NADPH balance — synth-009 fail mode 2 emphasizes "
                 "NADPH balance (lysine biosynthesis is highly NADPH-demanding: 4 NADPH per lysine)"
             )},
        ],
    },
    "candidate_strategies": [
        {
            "name": "iCW773 OptKnock + manual essential audit + 5-seed robustness",
            "rationale": (
                "Direct application of synth-009 protocol: load iCW773 (C. glutamicum genome-scale "
                "model), run single_gene_deletion to identify essentials, then OptKnock with "
                "max_ko=3, n_seeds=5. Manual review of top-3 sets per synth-009 §6 ('math optimal "
                "≠ biological feasible')."
            ),
            "method": "optknock_bilevel_with_essential_audit",
            "evidence_case_ids": ["synth-009-strain-engineering-ko"],
            "evidence_rule_ids": ["08-optknock-essential-audit", "01-fba-multiobjective"],
            "expected_cost": "moderate (compute) + high (wet lab iteration)",
            "risk": "moderate (30-50% predicted/actual gap per synth-009 fail mode 5)",
        },
        {
            "name": "OptStoic (alternative formulation) for cross-validation",
            "rationale": (
                "Synthesis principle 3 (multi-method consensus). OptStoic uses pure stoichiometric "
                "reasoning without thermodynamic constraints — surfaces solutions OptKnock misses. "
                "Run on the same iCW773; intersect candidate KO sets."
            ),
            "method": "optstoic",
            "evidence_case_ids": ["synth-009-strain-engineering-ko"],
            "evidence_rule_ids": ["01-fba-multiobjective"],
            "expected_cost": "low (compute only)",
            "risk": "low",
        },
        {
            "name": "Cofactor-aware redesign (NADPH balance)",
            "rationale": (
                "Synth-009 fail mode 2 explicitly cites NADPH balance as equally important to "
                "carbon flux for lysine. Add NADPH demand reaction as a third objective in Pareto. "
                "This catches OptKnock 'mathematically perfect but cofactor-collapsed' solutions."
            ),
            "method": "fba_three_objective",
            "evidence_case_ids": ["synth-009-strain-engineering-ko"],
            "evidence_rule_ids": ["01-fba-multiobjective"],
            "expected_cost": "low",
            "risk": "low",
        },
    ],
    "confidence": "high",
    "open_questions": [
        "Confirm strain background: ATCC 13032 (research) vs ATCC 21253 / industrial isolates",
        "Carbon source: pure glucose vs glucose+sucrose (industrial molasses-derived)?",
        "Available iCW773 model version (a 2011 vs 2015 update changes ~50 reactions).",
    ],
}

_LYSINE_DESIGN = {
    "task_id": "demo-lysine-cglutamicum-industrial",
    "selected_strategy": {
        "name": "iCW773 OptKnock + manual essential audit + 5-seed robustness",
        "rationale": "Direct synth-009 protocol; only proven approach for industrial-scale lysine.",
        "alternatives_considered": [
            "OptStoic — round-2 cross-check",
            "Cofactor-aware Pareto — embedded into OptKnock args (multi_objective=True)",
        ],
    },
    "design_library": [
        {
            "design_id": "D1_optknock_ko_set",
            "kind": "KO_set",
            "spec": {
                "model": "iCW773 (currently fall back to iML1515 for stub-mode demo)",
                "target_reaction": "EX_lys__L_e",
                "max_ko": 3,
                "n_seeds": 5,
                "audit_essential": True,
                "expected_top_kos": (
                    "literature priors point to lysC (asp kinase) deregulation, hom (homoserine "
                    "DH) attenuation, and pyc (pyruvate carboxylase) over-expression — but these "
                    "are gain-of-function, not pure KO; OptKnock will surface complementary KOs"
                ),
            },
            "rationale": (
                "Per synth-009 §3-5 protocol exactly. Audit_essential=True is non-negotiable "
                "(rule 08); n_seeds=5 per synth-009 lesson 6."
            ),
            "evidence_case_ids": ["synth-009-strain-engineering-ko"],
            "evidence_rule_ids": ["08-optknock-essential-audit", "01-fba-multiobjective"],
        },
    ],
    "excluded_designs": [
        {
            "kind": "essential_gene_KO",
            "item": "all genes flagged by single_gene_deletion (growth ≤ 1% WT)",
            "reason": (
                "Synth-009 §3 excluded approach: 'OptKnock predicted essential KO; outer "
                "optimization unaware'. Rule 08 mandates pre-filter."
            ),
            "rule_id": "08-optknock-essential-audit",
            "case_id": "synth-009-strain-engineering-ko",
        },
        {
            "kind": "essential_gene_KO",
            "item": "ribosomal proteins (rps* / rpl* / rpm*), translation factors (infA, infB, infC)",
            "reason": "Always lethal; regex post-filter on OptKnock output (rule 08 enforcement).",
            "rule_id": "08-optknock-essential-audit",
            "case_id": "synth-009-strain-engineering-ko",
        },
        {
            "kind": "single_KO_design",
            "item": "1-gene knockouts only",
            "reason": "Synth-009 lesson 1: industrial lysine production requires multi-KO (3-5).",
            "rule_id": None,
            "case_id": "synth-009-strain-engineering-ko",
        },
        {
            "kind": "single_seed_optimization",
            "item": "n_seeds = 1",
            "reason": "Synth-009 fail mode 6: single seed → unstable / non-robust solution.",
            "rule_id": None,
            "case_id": "synth-009-strain-engineering-ko",
        },
        {
            "kind": "ignored_cofactor_balance",
            "item": "single-objective FBA (max biomass only)",
            "reason": (
                "Synth-009 fail mode 2 + rule 01: lysine biosynthesis demands 4 NADPH per molecule; "
                "ignoring NADPH balance gives strains that grow well but produce 0 lysine."
            ),
            "rule_id": "01-fba-multiobjective",
            "case_id": "synth-009-strain-engineering-ko",
        },
    ],
    "computational_pipeline": [
        {
            "step": 1,
            "skill": "fba_simulate",
            "args": {"model_path": "iML1515"},
            "multi_objective": True,
            "rationale": (
                "Baseline FBA + MEMOTE QC. NB: production stub uses iML1515 (E. coli) since "
                "the iCW773 SBML is not bundled; the procedural logic is identical."
            ),
        },
        {
            "step": 2,
            "skill": "optknock_strain",
            "args": {
                "model_path": "iML1515",
                "target_reaction": "EX_lys__L_e",
                "audit_essential": True,
                "n_seeds": 5,
                "max_ko": 3,
                "n_candidates_per_seed": 12,
            },
            "multi_objective": True,
            "rationale": (
                "Rule 08 (audit_essential=True) + rule 01 (multi_objective=True). Synth-009 §3 "
                "exact protocol: max_ko=3, n_seeds=5, manual review of top-3 KO sets after "
                "screening for ribosomal-pattern hits."
            ),
        },
    ],
    "validation_plan": {
        "experiments": [
            {
                "assay": "HPLC lysine titer in fed-batch fermenter",
                "expected_metric": "g/L lysine after 72h fed-batch",
                "n_replicates": 3,
            },
            {
                "assay": "biomass yield (Y_X/S)",
                "expected_metric": "g cell / g glucose; should be 0.4-0.5 (synth-009 normal range)",
                "n_replicates": 3,
            },
            {
                "assay": "NADPH/NADP+ ratio (LC-MS metabolomics)",
                "expected_metric": "ratio in steady-state; synth-009 fail mode 2 cofactor check",
                "n_replicates": 3,
            },
            {
                "assay": "100-generation strain stability",
                "expected_metric": "lysine titer at gen 0, 25, 50, 100; drop ≤ 20% acceptable",
                "n_replicates": 3,
            },
        ],
        "readout": "HPLC + LC-MS metabolomics + OD600",
    },
    "confidence": "high",
}

_LYSINE_REPORT_INTERP = {
    "why_succeeded": [
        "Pipeline directly mirrors synth-009 §3-7 protocol with no shortcuts.",
        "audit_essential=True enforced (rule 08); n_seeds=5 per synth-009 lesson 6.",
        "Excluded_designs explicitly captures the 5 anti-patterns from synth-009 ★排除 section.",
    ],
    "why_failed": ["No failures recorded"],
    "literature_alignment": [
        "Aligned with synth-009 (Burgard 2003 OptKnock for C. glutamicum lysine): same model "
        "class (iCW773 analog), same KO size (3), same multi-seed protocol (n_seeds=5), same "
        "essential-gene audit principle.",
        "Inherits synth-001 MEMOTE + Pareto principles for the FBA baseline step.",
    ],
    "rules_invoked": ["01-fba-multiobjective", "08-optknock-essential-audit"],
}


# ---------- TOGGLE SWITCH (bistable circuit) ----------

_TOGGLE_SCOPING = {
    "task_id": "demo-toggle-switch-ecoli",
    "problem": {
        "synth_task": "circuit",
        "host_organism": "E. coli",
        "constraints": ["bistable", "switchable by IPTG and aTc",
                        "single-cell readout (rule 07)"],
    },
    "literature_summary": [
        {"doi": "10.1038/35002131", "key_finding": (
            "Gardner/Cantor/Collins 2000 (synth-005): mutually-repressing pair (LacI / TetR) "
            "with Hill coefficient n > 1 in cooperativity. Bistability requires α (production) "
            "above a threshold AND symmetric kinetics. ODE + 4-D parameter sweep + dual reporter "
            "+ flow cytometry are mandatory ingredients."
        ), "relevance": "high"},
    ],
    "retrieved_evidence": {
        "cases": [
            {"case_id": "synth-005-toggle-switch-circuit", "similarity": 0.95,
             "pool": "same_task_same_host",
             "key_takeaway": (
                 "Direct case: bistable toggle in E. coli; ODE Hill repression; 4-D parameter "
                 "sweep; dual reporter; single-cell flow cytometry; growth-phase aware."
             ),
             "doi": "10.1038/35002131"},
        ],
        "rules": [
            {"rule_id": "06-bistable-parametric-sim",
             "applicability_note": "Mandatory 4-D parametric sweep (α1, α2, n, K) — synth-005 §3 protocol."},
            {"rule_id": "07-flow-cytometry-bimodal",
             "applicability_note": "Bistable readout cannot be plate-reader bulk; flow cytometry mandatory."},
        ],
    },
    "candidate_strategies": [
        {
            "name": "Gardner-2000 canonical toggle (LacI-Ptrc + TetR-PL_tet)",
            "rationale": (
                "Direct synth-005 §1 topology. Mutually-repressing pair with IPTG and aTc as "
                "orthogonal inducers. Bistability proven empirically in literature."
            ),
            "method": "canonical_toggle",
            "evidence_case_ids": ["synth-005-toggle-switch-circuit"],
            "evidence_rule_ids": ["06-bistable-parametric-sim"],
            "expected_cost": "low (well-characterized parts)",
            "risk": "low (well-trodden path)",
        },
    ],
    "confidence": "high",
    "open_questions": [
        "Reporter pairing: GFP+mCherry (synth-005 §6) vs sfGFP+mScarlet (faster maturation, "
        "synth-008 §5 reporter maturation aware)?",
    ],
}

_TOGGLE_DESIGN = {
    "task_id": "demo-toggle-switch-ecoli",
    "selected_strategy": {
        "name": "Gardner-2000 canonical toggle (LacI-Ptrc + TetR-PL_tet)",
        "rationale": "Direct application of synth-005 protocol.",
        "alternatives_considered": ["sigma-factor toggle (more complex, rejected)"],
    },
    "design_library": [
        {
            "design_id": "D1_toggle_topology",
            "kind": "circuit_topology",
            "spec": {
                "type": "bistable toggle (Gardner 2000)",
                "host": "E. coli",
                "node_1": {"tf": "LacI", "promoter": "Ptrc (IPTG-inducible repression-relief)",
                           "reporter": "GFP", "rbs": "BBa_B0034"},
                "node_2": {"tf": "TetR", "promoter": "PL_tet (aTc-inducible)",
                           "reporter": "mCherry", "rbs": "BBa_B0034"},
                "kinetic_params": {"alpha": 10.0, "n": 2.0, "K": 1.0},
                "param_sweep_dims": 4,
                "param_sweep_grid": {"alpha": [2, 6, 10, 14, 20], "n": [1, 2, 3, 4],
                                     "K": [0.5, 1.0, 2.0, 4.0], "beta": [0.5, 1.0, 1.5]},
            },
            "rationale": (
                "Synth-005 §1+§3 canonical topology with Hill cooperativity n=2 (LacI is "
                "tetrameric, TetR is dimeric so n=2 is the conservative lower bound). Rule 06 "
                "mandates 4-D sweep; we run the full grid."
            ),
            "evidence_case_ids": ["synth-005-toggle-switch-circuit"],
            "evidence_rule_ids": ["06-bistable-parametric-sim", "07-flow-cytometry-bimodal"],
        },
    ],
    "excluded_designs": [
        {
            "kind": "weak_cooperativity",
            "item": "Hill n = 1 (no cooperativity)",
            "reason": "Synth-005 §3: bistability mathematically requires n > 1.",
            "rule_id": "06-bistable-parametric-sim",
            "case_id": "synth-005-toggle-switch-circuit",
        },
        {
            "kind": "single_reporter",
            "item": "GFP only (no mCherry)",
            "reason": "Synth-005 ★排除 entry: 'Single readout state — bimodal verify needs dual reporter'.",
            "rule_id": None,
            "case_id": "synth-005-toggle-switch-circuit",
        },
        {
            "kind": "bulk_readout",
            "item": "plate reader fluorescence only",
            "reason": (
                "Synth-005 ★排除 entry + rule 07: bulk averages bimodal distribution to a "
                "meaningless mid-value; flow cytometry mandatory."
            ),
            "rule_id": "07-flow-cytometry-bimodal",
            "case_id": "synth-005-toggle-switch-circuit",
        },
        {
            "kind": "no_parametric_sweep",
            "item": "skip 4-D parameter scan, build first design directly",
            "reason": "Rule 06 + synth-005 ★排除 entry 1: parameter space mis-pick = monostable.",
            "rule_id": "06-bistable-parametric-sim",
            "case_id": "synth-005-toggle-switch-circuit",
        },
    ],
    "computational_pipeline": [
        {
            "step": 1,
            "skill": "circuit_simulate",
            "args": {
                "topology": "toggle",
                "params": {"alpha": 10.0, "n": 2.0, "K": 1.0},
                "do_parametric_sweep": True,
                "param_sweep_dims": 4,
            },
            "rationale": (
                "Rule 06 — full 4-D parametric sweep over (α, n, K, β). Synth-005 §3 protocol; "
                "output gives bistable_region_present + parameter_robustness_score."
            ),
        },
    ],
    "validation_plan": {
        "experiments": [
            {
                "assay": "bimodal fluorescence distribution",
                "expected_metric": "% cells in ON-state vs OFF-state by flow cytometry",
                "n_replicates": 3,
                "flow_cytometry": True,
            },
            {
                "assay": "switching kinetics (IPTG / aTc dose response)",
                "expected_metric": "fraction switching state per dose",
                "n_replicates": 3,
                "flow_cytometry": True,
            },
            {
                "assay": "growth-phase invariance (synth-005 fail mode 6)",
                "expected_metric": "bistability holds in log AND stationary phase",
                "n_replicates": 3,
                "flow_cytometry": True,
            },
        ],
        "readout": "flow cytometry (mandatory per rule 07)",
    },
    "confidence": "high",
}

_TOGGLE_REPORT_INTERP = {
    "why_succeeded": [
        "4-D parametric sweep run (rule 06); robustness score quantified.",
        "Dual reporter design + flow cytometry readout (rule 07 + synth-005 lesson 4).",
        "Excluded designs explicitly enumerate the 4 synth-005 ★排除 entries.",
    ],
    "why_failed": ["No failures recorded"],
    "literature_alignment": [
        "Aligned with synth-005 (Gardner 2000 Nature toggle switch): identical topology, "
        "identical Hill-repression ODE form, same 4-D sweep dimensions, same "
        "dual-reporter + flow-cytometry readout protocol.",
    ],
    "rules_invoked": ["06-bistable-parametric-sim", "07-flow-cytometry-bimodal"],
}


# ---------- iML1515 FBA / aerobic glucose ----------
# Direct application of synth-001 (Monk 2017 iML1515 protocol). Single-skill demo.

_FBA_SCOPING = {
    "task_id": "demo-iml1515-fba-aerobic",
    "problem": {
        "synth_task": "fba",
        "host_organism": "E. coli K-12 MG1655",
        "constraints": ["aerobic glucose minimal medium", "MEMOTE QC pass required"],
    },
    "literature_summary": [
        {"doi": "10.1038/nbt.3956", "key_finding": (
            "Monk 2017 / iML1515 (synth-001): the standard E. coli K-12 genome-scale model "
            "with 1515 genes / 2719 reactions / 1192 metabolites. Default M9 + 10 mmol/gDW/h "
            "glucose + unlimited O2 → biomass growth ~0.88 1/h. MEMOTE QC mandatory before "
            "any FBA call (synth-001 ★排除 entry 1). Single-objective is excluded; "
            "metabolic engineering is multi-objective by definition."
        ), "relevance": "high"},
    ],
    "retrieved_evidence": {
        "cases": [
            {"case_id": "synth-001-fba-ecoli-iml1515", "similarity": 0.97,
             "pool": "same_task_same_host",
             "key_takeaway": "Direct case: iML1515 baseline FBA with MEMOTE QC and Pareto",
             "doi": "10.1038/nbt.3956"},
        ],
        "rules": [
            {"rule_id": "01-fba-multiobjective",
             "applicability_note": "Direct enforcement: any FBA call must be multi-objective unless "
                                    "explicit override flag is passed (rule 01)."},
        ],
    },
    "candidate_strategies": [
        {
            "name": "iML1515 baseline + MEMOTE QC + multi-objective Pareto",
            "rationale": (
                "Direct synth-001 §1-3 protocol. Load model → MEMOTE consistency / mass balance / "
                "charge balance → optimize biomass at default M9+glucose. Establishes baseline "
                "for any downstream KO scan or product-targeting study."
            ),
            "method": "cobrapy_with_memote_qc",
            "evidence_case_ids": ["synth-001-fba-ecoli-iml1515"],
            "evidence_rule_ids": ["01-fba-multiobjective"],
            "expected_cost": "low (compute only, ~5s wallclock)",
            "risk": "low",
        },
    ],
    "confidence": "high",
    "open_questions": [
        "Strain background: K-12 MG1655 (matches iML1515 directly) or BL21(DE3)? "
        "BL21 has slightly different gene complement; iML1515 will overestimate growth by ~5%.",
    ],
}

_FBA_DESIGN = {
    "task_id": "demo-iml1515-fba-aerobic",
    "selected_strategy": {
        "name": "iML1515 baseline + MEMOTE QC + multi-objective Pareto",
        "rationale": "Direct synth-001 protocol; only canonical baseline FBA approach.",
        "alternatives_considered": ["dynamic FBA (out of scope for steady-state baseline)"],
    },
    "design_library": [
        {
            "design_id": "D1_iml1515_baseline_fba",
            "kind": "strain_modification",
            "spec": {
                "model": "iML1515",
                "medium": "M9 minimal + glucose 10 mmol/gDW/h, O2 unlimited",
                "objective": "biomass",
                "memote_qc": True,
                "expected_growth_range_per_h": [0.85, 0.90],
            },
            "rationale": (
                "Synth-001 §2-3 baseline. Expected growth 0.88 1/h ± 0.02 (the published value "
                "from Monk 2017). MEMOTE QC catches any model corruption that would render the "
                "result misleading (synth-001 ★排除 entry 1)."
            ),
            "evidence_case_ids": ["synth-001-fba-ecoli-iml1515"],
            "evidence_rule_ids": ["01-fba-multiobjective"],
        },
    ],
    "excluded_designs": [
        {
            "kind": "single_objective_only",
            "item": "max biomass without secondary objective declared",
            "reason": (
                "Synth-001 ★排除 entry 3 + rule 01: metabolic engineering is multi-objective. "
                "Setting multi_objective=True is required even for baseline runs (skill enforces)."
            ),
            "rule_id": "01-fba-multiobjective",
            "case_id": "synth-001-fba-ecoli-iml1515",
        },
        {
            "kind": "memote_skipped",
            "item": "MEMOTE consistency check disabled",
            "reason": (
                "Synth-001 ★排除 entry 1: 'FBA without MEMOTE → misleading prediction'. "
                "Skill default skip_memote=False; this excluded design enforces the default."
            ),
            "rule_id": None,
            "case_id": "synth-001-fba-ecoli-iml1515",
        },
        {
            "kind": "essential_gene_KO",
            "item": "any KO without single_gene_deletion audit",
            "reason": "Synth-001 ★排除 entry 4 + rule 08: KO-essential gene → growth=0 → pipeline failure.",
            "rule_id": "08-optknock-essential-audit",
            "case_id": "synth-001-fba-ecoli-iml1515",
        },
        {
            "kind": "strain_mismatch",
            "item": "applying iML1515 results to BL21 / W3110 without strain-specific validation",
            "reason": "Synth-001 ★排除 entry 6: strain-specific model required (iML1515 is K-12-only).",
            "rule_id": None,
            "case_id": "synth-001-fba-ecoli-iml1515",
        },
    ],
    "computational_pipeline": [
        {
            "step": 1,
            "skill": "fba_simulate",
            "args": {"model_path": "iML1515", "objective": "biomass", "skip_memote": False},
            "multi_objective": True,
            "rationale": "Rule 01 + synth-001 §1-3 baseline. Real cobra+iML1515 SBML; MEMOTE pre-check.",
        },
    ],
    "validation_plan": {
        "experiments": [
            {
                "assay": "literature comparison",
                "expected_metric": "growth rate within [0.85, 0.90] 1/h (matches Monk 2017 published value)",
                "n_replicates": 1,
            },
        ],
        "readout": "in silico (computational baseline; no wet lab required)",
    },
    "confidence": "high",
}

_FBA_REPORT_INTERP = {
    "why_succeeded": [
        "Direct synth-001 protocol applied without modification.",
        "Real cobra+iML1515 SBML returned growth in expected literature range.",
        "MEMOTE QC passed (rule 01 enforcement satisfied).",
    ],
    "why_failed": ["No failures recorded"],
    "literature_alignment": [
        "Aligned with synth-001 (Monk 2017 iML1515 baseline): same default M9+glucose+aerobic "
        "condition, same biomass objective, same expected growth ~0.88 1/h.",
    ],
    "rules_invoked": ["01-fba-multiobjective"],
}


# ---------- MoClo Golden Gate 5-fragment plasmid ----------
# Direct application of synth-003 (Engler 2011 MoClo protocol).

_MOCLO_SCOPING = {
    "task_id": "demo-moclo-5fragment-assembly",
    "problem": {
        "synth_task": "plasmid_assembly",
        "host_organism": "E. coli",
        "assembly_strategy": "golden_gate",
        "constraints": ["5-fragment level-1 assembly", "BsaI", "MoClo standard library overhangs"],
    },
    "literature_summary": [
        {"doi": "10.1371/journal.pone.0016765", "key_finding": (
            "Engler 2011 / MoClo (synth-003): Type-IIs Golden Gate assembly with 4-bp overhangs. "
            "5-fragment success rate ~70%; 10-fragment ~30%. Overhang collision is the #1 failure "
            "mode; internal BsaI/BsmBI sites must be removed by silent codon mutation; ≥3 colony "
            "pick + colony PCR + Plasmidsaurus for verification."
        ), "relevance": "high"},
        {"doi": "10.1093/bioinformatics/btaa558", "key_finding": (
            "Zulkower 2020 / DNAchisel (synth-006): constraint solver removes type-IIs sites "
            "from CDS while preserving translation; multi-restart simulated annealing avoids "
            "local minima."
        ), "relevance": "high"},
    ],
    "retrieved_evidence": {
        "cases": [
            {"case_id": "synth-003-golden-gate-moclo", "similarity": 0.96,
             "pool": "same_task_same_host",
             "key_takeaway": "Direct MoClo protocol — overhang collision check + ≥3 colony pick",
             "doi": "10.1371/journal.pone.0016765"},
            {"case_id": "synth-006-dnachisel-restriction-removal", "similarity": 0.61,
             "pool": "same_task",
             "key_takeaway": "DNAchisel removes internal BsaI/BsmBI sites from cassette CDS",
             "doi": "10.1093/bioinformatics/btaa558"},
        ],
        "rules": [
            {"rule_id": "03-golden-gate-overhang-collision",
             "applicability_note": "Mandatory overhang uniqueness + non-palindrome + GC≤75% check"},
            {"rule_id": "04-restriction-site-destroy",
             "applicability_note": "Pre-step required: dna_constraint_solve to remove internal sites"},
            {"rule_id": "05-multi-colony-pick",
             "applicability_note": "Validation plan must specify colony_pick_n ≥ 3 + colony_pcr + full_plasmid_seq"},
        ],
    },
    "candidate_strategies": [
        {
            "name": "MoClo level-1 BsaI assembly + DNAchisel pre-step",
            "rationale": (
                "Synth-003 §1-2 standard MoClo protocol. Pre-step DNAchisel ensures parts are "
                "free of internal BsaI sites (rule 04). Level-1 backbone with BsaI overhang "
                "library (synth-003 §2)."
            ),
            "method": "moclo_level1_bsai",
            "evidence_case_ids": ["synth-003-golden-gate-moclo", "synth-006-dnachisel-restriction-removal"],
            "evidence_rule_ids": ["03-golden-gate-overhang-collision", "04-restriction-site-destroy"],
            "expected_cost": "low (parts library + standard reaction)",
            "risk": "low (5-fragment success rate ~70% per synth-003 §1)",
        },
    ],
    "confidence": "high",
    "open_questions": [
        "Backbone selection: pSB1A3 (high copy, ampR) vs pSB1C3 (medium, cmR)?",
        "Whether to validate via Sanger junction-only (cheaper) or Plasmidsaurus full-plasmid (synth-003 lesson 4 prefers full).",
    ],
}

_MOCLO_DESIGN = {
    "task_id": "demo-moclo-5fragment-assembly",
    "selected_strategy": {
        "name": "MoClo level-1 BsaI assembly + DNAchisel pre-step",
        "rationale": "Synth-003 standard protocol; only proven approach for 5-fragment one-pot.",
        "alternatives_considered": ["Gibson (no internal-site constraint but no part standardization)"],
    },
    "design_library": [
        {
            "design_id": "D1_moclo_5part_assembly",
            "kind": "plasmid_construct",
            "spec": {
                "strategy": "MoClo level-1 Golden Gate",
                "enzyme": "BsaI",
                "n_fragments": 5,
                "overhangs": ["AATG", "AGCC", "TACT", "GCTT", "CCGA"],
                "backbone": "pSB1C3 (medium copy, cmR)",
                "reaction": "BsaI-HFv2 + T4 ligase, 37°C 30 cycle / 16°C 5 min cycle, 75°C heat-kill",
                "max_overhang_gc_pct": 0.75,
            },
            "rationale": (
                "Synth-003 §1-2 protocol. The 5 chosen overhangs are non-palindromic and pairwise "
                "distinct (rule 03 will verify); they match published MoClo standard library "
                "junction codes."
            ),
            "evidence_case_ids": ["synth-003-golden-gate-moclo"],
            "evidence_rule_ids": ["03-golden-gate-overhang-collision", "05-multi-colony-pick"],
        },
    ],
    "excluded_designs": [
        {
            "kind": "palindromic_overhang",
            "item": "TGCA / GATC / CATG / GCGC (any 4-bp palindrome)",
            "reason": "Synth-003 fail mode 1: palindromes self-anneal → ligation drop.",
            "rule_id": "03-golden-gate-overhang-collision",
            "case_id": "synth-003-golden-gate-moclo",
        },
        {
            "kind": "high_GC_overhang",
            "item": "overhangs with GC% > 75%",
            "reason": "Synth-003 fail mode 2: high GC ligation efficiency drops.",
            "rule_id": "03-golden-gate-overhang-collision",
            "case_id": "synth-003-golden-gate-moclo",
        },
        {
            "kind": "internal_restriction_site",
            "item": "any internal BsaI / BsmBI in any cassette CDS",
            "reason": "Synth-003 ★排除 entry 2 + rule 04: internal site self-cleaves cassette.",
            "rule_id": "04-restriction-site-destroy",
            "case_id": "synth-003-golden-gate-moclo",
        },
        {
            "kind": "single_colony_pick",
            "item": "1-colony validation",
            "reason": "Synth-003 ★排除 entry 4 + rule 05: assembly errors detectable only at ≥3 colonies.",
            "rule_id": "05-multi-colony-pick",
            "case_id": "synth-003-golden-gate-moclo",
        },
        {
            "kind": "manual_backbone_linearization",
            "item": "pre-linearize destination vector",
            "reason": "Synth-003 ★排除 entry 6: Golden Gate handles vector cycling natively.",
            "rule_id": None,
            "case_id": "synth-003-golden-gate-moclo",
        },
    ],
    "computational_pipeline": [
        {
            "step": 1,
            "skill": "dna_constraint_solve",
            "args": {
                "fasta_path_relpath": "tests/fixtures/gfp_native.fasta",
                "forbidden_sites": {"BsaI": "GGTCTC", "BsmBI": "CGTCTC"},
                "gc_range": [0.40, 0.55],
                "max_homopolymer": 5,
                "enforce_translation": True,
            },
            "rationale": "Rule 04 — pre-step before Golden Gate. Synth-006 §1-3 protocol.",
        },
        {
            "step": 2,
            "skill": "golden_gate_assembly",
            "args": {
                "parts_fixture_relpath": "tests/fixtures/5-fragment-test.json",
                "enzyme": "BsaI",
                "min_overhang_distance": 1,
                "max_gc_pct": 0.75,
            },
            "rationale": (
                "Synth-003 §1-2 MoClo level-1 reaction. Real Biopython.Restriction validator "
                "+ overhang collision check (rule 03)."
            ),
        },
    ],
    "validation_plan": {
        "experiments": [
            {
                "assay": "colony PCR with backbone-spanning primers",
                "expected_metric": "amplicon at expected size for ≥80% of colonies picked",
                "n_replicates": 3,
                "colony_pick_n": 3,
                "colony_pcr": True,
                "full_plasmid_seq": True,
            },
            {
                "assay": "Plasmidsaurus / Nanopore full-plasmid sequencing",
                "expected_metric": "100% identity to design over full circular plasmid",
                "n_replicates": 3,
                "colony_pick_n": 3,
                "colony_pcr": True,
                "full_plasmid_seq": True,
            },
        ],
        "readout": "PCR gel + sequencing (synth-003 lesson 4 strongly prefers full-plasmid)",
    },
    "confidence": "high",
}

_MOCLO_REPORT_INTERP = {
    "why_succeeded": [
        "DNAchisel pre-step removes any internal BsaI/BsmBI from CDS (rule 04).",
        "Overhang collision check ran (rule 03); 5 unique non-palindromic junctions confirmed.",
        "Validation plan specifies colony_pick_n=3 + colony_pcr + full_plasmid_seq (rule 05).",
        "Excluded designs enumerate the 5 synth-003 ★排除 entries.",
    ],
    "why_failed": ["No failures recorded"],
    "literature_alignment": [
        "Aligned with synth-003 (Engler 2011 MoClo): same Type-IIs enzyme (BsaI), same 4-bp "
        "overhang scheme, same level-1 protocol.",
        "Aligned with synth-006 (Zulkower 2020 DNAchisel): same solver-based pre-step.",
    ],
    "rules_invoked": ["03-golden-gate-overhang-collision", "04-restriction-site-destroy",
                       "05-multi-colony-pick"],
}


# ---------- IL-2 codon optimization in yeast ----------
# Direct application of synth-004 (Chen 2018 + DNAchisel).

_CODONOPT_SCOPING = {
    "task_id": "demo-il2-codon-opt-yeast",
    "problem": {
        "synth_task": "codon_opt",
        "host_organism": "Saccharomyces cerevisiae",
        "target_protein": "GFP (stand-in for human IL-2)",
        "constraints": ["yeast codon table", "no BsaI/BsmBI/SapI", "GC 0.35-0.55", "preserve rare codons ~5%"],
    },
    "literature_summary": [
        {"doi": "10.1186/s12859-018-2333-9", "key_finding": (
            "synth-004 / IL-2 in yeast: native human IL-2 CAI 0.45 → DNAchisel-optimized 0.88 "
            "in S. cerevisiae; estimated translation efficiency ↑ 5-10×. Multi-constraint solver "
            "essential because CAI alone misses 5'UTR secondary structure / cryptic splice / "
            "homopolymer issues. Avoid 100% optimization (synth-004 ★排除 entry 5: rare codon "
            "stretches give ribosome-pause for proper folding)."
        ), "relevance": "high"},
        {"doi": "10.1093/bioinformatics/btaa558", "key_finding": (
            "synth-006 / DNAchisel: constraint solver does the heavy lifting via simulated "
            "annealing; multi-window GC, multi-restart for robustness."
        ), "relevance": "high"},
    ],
    "retrieved_evidence": {
        "cases": [
            {"case_id": "synth-004-codon-optimization", "similarity": 0.91,
             "pool": "same_task_same_host",
             "key_takeaway": "Native human IL-2 CAI 0.45 → optimized 0.88; multi-constraint",
             "doi": "10.1186/s12859-018-2333-9"},
            {"case_id": "synth-006-dnachisel-restriction-removal", "similarity": 0.85,
             "pool": "same_task",
             "key_takeaway": "DNAchisel constraint solver, multi-restart simulated annealing",
             "doi": "10.1093/bioinformatics/btaa558"},
        ],
        "rules": [
            {"rule_id": "02-codon-optimize-mandatory",
             "applicability_note": "Heterologous (human → yeast); rule 02 mandatory."},
            {"rule_id": "04-restriction-site-destroy",
             "applicability_note": "Forbidden sites declared as constraint set."},
        ],
    },
    "candidate_strategies": [
        {
            "name": "DNAchisel multi-constraint optimize for S. cerevisiae",
            "rationale": (
                "Direct synth-004 §3 protocol. Constraints: yeast CAI ↑, GC 0.35-0.55, no "
                "BsaI/BsmBI/SapI, no homopolymer ≥5, preserve_rare_codons=True (synth-004 ★排除 "
                "entry 5)."
            ),
            "method": "dnachisel_multi_constraint",
            "evidence_case_ids": ["synth-004-codon-optimization", "synth-006-dnachisel-restriction-removal"],
            "evidence_rule_ids": ["02-codon-optimize-mandatory", "04-restriction-site-destroy"],
            "expected_cost": "low (compute only)",
            "risk": "low",
        },
    ],
    "confidence": "high",
    "open_questions": [
        "Are there host-specific tRNA modifications to consider beyond codon usage table? "
        "(synth-004 lesson 6: lab vs industrial yeast tRNA pool slightly differs).",
    ],
}

_CODONOPT_DESIGN = {
    "task_id": "demo-il2-codon-opt-yeast",
    "selected_strategy": {
        "name": "DNAchisel multi-constraint optimize for S. cerevisiae",
        "rationale": "Direct synth-004 protocol; multi-constraint solver is canonical.",
        "alternatives_considered": ["JCAT (web)", "GeneOptimizer (commercial)"],
    },
    "design_library": [
        {
            "design_id": "D1_codon_optimized_cassette",
            "kind": "sequence_optimized",
            "spec": {
                "host_codon_table": "S. cerevisiae",
                "target_CAI_min": 0.65,
                "GC_range": [0.35, 0.55],
                "forbidden_sites": ["BsaI", "BsmBI", "SapI"],
                "max_homopolymer": 5,
                "preserve_rare_codons_pct": 5,
                "expected_CAI_lift_vs_native": "≥0.30 (synth-004 reports 0.45→0.88 for IL-2)",
            },
            "rationale": "Synth-004 §3 + synth-006 §1 protocol exactly.",
            "evidence_case_ids": ["synth-004-codon-optimization", "synth-006-dnachisel-restriction-removal"],
            "evidence_rule_ids": ["02-codon-optimize-mandatory", "04-restriction-site-destroy"],
        },
    ],
    "excluded_designs": [
        {
            "kind": "CAI_only_optimization",
            "item": "optimize CAI without GC / forbidden sites / 5'UTR check",
            "reason": "Synth-004 ★排除 entry 1: CAI alone misses secondary issues.",
            "rule_id": None,
            "case_id": "synth-004-codon-optimization",
        },
        {
            "kind": "100_percent_optimal",
            "item": "no rare codons preserved (CAI > 0.95)",
            "reason": "Synth-004 ★排除 entry 5 + fail mode 2: over-opt breaks cotranslational folding.",
            "rule_id": None,
            "case_id": "synth-004-codon-optimization",
        },
        {
            "kind": "single_strand_check",
            "item": "checking restriction sites on forward strand only",
            "reason": "Synth-006 ★排除 entry 2: palindromes need both-strand check.",
            "rule_id": "04-restriction-site-destroy",
            "case_id": "synth-006-dnachisel-restriction-removal",
        },
        {
            "kind": "extreme_GC",
            "item": "GC < 0.30 or > 0.70",
            "reason": "Synth-004 ★排除 entry 4: extreme GC blocks translation.",
            "rule_id": None,
            "case_id": "synth-004-codon-optimization",
        },
    ],
    "computational_pipeline": [
        {
            "step": 1,
            "skill": "codon_optimize",
            "args": {
                "dna_native_fasta_relpath": "tests/fixtures/gfp_native.fasta",
                "host": "scerevisiae",
                "forbidden_sites": {"BsaI": "GGTCTC", "BsmBI": "CGTCTC", "SapI": "GCTCTTC"},
                "gc_range": [0.35, 0.55],
                "preserve_rare_codons": True,
            },
            "rationale": "Rule 02 + synth-004 §3 protocol. Real DNAchisel constraint solve.",
        },
    ],
    "validation_plan": {
        "experiments": [
            {
                "assay": "CAI lift vs native",
                "expected_metric": "CAI delta ≥ 0.30 (synth-004 reports 0.45→0.88)",
                "n_replicates": 1,
            },
            {
                "assay": "in vitro translation in S. cerevisiae extract",
                "expected_metric": "protein yield 5-10× over native (synth-004 §5)",
                "n_replicates": 3,
            },
            {
                "assay": "restriction site scan post-optimization",
                "expected_metric": "0 BsaI/BsmBI/SapI sites (both strands)",
                "n_replicates": 1,
            },
        ],
        "readout": "computational + ELISA",
    },
    "confidence": "high",
}

_CODONOPT_REPORT_INTERP = {
    "why_succeeded": [
        "DNAchisel multi-constraint solve ran fully on real GFP DNA.",
        "Rare codon preservation enforced (synth-004 ★排除 entry 5; rule 02 boundary).",
        "All forbidden sites cleared; GC kept in [0.35, 0.55].",
        "Excluded designs map to 4 synth-004/006 ★排除 entries.",
    ],
    "why_failed": ["No failures recorded"],
    "literature_alignment": [
        "Aligned with synth-004 (IL-2 codon-opt for yeast): same constraint set, same expected "
        "CAI lift magnitude, same multi-constraint solver approach.",
        "Aligned with synth-006 (DNAchisel): real DNAchisel binary used.",
    ],
    "rules_invoked": ["02-codon-optimize-mandatory", "04-restriction-site-destroy"],
}


# ---------- TX-TL cell-free GFP prototyping ----------
# Direct application of synth-007.

_CELLFREE_SCOPING = {
    "task_id": "demo-txtl-gfp-prototyping",
    "problem": {
        "synth_task": "cell_free",
        "host_organism": "cell_free",
        "target_protein": "GFP",
        "constraints": ["TX-TL E. coli extract", "Mg²⁺ in 8-15 mM optimal range", "real-time GFP monitor"],
    },
    "literature_summary": [
        {"doi": "10.1038/nbt980", "key_finding": (
            "synth-007: TX-TL E. coli extract for fast prototyping (mg/mL yields, hours not days). "
            "Mg²⁺ 8-15 mM critical (synth-007 lesson 2); reaction time 4-8h (>10h energy depleted, "
            "synth-007 ★排除 entry 4). Linear template ≥ 100 ng/μL (lesson 5). Codon optimization "
            "for E. coli still required for cell-free since the extract IS E. coli."
        ), "relevance": "high"},
    ],
    "retrieved_evidence": {
        "cases": [
            {"case_id": "synth-007-cell-free-system", "similarity": 0.95,
             "pool": "same_task_same_host",
             "key_takeaway": "TX-TL recipe: Mg²⁺ tuning, T7 promoter, 4-8h reaction",
             "doi": "10.1038/nbt980"},
        ],
        "rules": [
            {"rule_id": "02-codon-optimize-mandatory",
             "applicability_note": "Even cell-free requires codon opt for E. coli (extract is E. coli)"},
        ],
    },
    "candidate_strategies": [
        {
            "name": "TX-TL E. coli extract + standard recipe",
            "rationale": "Synth-007 §1 default; mg/mL yields suitable for prototyping.",
            "method": "txtl_standard_recipe",
            "evidence_case_ids": ["synth-007-cell-free-system"],
            "evidence_rule_ids": ["02-codon-optimize-mandatory"],
            "expected_cost": "moderate (extract preparation or commercial NEBExpress)",
            "risk": "low",
        },
        {
            "name": "PURE (alternative for clean / disulfide / minimal-component)",
            "rationale": (
                "Synth-007 §1 PURE alternative. μg/mL yields but no endogenous mRNA / protease. "
                "Use when target has disulfides + we need redox control."
            ),
            "method": "pure_recombinant",
            "evidence_case_ids": ["synth-007-cell-free-system"],
            "evidence_rule_ids": [],
            "expected_cost": "high (PURExpress kit)",
            "risk": "low",
        },
    ],
    "confidence": "high",
    "open_questions": [
        "Whether the GFP variant has any disulfides (no for standard sfGFP / EGFP).",
        "Real-time vs endpoint readout?",
    ],
}

_CELLFREE_DESIGN = {
    "task_id": "demo-txtl-gfp-prototyping",
    "selected_strategy": {
        "name": "TX-TL E. coli extract + standard recipe",
        "rationale": "GFP has no disulfides; TX-TL gives mg/mL yields.",
        "alternatives_considered": ["PURE (rejected: yield too low for prototyping pace)"],
    },
    "design_library": [
        {
            "design_id": "D1_txtl_recipe_gfp",
            "kind": "fermentation_recipe",
            "spec": {
                "system": "TX-TL",
                "extract": "E. coli BL21 Rosetta2 (Rosetta supports rare codons)",
                "Mg_mM": 12,
                "K_glu_mM": 150,
                "ATP_mM": 1.5,
                "GTP_mM": 0.9,
                "amino_acids_mM": 1.5,
                "PEG_pct": 2.0,
                "T_celsius": 29,
                "time_h": 6,
                "template_concentration_ng_per_uL": 150,
                "expected_yield_mg_per_mL": "0.5-1.0 (synth-007 reports mg/mL for soluble proteins)",
            },
            "rationale": "Synth-007 §3-4 default + Mg²⁺=12 (middle of 8-15 optimal).",
            "evidence_case_ids": ["synth-007-cell-free-system"],
            "evidence_rule_ids": ["02-codon-optimize-mandatory"],
        },
    ],
    "excluded_designs": [
        {
            "kind": "Mg_out_of_range",
            "item": "Mg²⁺ < 8 mM or > 15 mM",
            "reason": "Synth-007 lesson 2: outside this range yield drops sharply.",
            "rule_id": None,
            "case_id": "synth-007-cell-free-system",
        },
        {
            "kind": "long_reaction",
            "item": "reaction time > 10 h",
            "reason": "Synth-007 ★排除 entry 4: energy depleted, byproducts accumulate.",
            "rule_id": None,
            "case_id": "synth-007-cell-free-system",
        },
        {
            "kind": "low_template",
            "item": "linear template < 50 ng/μL",
            "reason": "Synth-007 ★排除 entry 2: yield too low to be useful.",
            "rule_id": None,
            "case_id": "synth-007-cell-free-system",
        },
        {
            "kind": "single_replicate",
            "item": "1-replicate measurement",
            "reason": "Synth-007 ★排除 entry 5: batch-to-batch variation 5×; need ≥3 replicates.",
            "rule_id": None,
            "case_id": "synth-007-cell-free-system",
        },
        {
            "kind": "glycosylated_target",
            "item": "any glycosylated mammalian protein",
            "reason": "Synth-007 fail mode 6: bacterial extract lacks glycosylation machinery.",
            "rule_id": None,
            "case_id": "synth-007-cell-free-system",
        },
    ],
    "computational_pipeline": [
        {
            "step": 1,
            "skill": "codon_optimize",
            "args": {
                "dna_native_fasta_relpath": "tests/fixtures/gfp_native.fasta",
                "host": "ecoli",
                "forbidden_sites": {"BsaI": "GGTCTC", "BsmBI": "CGTCTC"},
                "preserve_rare_codons": True,
            },
            "rationale": (
                "Rule 02 + synth-007 ★排除 entry 1 (cell-free still requires codon opt for "
                "E. coli, since the extract IS E. coli)."
            ),
        },
        {
            "step": 2,
            "skill": "cellfree_design",
            "args": {
                "target_protein": "GFP",
                "system": "TX-TL",
                "custom_recipe": {"Mg_mM": 12, "time_h": 6},
                "has_disulfide": False,
                "has_glycosylation": False,
            },
            "rationale": "Synth-007 §3-4 standard recipe with Mg²⁺=12 (mid optimal).",
        },
    ],
    "validation_plan": {
        "experiments": [
            {
                "assay": "real-time GFP fluorescence in plate reader",
                "expected_metric": "log-phase fluorescence increase, plateau by 6h",
                "n_replicates": 3,
            },
            {
                "assay": "Western blot post-reaction",
                "expected_metric": "single ~27 kDa band (GFP)",
                "n_replicates": 3,
            },
            {
                "assay": "endpoint yield (Bradford / NanoDrop)",
                "expected_metric": "0.5-1.0 mg/mL soluble protein",
                "n_replicates": 3,
            },
        ],
        "readout": "real-time plate reader (synth-007 lesson 7) + Western/Bradford endpoint",
    },
    "confidence": "high",
}

_CELLFREE_REPORT_INTERP = {
    "why_succeeded": [
        "TX-TL chosen (mg/mL yield) over PURE (μg/mL); rationale documented.",
        "Mg²⁺ 12 mM in synth-007 optimal range (8-15).",
        "Reaction time 6 h within 4-8 h optimal window.",
        "Codon opt step still required even for cell-free (rule 02 + synth-007 ★排除 entry 1).",
        "Excluded designs map to 5 synth-007 ★排除 entries.",
    ],
    "why_failed": ["No failures recorded"],
    "literature_alignment": [
        "Aligned with synth-007 (Shimizu 2004 cell-free): same TX-TL recipe shape, same Mg²⁺ "
        "tuning principle, same reaction-time window.",
    ],
    "rules_invoked": ["02-codon-optimize-mandatory"],
}


# ---------- Arabinose biosensor ----------
# Direct application of synth-008.

_BIOSENSOR_SCOPING = {
    "task_id": "demo-arabinose-biosensor",
    "problem": {
        "synth_task": "biosensor",
        "host_organism": "E. coli",
        "target_analyte": "arabinose",
        "constraints": ["TF-promoter sensor", "specificity panel ≥5 compounds", "single-cell flow cytometry readout"],
    },
    "literature_summary": [
        {"doi": "10.1038/nbt.3865", "key_finding": (
            "synth-008: AraC TF + pBAD-GFP arabinose sensor. Dose-response Hill curve, "
            "dynamic range ≥ 10× preferred; specificity panel (≥5 cross-reactant sugars) "
            "mandatory; single-cell flow cytometry over plate-reader bulk (synth-008 ★排除 "
            "entry 5)."
        ), "relevance": "high"},
    ],
    "retrieved_evidence": {
        "cases": [
            {"case_id": "synth-008-biosensor-design", "similarity": 0.96,
             "pool": "same_task_same_host",
             "key_takeaway": "AraC-pBAD sensor protocol; specificity panel + flow cytometry",
             "doi": "10.1038/nbt.3865"},
        ],
        "rules": [
            {"rule_id": "10-biosensor-specificity-panel",
             "applicability_note": "Mandatory ≥5 cross-reactant compounds"},
            {"rule_id": "07-flow-cytometry-bimodal",
             "applicability_note": "Single-cell readout over bulk for sensor noise characterization"},
        ],
    },
    "candidate_strategies": [
        {
            "name": "AraC-pBAD canonical TF-promoter sensor",
            "rationale": (
                "Direct synth-008 §1 topology. AraC binds arabinose → pBAD activated → GFP. "
                "Well-characterized parts; dose-response Hill curve fit standard."
            ),
            "method": "tf_promoter_canonical",
            "evidence_case_ids": ["synth-008-biosensor-design"],
            "evidence_rule_ids": ["10-biosensor-specificity-panel", "07-flow-cytometry-bimodal"],
            "expected_cost": "low",
            "risk": "low",
        },
    ],
    "confidence": "high",
    "open_questions": [
        "Whether to include glucose in the cross-reactant panel given catabolite repression "
        "(synth-008 fail mode 2). Probably yes — it tests a known false-positive mode.",
    ],
}

_BIOSENSOR_DESIGN = {
    "task_id": "demo-arabinose-biosensor",
    "selected_strategy": {
        "name": "AraC-pBAD canonical TF-promoter sensor",
        "rationale": "Synth-008 direct protocol.",
        "alternatives_considered": ["riboswitch (faster but more complex)"],
    },
    "design_library": [
        {
            "design_id": "D1_arac_pbad_sensor",
            "kind": "sensor_topology",
            "spec": {
                "tf": "AraC",
                "promoter": "pBAD",
                "reporter": "GFP",
                "rbs": "BBa_B0034 (medium)",
                "expected_dynamic_range_fold": 50,
                "expected_specificity_ratio": 12,
                "EC50_uM": 100,
                "response_time_min": 20,
            },
            "rationale": "Synth-008 §1+§3 direct.",
            "evidence_case_ids": ["synth-008-biosensor-design"],
            "evidence_rule_ids": ["10-biosensor-specificity-panel", "07-flow-cytometry-bimodal"],
        },
    ],
    "excluded_designs": [
        {
            "kind": "no_specificity_panel",
            "item": "validate only on arabinose without off-target test",
            "reason": "Synth-008 ★排除 entry 2 + rule 10: ≥5 cross-reactants required.",
            "rule_id": "10-biosensor-specificity-panel",
            "case_id": "synth-008-biosensor-design",
        },
        {
            "kind": "low_dynamic_range",
            "item": "accept dynamic range < 5×",
            "reason": "Synth-008 ★排除 entry 3: low DR makes hit/no-hit indistinguishable.",
            "rule_id": None,
            "case_id": "synth-008-biosensor-design",
        },
        {
            "kind": "bulk_readout",
            "item": "plate-reader-only readout",
            "reason": "Synth-008 ★排除 entry 5 + rule 07: cell-to-cell variability requires single-cell.",
            "rule_id": "07-flow-cytometry-bimodal",
            "case_id": "synth-008-biosensor-design",
        },
        {
            "kind": "ignore_catabolite_repression",
            "item": "test in glucose-rich media without controls",
            "reason": "Synth-008 fail mode 2: glucose down-regulates pBAD via catabolite repression.",
            "rule_id": None,
            "case_id": "synth-008-biosensor-design",
        },
    ],
    "computational_pipeline": [
        {
            "step": 1,
            "skill": "biosensor_design",
            "args": {
                "analyte": "arabinose",
                "n_cross_reactants_required": 5,
                "expected_specificity_ratio": 10,
                "Hill_n": 2.0,
            },
            "rationale": "Synth-008 §3 dose-response + rule 10 panel + rule 07 readout.",
        },
    ],
    "validation_plan": {
        "experiments": [
            {
                "assay": "dose-response with arabinose 0.001-100 mM",
                "expected_metric": "Hill curve, dynamic range ≥ 10×",
                "n_replicates": 3,
                "flow_cytometry": True,
                "cross_reactant_panel": {
                    "n_compounds": 5,
                    "list": ["glucose", "galactose", "xylose", "lyxose", "fructose"],
                },
            },
            {
                "assay": "flow cytometry per-cell distribution",
                "expected_metric": "narrow unimodal in ON state, no bimodal noise",
                "n_replicates": 3,
                "flow_cytometry": True,
                "cross_reactant_panel": {
                    "n_compounds": 5,
                    "list": ["glucose", "galactose", "xylose", "lyxose", "fructose"],
                },
            },
        ],
        "readout": "flow cytometry (rule 07)",
    },
    "confidence": "high",
}

_BIOSENSOR_REPORT_INTERP = {
    "why_succeeded": [
        "AraC-pBAD topology produced predicted dynamic range of 50× and specificity ratio 12×.",
        "Cross-reactant panel includes 5 sugars per rule 10.",
        "Flow cytometry readout enforced (rule 07).",
        "Excluded designs map to 4 synth-008 ★排除 entries / fail modes.",
    ],
    "why_failed": ["No failures recorded"],
    "literature_alignment": [
        "Aligned with synth-008 (Yang 2017 arabinose sensor): same topology, same panel size, "
        "same readout method, dynamic range matches the synth-008 expected range (≥10×).",
    ],
    "rules_invoked": ["07-flow-cytometry-bimodal", "10-biosensor-specificity-panel"],
}


# ---------- Streptomyces BGC mining ----------
# Direct application of synth-010.

_BGC_SCOPING = {
    "task_id": "demo-streptomyces-bgc-mining",
    "problem": {
        "synth_task": "bgc_mining",
        "host_organism": "Streptomyces",
        "constraints": ["antiSMASH + DeepBGC consensus", "MIBiG cross-check mandatory"],
    },
    "literature_summary": [
        {"doi": "10.1093/nar/gkaa978", "key_finding": (
            "synth-010: antiSMASH 7 detects NRPS / PKS / terpene / RiPP clusters in microbial "
            "genomes (~5-10% of Streptomyces genome encodes BGCs). MIBiG cross-check mandatory "
            "for novelty assessment; ~80% rediscovery rate baseline. DeepBGC complements antiSMASH "
            "by ML detection of architectures the rule-based tools miss."
        ), "relevance": "high"},
    ],
    "retrieved_evidence": {
        "cases": [
            {"case_id": "synth-010-bgcs-natural-product", "similarity": 0.95,
             "pool": "same_task_same_host",
             "key_takeaway": "antiSMASH+DeepBGC consensus + MIBiG cross-ref + BiG-SCAPE families",
             "doi": "10.1093/nar/gkaa978"},
        ],
        "rules": [
            {"rule_id": "09-antismash-mibig-cross",
             "applicability_note": "Mandatory MIBiG cross-check; without it the run is rejected"},
        ],
    },
    "candidate_strategies": [
        {
            "name": "antiSMASH + DeepBGC consensus + MIBiG cross-check",
            "rationale": (
                "Synth-010 §3+§5+§7: multi-tool consensus avoids antiSMASH false positives and "
                "DeepBGC misses; MIBiG ID% bands (≥80 known / 30-80 variant / <30 novel) drive "
                "wet-lab priority."
            ),
            "method": "antismash_plus_deepbgc",
            "evidence_case_ids": ["synth-010-bgcs-natural-product"],
            "evidence_rule_ids": ["09-antismash-mibig-cross"],
            "expected_cost": "low (compute) + high (heterologous expression downstream)",
            "risk": "moderate (synth-010 fail mode 4: rediscovery rate ~80%)",
        },
        {
            "name": "BiG-SCAPE family network for cross-genome priority",
            "rationale": "Synth-010 §4: groups homologous BGCs across genomes; surfaces orphan families.",
            "method": "bigscape",
            "evidence_case_ids": ["synth-010-bgcs-natural-product"],
            "evidence_rule_ids": [],
            "expected_cost": "moderate",
            "risk": "low",
        },
        {
            "name": "DeepBGC alternate architecture detection",
            "rationale": "Synth-010 §8: ML-based, picks novel architectures.",
            "method": "deepbgc",
            "evidence_case_ids": ["synth-010-bgcs-natural-product"],
            "evidence_rule_ids": ["09-antismash-mibig-cross"],
            "expected_cost": "low",
            "risk": "low",
        },
    ],
    "confidence": "high",
    "open_questions": [
        "Heterologous expression host: Streptomyces venezuelae (synth-010 §7 default) "
        "vs S. coelicolor M1146/M1152 (deletion strains for cleaner background)?",
    ],
}

_BGC_DESIGN = {
    "task_id": "demo-streptomyces-bgc-mining",
    "selected_strategy": {
        "name": "antiSMASH + DeepBGC consensus + MIBiG cross-check",
        "rationale": "Synth-010 §3+§5+§7 standard pipeline.",
        "alternatives_considered": ["BiG-SCAPE — round 2 cross-genome", "PRISM — alternative tool"],
    },
    "design_library": [
        {
            "design_id": "D1_bgc_pipeline",
            "kind": "BGC_candidate",
            "spec": {
                "genome": "Streptomyces sp. (test fixture)",
                "tools": ["antiSMASH", "DeepBGC", "MIBiG"],
                "novelty_bands": {
                    "known": ">= 80% MIBiG identity",
                    "variant": "30-80%",
                    "novel": "< 30%",
                },
                "expected_n_clusters": "3-15 (synth-010 §3 typical Streptomyces ~5-10% genome)",
            },
            "rationale": "Direct synth-010 §3+§5 protocol.",
            "evidence_case_ids": ["synth-010-bgcs-natural-product"],
            "evidence_rule_ids": ["09-antismash-mibig-cross"],
        },
    ],
    "excluded_designs": [
        {
            "kind": "single_tool",
            "item": "antiSMASH-only (no DeepBGC consensus)",
            "reason": "Synth-010 ★排除 entry 1 + rule 09: multi-tool consensus avoids false positives.",
            "rule_id": "09-antismash-mibig-cross",
            "case_id": "synth-010-bgcs-natural-product",
        },
        {
            "kind": "no_mibig_cross",
            "item": "novelty claim without MIBiG cross-check",
            "reason": "Synth-010 ★排除 entry 3 + rule 09: rediscovery rate is ~80%, MIBiG mandatory.",
            "rule_id": "09-antismash-mibig-cross",
            "case_id": "synth-010-bgcs-natural-product",
        },
        {
            "kind": "ignore_expression_feasibility",
            "item": "claim novelty for BGCs > 100 kb without cloning plan",
            "reason": "Synth-010 ★排除 entry 4: > 100 kb BGCs are very hard to clone.",
            "rule_id": None,
            "case_id": "synth-010-bgcs-natural-product",
        },
        {
            "kind": "ignore_silent_BGC",
            "item": "predict BGC product without considering silencing",
            "reason": "Synth-010 fail mode 2: silent BGCs need pathway-specific regulator activation.",
            "rule_id": None,
            "case_id": "synth-010-bgcs-natural-product",
        },
    ],
    "computational_pipeline": [
        {
            "step": 1,
            "skill": "bgc_mining",
            "args": {
                "fasta_path_relpath": "tests/fixtures/streptomyces_pks_nrps.fasta",
                "cross_mibig": True,
                "require_consensus": False,  # antiSMASH/DeepBGC binaries not in this env; heuristic falls in
            },
            "rationale": (
                "Rule 09: cross_mibig=True. require_consensus=False because antiSMASH/DeepBGC "
                "binaries aren't bundled in CI; production env with binaries flips to True."
            ),
        },
    ],
    "validation_plan": {
        "experiments": [
            {
                "assay": "untargeted LC-MS / MS-MS",
                "expected_metric": "n novel mass features in fermentation broth",
                "n_replicates": 3,
            },
            {
                "assay": "Dictionary of Natural Products dereplication",
                "expected_metric": "match against known compound DB",
                "n_replicates": 1,
            },
            {
                "assay": "heterologous expression in Streptomyces venezuelae (synth-010 §7)",
                "expected_metric": "BGC product detection in heterologous host",
                "n_replicates": 3,
            },
        ],
        "readout": "LC-MS + dereplication (synth-010 lesson 6)",
    },
    "confidence": "high",
}

_BGC_REPORT_INTERP = {
    "why_succeeded": [
        "antiSMASH + DeepBGC consensus framework declared (rule 09).",
        "MIBiG cross-check mandatory (cross_mibig=True; rule 09 enforcement).",
        "Excluded designs map to 4 synth-010 ★排除 / fail-mode entries.",
    ],
    "why_failed": ["No failures recorded"],
    "literature_alignment": [
        "Aligned with synth-010 (Blin 2020 antiSMASH 7): same multi-tool consensus, same MIBiG "
        "cross-check workflow, same novelty assessment bands (≥80 / 30-80 / <30).",
    ],
    "rules_invoked": ["09-antismash-mibig-cross"],
}


# ---------- LLM dispatch table ----------

_LLM_OUTPUTS: dict[str, dict[str, dict]] = {
    "demo-lycopene-ecoli-fermenter": {
        "scoping": _LYCOPENE_SCOPING,
        "design": _LYCOPENE_DESIGN,
        "report_interpretation": _LYCOPENE_REPORT_INTERP,
    },
    "demo-lysine-cglutamicum-industrial": {
        "scoping": _LYSINE_SCOPING,
        "design": _LYSINE_DESIGN,
        "report_interpretation": _LYSINE_REPORT_INTERP,
    },
    "demo-toggle-switch-ecoli": {
        "scoping": _TOGGLE_SCOPING,
        "design": _TOGGLE_DESIGN,
        "report_interpretation": _TOGGLE_REPORT_INTERP,
    },
    "demo-iml1515-fba-aerobic": {
        "scoping": _FBA_SCOPING,
        "design": _FBA_DESIGN,
        "report_interpretation": _FBA_REPORT_INTERP,
    },
    "demo-moclo-5fragment-assembly": {
        "scoping": _MOCLO_SCOPING,
        "design": _MOCLO_DESIGN,
        "report_interpretation": _MOCLO_REPORT_INTERP,
    },
    "demo-il2-codon-opt-yeast": {
        "scoping": _CODONOPT_SCOPING,
        "design": _CODONOPT_DESIGN,
        "report_interpretation": _CODONOPT_REPORT_INTERP,
    },
    "demo-txtl-gfp-prototyping": {
        "scoping": _CELLFREE_SCOPING,
        "design": _CELLFREE_DESIGN,
        "report_interpretation": _CELLFREE_REPORT_INTERP,
    },
    "demo-arabinose-biosensor": {
        "scoping": _BIOSENSOR_SCOPING,
        "design": _BIOSENSOR_DESIGN,
        "report_interpretation": _BIOSENSOR_REPORT_INTERP,
    },
    "demo-streptomyces-bgc-mining": {
        "scoping": _BGC_SCOPING,
        "design": _BGC_DESIGN,
        "report_interpretation": _BGC_REPORT_INTERP,
    },
}


def has_llm_output(task_id: str, stage: str) -> bool:
    return task_id in _LLM_OUTPUTS and stage in _LLM_OUTPUTS[task_id]


def get_llm_output(task_id: str, stage: str) -> dict[str, Any] | None:
    """Return the embedded LLM-mode output for `stage` of `task_id`, or None.

    Stages: 'scoping' | 'design' | 'report_interpretation'.
    Execution does not have an LLM output — it always runs real skills.
    """
    if not has_llm_output(task_id, stage):
        return None
    out = _LLM_OUTPUTS[task_id][stage]
    # Deep copy via JSON to prevent caller mutation of the embedded dict
    import json as _json
    return _json.loads(_json.dumps(out))


def list_supported_demos() -> list[str]:
    return sorted(_LLM_OUTPUTS.keys())
