---
rule_id: 01-covalent-docking-reactive-residue-mandatory
schema_version: 1
rule_type: case_distilled
confidence: high
applies_to:
  docking_types: [covalent_protein_ligand]
  target_classes: [kinase, GTPase, protease, deubiquitinase]
evidence_cases:
  - dock-006-covalent-docking-cysteine    # KRAS G12C + sotorasib (acrylamide)
  - dock-011-btk-ibrutinib-covalent-ser   # BTK Cys481 + ibrutinib (acrylamide, wild-type Cys)
distilled_at: 2026-04-30
---

# Rule 01: Covalent Docking Requires Explicit Reactive Residue + Distance Restraint

**Confidence**: high (≥ 2 case-evidence + cross-target consistency)

## Statement

For all `docking_type == covalent_protein_ligand` tasks, the following are
**mandatory** and Reviewer must block any design that violates them:

1. **`reactive_residue` (chain:3-letter:resnum) must be specified** in
   `system_specifics` or `restraints`. No "to-be-determined" allowed at design stage
   (scoping stage is OK to defer).
2. **`distance_constraint_A ≤ 2.0 Å`** between warhead α-carbon and the reactive
   atom (Cys SG / Ser OG / Lys NZ). Default: 2.0 Å.
3. **Warhead detection** (acrylamide / chloroacetamide / Michael acceptor /
   vinyl sulfonamide / α-chloroketone / cyanoacrylamide / etc.): SMARTS pattern
   matching against ligand SMILES is mandatory. If no warhead detected and no
   `reactive_residue` specified, switch to `vina_gnina_dock` non-covalent.
4. **`vina_gnina_dock` alone (without `--covalent-residue` flag) is auto-rejected**
   for covalent ligands (warhead would point away from reactive residue).
5. **Use Meeko `--tether_smarts` + `--rec_residue`** for ligand prep when
   `mk_prepare_ligand.py` is available; this generates the covalent-attached
   PDBQT that Vina then optimizes.

## Why this is a high-confidence rule

### Evidence: dock-006 (KRAS G12C + sotorasib)

- Without distance constraint, plain Vina puts warhead "朝外 / 朝 ATP 进入方向 — 物理不可成键"
- Multiple candidate Cys in receptor (e.g., Cys118 vs Cys12); docking must
  limit to target Cys
- Two-step approach mandatory: (a) reversible warhead-residue placement,
  (b) covalent attachment + minimization

### Evidence: dock-011 (BTK + ibrutinib)

- BTK Cys481 (wild-type, NOT mutation-introduced like KRAS G12C) — same
  reactive Cys workflow applies regardless of WT vs mutant
- Pocket geometry **+** warhead reactivity together determine selectivity;
  different acrylamide warheads on different Cys give different selectivity
  (BTK selective ibrutinib vs ITK off-target Cys)
- C481S resistance mutation pre-prediction: docking with reactive Cys → Ser
  swap → low covalent score → predict non-covalent BTK inhibitor needed.
  Without reactive_residue specification, this prediction is impossible.

### Cross-case consistency

Both cases independently demand:
- Explicit reactive Cys residue specification
- Distance restraint enforcement (≤ 2.0 Å)
- Warhead detection up-front
- Off-target Cys panel evaluation (proteome-wide reactivity prediction)

These align across kinase (BTK) and GTPase (KRAS) targets, suggesting the
rule generalizes to **all covalent protein-ligand docking**.

## Reviewer enforcement

In `agents/prompts/reviewer.md` covalent rules:

> For `detected_docking_type == covalent_protein_ligand`:
>   - `restraints.reactive_residue` must be specified (else BLOCK with
>     "covalent must specify reactive Cys")
>   - `restraints.distance_constraint_Å` must be ≤ 2.0 (else BLOCK)
>   - `chosen_methods` must NOT include `vina_gnina_dock` alone — must use
>     covalent variant (else BLOCK)

This rule is the formal high-confidence statement of those Reviewer checks.

## Boundary conditions (when this rule does NOT apply)

- **Reversible covalent** (cyanoacrylamide, β-lactam, certain warheads with
  reverse-Michael): equilibrium analysis required; distance restraint still
  applies but `kinact/Ki` separate from docking score.
- **Allosteric covalent**: warhead reactivity ≠ binding pocket; docking
  cannot capture allosteric mechanism — ensemble docking + MD likely needed.
- **Cys oxidation state**: in oxidative environments Cys can be sulfenylated
  (S-OH) or in disulfide bridges; rule assumes reduced Cys. Flag as caveat.
- **Multiple reactive residues**: receptor has multiple potentially-reactive
  Cys (proteome-scale); docking solves single-target case but proteome-wide
  off-target panel is a separate analysis.

## Promotion path forward

Adding **dock-016+** with covalent on Lys nucleophile (e.g., FBA covalent
lysine inhibitors) or covalent on Ser (e.g., serine protease + boronate)
would extend this rule to non-Cys nucleophiles. Currently the rule's evidence
is Cys-only (dock-006 + dock-011); other nucleophile types are sound by
extrapolation but not formally evidence-backed.
