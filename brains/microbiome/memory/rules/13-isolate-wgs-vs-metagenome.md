---
rule_id: 13-isolate-wgs-vs-metagenome
rule_type: case_distilled
applies_to: {microbiome_task: [isolate_wgs_pipeline, mag_assembly, shotgun_taxonomy], sample_type: [anaerobic_pure_culture, single_strain_culture, human_gut, mock_community]}
confidence: high
evidence_cases: [microbiome-013-hgmb-isolate-wgs, microbiome-002-shotgun-kraken, microbiome-003-mag-assembly]
schema_version: 2
---

# Rule 13: Use single-genome (SPAdes --isolate) for pure culture, NOT metagenome assembly

## Statement
When the input is a **pure-culture isolate**（hGMB / mGMB / 单菌纯培养 WGS reads），use:
- **SPAdes --isolate** or **Unicycler** for assembly (NOT MEGAHIT / metaSPAdes)
- **Direct ANI** vs type-strain DB for species call (NOT Kraken2/MetaPhlAn community classifiers)
- **No binning** (single genome — no bins to pull)
- **CheckM2** for completeness/contamination QC (single-genome mode)

## Why
Liu Shuangjiang lab's hGMB workflow (Zou et al. 2019 *Nat Biotechnol*, 10.1038/s41587-018-0008-8) demonstrated that:
- Single-isolate genomes assembled with SPAdes --isolate achieve N50 100kb–1Mb and complete 16S/23S rDNA recovery
- Metagenome assemblers (MEGAHIT/metaSPAdes) are tuned for low-coverage chimeric communities and produce more fragmented assemblies on pure cultures
- Community classifiers (Kraken2/MetaPhlAn) waste compute and obscure novelty: hGMB has 264 *previously uncultured* species that have NO reference in shotgun DBs
- The correct identification path for a pure isolate is **fastANI/skani vs type-strain genomes** — > 95% ANI = same species; > 99.99% = same strain

Treating an isolate as a metagenome:
- Wastes CPU on multi-binner consensus (rule-03), producing 1 bin = the isolate (silly)
- Misses 264 species in hGMB that have no Kraken2 entry → "Unassigned"
- Produces meaningless DA / network analyses (only 1 sample)

## How to apply
- **Reviewer gate `MICROBIOME_REVIEW_METAGENOME_FOR_ISOLATE`**: trigger when `input.metadata.sample_type ∈ {anaerobic_pure_culture, single_strain_culture, isolate}` AND pipeline tools include `megahit | metaspades | kraken2 | metaphlan | concoct | metabat2`.
- Recommended skill: **`cultured_isolate_wgs_real`** (single-genome SPAdes + Prokka + skani + diamond KO + abricate ARG).
- Required steps inside the skill: fastp QC → SPAdes --isolate → QUAST → CheckM2 → skani vs hGMB type strains → Prokka → KEGG KO + SCFA targeted scan → CARD ARG.

## Evidence
- microbiome-013 (hGMB / Zou 2019): 1,520 isolate genomes, all SPAdes-assembled; demonstrates pure-culture WGS pipeline is distinct from metagenome
- microbiome-003 (MAG assembly): explicitly applies multi-binner only when sample is community
- microbiome-002 (Kraken2 shotgun): only valid for community samples

## Anti-patterns
- ❌ MEGAHIT on pure-culture reads
- ❌ Kraken2/MetaPhlAn for "community profile" of a single isolate
- ❌ MetaBAT2/CONCOCT/MaxBin2 binning of single-genome assembly
- ❌ Treating isolate WGS as if it were metagenome → no diversity / no DA / useless

## Implementation pointer
- `skills/workflows/cultured_isolate_wgs_real/run.py`
- `skills/workflows/scfa_butyrate_screen_real/run.py` for downstream SCFA pathway analysis
- Anti-rule predicate in `scripts/retrieval/anti_pattern_retrieval.py` (rule 13: NEG-METAGENOME-FOR-ISOLATE)
