# Offline trace and provenance case results

These historical results cover 16 test cases representing 14 distinct requests.
They mix mock, mechanistic, scoring, and advisory paths; they are not a benchmark
of eight validated predictive models. The tests remain available under
`praxis_virtualcell/tests/phase10`. Re-run them for current software validation.

All 16 offline cases recorded `llm_used_for_prediction=False`. Mock values are test fixtures.

| case | abstain | models_used | prediction | module_plan.primary | trace_len |
|---|---|---|---|---|---|
| S1_M1_membrane_FASN | True | ['MockLinear', 'MockCPA'] | None | genetic_hub | 32 |
| S2_M2_genetic_AHR | False | ['MockLinear', 'MockCPA', 'MockGEARS'] | {'delta': [0.3]} | genetic_hub | 32 |
| S3_M3_mito_MYC_growth | True | [] | None | cytoplasmic_metabolism | 28 |
| S4_M4_cobra_b0720_b1136 | False | ['CaseRunner'] | {'delta': [-1.0, -1.0]} | cytoplasmic_metabolism | 28 |
| S5_M5_biosynth_RPL5 | True | ['MockLinear', 'MockCPA'] | None | genetic_hub | 32 |
| S6_M6_niche_state | True | [] | None | None(unroutable) | 28 |
| S7_M7_state_IFNB1 | False | ['CaseRunner'] | {'delta': [2.485]} | stress_processor | 28 |
| S8_M8_degrad_UBB | True | [] | None | cytoplasmic_metabolism | 28 |
| X1_M4M3_flux_IFNB1 | False | ['CaseRunner'] | {'delta': [0.101, 0.281]} | cytoplasmic_metabolism | 28 |
| X2_M4M3_growth_MYC_KRAS | True | [] | None | cytoplasmic_metabolism | 28 |
| X3_quad_SLC2A1_RPL5_PSMB5 | True | ['MockLinear', 'MockCPA'] | None | genetic_hub | 32 |
| X4_M4M8_bact_UBB | True | [] | None | cytoplasmic_metabolism | 28 |
| X5_negtransfer_b0720_expr | True | [] | None | None(unroutable) | 28 |
| X6_C1gate_MYC_growth | True | [] | None | cytoplasmic_metabolism | 28 |
| X7_mouse_GATA1 | False | ['MockLinear', 'MockCPA', 'MockGEARS'] | {'delta': [0.3]} | genetic_hub | 32 |
| X8_diverge_SNAI1_state | True | [] | None | stress_processor | 28 |
