---
rule_id: rule_13_active_metabolite_pkpd
rule_type: case_distilled
applies_to: [pkpd, ddi, tdm]
evidence_cases:
  - pharma-009-pkpd-emax
  - pharma-012-cyp2d6-codeine
  - pharma-013-cyp2c19-clopidogrel
confidence: high
authoring_date: 2026-04-30
source_synthesis_section: parent vs active metabolite PK
---

# 活性代谢物 PK 必须独立建模

Many drugs are prodrugs or have pharmacologically active metabolites; the
parent compound concentration is **not** what drives the effect. PK-PD
modeling on the parent alone fails to capture the true dose-response.

## Examples
- **Codeine** (case-012): parent codeine itself is weak μ-receptor agonist;
  morphine (CYP2D6 metabolite) is the active analgesic. CYP2D6 PMs cleave
  codeine to morphine inefficiently → no analgesia despite normal codeine
  exposure. CYP2D6 UMs cleave too efficiently → toxic morphine concentrations.
- **Clopidogrel** (case-013): clopidogrel is itself inactive; CYP2C19
  generates the active thiol metabolite that covalently binds P2Y12.
  CYP2C19 PMs have ~50% active metabolite AUC → reduced platelet inhibition
  → ↑MACE.
- **Pembrolizumab** (case-009 — NOT a prodrug): the parent IS the active
  agent (mAb). Note this rule does NOT apply to all biologics; check whether
  the active species = administered species.
- **Tamoxifen** → endoxifen (CYP2D6); 4-hydroxytamoxifen also active.
- **Codeine sibling tramadol**: tramadol → O-desmethyltramadol (CYP2D6) is the
  active metabolite for analgesia.

## Mandatory operations

1. **Identify the active species** explicitly in case provenance. Document in
   `key_paper_doi`-cited mechanism section.
2. **Model active metabolite PK separately** from parent: separate CL, V,
   formation rate; PD modeling uses active metabolite concentration.
3. **Pharmacogenomic awareness** for bioactivation pathways: CYP2D6 (codeine,
   tramadol, tamoxifen, atomoxetine), CYP2C19 (clopidogrel, prasugrel partial),
   CYP3A4 (cyclophosphamide).
4. **DDI risk**: inhibition of bioactivation pathway = LOSS OF EFFICACY
   (not toxicity). Reverse direction from typical DDI thinking.
5. **Reviewer soft-flag**: PK/PD model on parent for known prodrug → flag for
   re-modeling.

## Confidence

3 case-evidenced direct + meta-evidence from CPIC-listed prodrugs.
