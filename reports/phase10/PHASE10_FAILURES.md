# PHASE 10 — 负例与 ABSTAIN 表

> T10.3 16 case 中 11 个诚实 abstain(数据源 trace_bundle.json)。
> 补充负例 corpus(schema/route/provenance gate/注入)见 tests/negative_cases、
> test_t10_4/5/6、test_negative_cases.py —— 见 spec §2.5 数据源清单。

| case | abstain_reason(推断) | models_rejected | module_plan |
|---|---|---|---|
| S1_M1_membrane_FASN | prediction None | ['MockGEARS'] | genetic_hub overall=downgrade |
| S3_M3_mito_MYC_growth | prediction None | ['CaseRunner'] | cytoplasmic_metabolism overall=downgrade |
| S5_M5_biosynth_RPL5 | prediction None | ['MockGEARS'] | genetic_hub overall=downgrade |
| S6_M6_niche_state | prediction None | ['MockLinear', 'MockCPA', 'MockGEARS'] | None(unroutable) |
| S8_M8_degrad_UBB | prediction None | ['CaseRunner'] | cytoplasmic_metabolism overall=downgrade |
| X2_M4M3_growth_MYC_KRAS | prediction None | ['CaseRunner'] | cytoplasmic_metabolism overall=downgrade |
| X3_quad_SLC2A1_RPL5_PSMB5 | prediction None | ['MockGEARS'] | genetic_hub overall=downgrade |
| X4_M4M8_bact_UBB | prediction None | ['CaseRunner'] | cytoplasmic_metabolism overall=downgrade |
| X5_negtransfer_b0720_expr | prediction None | ['MockLinear', 'MockCPA', 'MockGEARS'] | None(unroutable) |
| X6_C1gate_MYC_growth | prediction None | ['CaseRunner'] | cytoplasmic_metabolism overall=downgrade |
| X8_diverge_SNAI1_state | prediction None | ['CaseRunner'] | stress_processor overall=accept |
