# Offline abstention cases

These historical results cover 16 test cases representing 14 distinct requests.
They mix mock, mechanistic, scoring, and advisory paths; they are not a benchmark
of eight validated predictive models. The tests remain available under
`praxis_virtualcell/tests/phase10`. Re-run them for current software validation.

Eleven cases abstained. Reasons below are inferred from stored artifacts; the runtime report is authoritative.

| case | Inferred abstention reason | models_rejected | module_plan |
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
