---
rule_id: anti-rules-from-NEG-cases
schema_version: 1
rule_type: anti_rule_collection
confidence: high
applies_to:
  docking_types: ["*"]
evidence_neg_cases:
  - NEG-01-no-redock-self-test
  - NEG-02-single-method-no-consensus
  - NEG-03-rigid-receptor-large-conformational-gap
  - NEG-04-box-too-large-drift
  - NEG-05-pp-ranked-by-raw-score
  - NEG-06-antibody-with-generic-pp-docker
  - NEG-07-flexpepdock-long-peptide
  - NEG-08-covalent-without-warhead-restraint
  - NEG-09-ensemble-too-short-md
  - NEG-10-ifd-as-first-line
  - NEG-11-iptm-as-affinity
  - NEG-12-na-with-pp-docker
  - NEG-13-dud-e-no-baseline
  - NEG-14-diffdock-blind-shipped
  - NEG-15-gpcr-state-mismatch
  - NEG-16-mpro-covalent-no-warhead
  - NEG-17-protac-iptm-as-affinity
  - NEG-18-rfaa-single-seed
  - NEG-19-rna-aptamer-pp-docker
  - NEG-20-membrane-md-no-lipid
distilled_at: 2026-05-03
version: v0.9 (multi-anchor)
---

# 12 Anti-Rules From 20 NEG- Cases (multi-anchor evidence)

12 formal anti-patterns. Any candidate triggering any one is auto-rejected by Reviewer.
Each anti-rule has multi-anchor evidence (1-3 NEG cases each).
Verifier: scripts/retrieval/test_anti_retrieval.py (12/12 pass = system healthy).

## anti-rule-01: No redock self-test on production PL docking
- Trigger: PL docking_type + missing redock_self_test_min_0.30 sanity check; OR DUD-E EF/AUC as substitute
- Evidence: NEG-01 (Vina kinase library) / NEG-13 (DUD-E AKT1 EF=12.5 redock 22%) / dock-001
- Severity: BLOCK

## anti-rule-02: Single docking method shipped (no >= 2 method consensus)
- Trigger: chosen_methods.length < 2; cross_method_consensus.level == null; DiffDock-blind solo; FM n_seeds < 5
- Evidence: NEG-02 (Vina-only) / NEG-14 (DiffDock-blind) / NEG-18 (RFAA single-seed) / dock-001 / dock-013
- Severity: BLOCK
- Multi-anchor: 3 NEG -> causal candidate

## anti-rule-03: Rigid receptor + large conformational change
- Trigger: rigid + apo->holo gap > 3 A; GPCR agonist <-> inactive crystal mismatch
- Evidence: NEG-03 (kinase DFG-out) / NEG-15 (GPCR state mismatch) / dock-008 / dock-012
- Severity: BLOCK; route to ensemble / IFD / AF3

## anti-rule-04: Vina box > 30 A drifts to allosteric / surface
- Trigger: box.size dim > 30 (BLOCK at 40); GPCR > 22
- Evidence: NEG-04 / dock-001 / dock-012
- Severity: WARN > 30, BLOCK > 40

## anti-rule-05: PP docking ranked by raw HADDOCK / PIPER score
- Trigger: cluster_size missing; HADDOCK AIR > 30; ClusPro weight_sets < 3
- Evidence: NEG-05 / dock-002 / dock-003
- Severity: BLOCK (cluster_size missing); WARN (multi-weight < 3)

## anti-rule-06: Antibody-antigen with generic PP docker (no antibody-mode)
- Trigger: cluspro_blind_pp without antibody_mode; haddock without paratope CDR_only; framework not in {IgFold, ImmuneBuilder, NanoNet, AF-Multimer}
- Evidence: NEG-06 / dock-003 / dock-004 / dock-014
- Severity: BLOCK

## anti-rule-07: Peptide > 20 aa with FlexPepDock
- Trigger: peptide_length_bin == ">20" + flexpepdock; cyclic peptide; missing secondary structure
- Evidence: NEG-07 / dock-005
- Severity: BLOCK; route to af3_complex_predict + post-MD

## anti-rule-08: Covalent ligand without warhead detection / reactive_residue / distance restraint
- Trigger: reactive_residue == null; distance > 2.0 A; vina_gnina_dock without --covalent-residue;
  warhead chemistry not detected (acrylamide / aldehyde / chloroacetamide / Michael acceptor / nitrile / vinyl sulfonamide / alpha-chloroketone / cyanoacrylamide / epoxide / boronate)
- Evidence: NEG-08 (KRAS Cys acrylamide) / NEG-16 (Mpro Cys145 aldehyde) / dock-006 / dock-011 / rule_01 formal
- Severity: BLOCK
- Multi-warhead-chemistry: acrylamide + aldehyde

## anti-rule-09: Ensemble docking MD < 100 ns OR water-only on membrane
- Trigger: md_length_ns < 50 (BLOCK); 50-100 ns without RMSD plateau (WARN);
  membrane protein + water-only MD; n_cluster_representatives outside 5-10
- Evidence: NEG-09 (HIV protease 30 ns) / NEG-20 (GPCR water-only) / dock-007 / dock-012 / dock-018
- Severity: BLOCK < 50 ns OR water-only-membrane; WARN 50-100 ns

## anti-rule-10: IFD as first-line on > 100 compound library
- Trigger: IFD + library > 100 + no rigid baseline; flex_residues > 6
- Evidence: NEG-10 / dock-008
- Severity: BLOCK flex > 6; WARN library > 100

## anti-rule-11: Foundation model output without PoseBusters / iPTM as affinity
- Trigger: posebusters_check == null; iPTM/pLDDT -> KD/IC50/DC50/alpha factor;
  PROTAC ternary iPTM as productive degradation; n_seeds < 5;
  PDB year < 2021 without train_set_leakage_acknowledged
- Evidence: NEG-11 (AF3 KD claim) / NEG-17 (PROTAC iPTM=0.91 anti-cooperative) / NEG-18 (RFAA single-seed) / dock-009 / dock-013 / dock-016
- Severity: BLOCK (PB missing OR affinity claim); WARN (n_seeds < 5)
- Multi-anchor: 3 NEG -> causal candidate

## anti-rule-12: Protein-NA with pure PP docker / no PWM-PAM-secondary-structure validation
- Trigger: cluspro/haddock without NA mode; PWM/PAM missing motif/sequence;
  Cas9 apo (4CMP) instead of holo (4OO8); ssRNA aptamer missing secondary structure
- Evidence: NEG-12 (Zif268 TF-DNA) / NEG-19 (RNA aptamer + HADDOCK) / dock-010 / dock-015
- Severity: BLOCK

## Multi-anchor coverage map

| anti-rule | NEG anchors | docking_types covered | promotion |
|---|---|---|---|
| 01 | NEG-01, NEG-13 | PL, PL_redocking | strong |
| 02 | NEG-02, NEG-14, NEG-18 | PL, FM | **causal candidate** |
| 03 | NEG-03, NEG-15 | kinase, GPCR | strong (cross target_class) |
| 04 | NEG-04 | PL | single |
| 05 | NEG-05 | PP | strong |
| 06 | NEG-06 | antibody | strong |
| 07 | NEG-07 | peptide | single |
| 08 | NEG-08, NEG-16 | covalent (acrylamide+aldehyde) | strong |
| 09 | NEG-09, NEG-20 | ensemble + membrane | strong |
| 10 | NEG-10 | IFD | single |
| 11 | NEG-11, NEG-17, NEG-18 | FM PL + ternary + RFAA | **causal candidate** |
| 12 | NEG-12, NEG-19 | NA dsDNA + ssRNA | strong |

Promotion to causal_tag = causal requires evidence across >= 3 confounder layers.

## Boundary conditions

- confidence_label: cold_start + explicit caveat -> may proceed (flagged metadata)
- User explicit --ignore-anti-rule N -> proceed with caveat
- Rule supersession by positive evidence -> RMCP Phase 4 arbitration
