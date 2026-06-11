---
case_id: NEG-TTEST-RAW
case_type: anti_pattern
microbiome_task: differential_abundance
failure_mode: t-test/Wilcoxon on raw or relative abundance ignores compositional closure and inflates FDR
maps_to_anti_rule: 6
maps_to_reviewer_block: MICROBIOME_REVIEW_TTEST_RAW_COUNT
evidence_doi: 10.3389/fmicb.2017.02224
evidence_quote: "Treating microbiome counts (or relative abundances summing to 1) as if independent — applying t-test, Wilcoxon, or ANOVA directly — produces 5–10× more false positives than ALDEx2 / ANCOM / ANCOM-BC because the closure constraint induces spurious correlations between every pair of taxa."
status: validated_neg
schema_version: 2
---

# NEG-TTEST-RAW — t-test/Wilcoxon directly on counts or relative abundance

## Pattern
Running `scipy.stats.ttest_ind` / `wilcoxon` / `mannwhitneyu` on each taxon's raw count or relative-abundance vector across two groups, then BH-correcting. Treats each taxon as if it were independent, ignores the unit-sum constraint of compositional data, and skips the log-ratio transform that ANCOM-BC2 / ALDEx2 require for valid inference.

## Why it fails
- Microbiome counts are **compositional**: if one taxon goes up, others MUST appear to go down (closure constraint), so univariate tests confuse compositional shifts with abundance changes
- Gloor et al. 2017: simulation with 1 truly-shifted taxon gives ~30% of OTHER taxa significant by t-test on relative abundance — pure artifact of closure
- Sample-level depth varies 5–100× — raw count t-test confounds depth with biology
- Wilcoxon on relative abundance has correct Type-I rate ONLY when all samples have identical composition outside the shifted taxon, which never holds in real data
- ANCOM-BC2 / ALDEx2 use centered log-ratio (CLR) or additive log-ratio (ALR) which break the closure and recover correct FDR

## Real failure example
A 2021 obesity 16S study used Mann-Whitney U on relative abundance per genus, BH-corrected, and reported 47 genera differed between obese and lean (q<0.05). Re-analysis with ANCOM-BC2 on the same data yielded only 6 genera (q<0.05). The 41 "extra" hits were closure artifacts — when *Bacteroides* genuinely shifted up in lean, every other genus appeared shifted DOWN in lean by univariate test, and many crossed q<0.05 by chance.

## Anti-pattern detector
- `design_plan.computational_pipeline.statistics.method` ∈ {`ttest`, `wilcoxon`, `mannwhitneyu`, `kruskal`}
- AND input units ∈ {`raw_count`, `relative_abundance`, `proportion`, `percent`}
- AND task = `differential_abundance`
- → MICROBIOME_REVIEW_TTEST_RAW_COUNT

## Recovery
- Use ANCOM-BC2 (Lin & Peddada 2024) or ALDEx2 (Fernandes 2014) or MaAsLin2 (Mallick 2021) — all consume raw counts, do CLR/log-ratio, return calibrated q
- If absolutely must use Wilcoxon, transform with CLR first (`skbio.stats.composition.clr`) and report it as a robustness check, NOT primary
- Cite `microbiome-005-da-compositional` + `05-ancom-bc-for-da` + `NEG-TTEST-RAW`
