# Offline module case results

These historical results cover 16 test cases representing 14 distinct requests.
They mix mock, mechanistic, scoring, and advisory paths; they are not a benchmark
of eight validated predictive models. The tests remain available under
`praxis_virtualcell/tests/phase10`. Re-run them for current software validation.

| case | Type | abstain | prediction | primary | secondary |
|---|---|---|---|---|---|
| S1_M1_membrane_FASN | Single module | True | None | genetic_hub | ['membrane_system'] |
| S2_M2_genetic_AHR | Single module | False | {'delta': [0.3]} | genetic_hub | [] |
| S3_M3_mito_MYC_growth | Single module | True | None | cytoplasmic_metabolism | ['mitochondrial_energy_metabolism'] |
| S4_M4_cobra_b0720_b1136 | Single module | False | {'delta': [-1.0, -1.0]} | cytoplasmic_metabolism | [] |
| S5_M5_biosynth_RPL5 | Single module | True | None | genetic_hub | ['biosynthetic_network'] |
| S6_M6_niche_state | Single module | True | None | None | [] |
| S7_M7_state_IFNB1 | Single module | False | {'delta': [2.485]} | stress_processor | [] |
| S8_M8_degrad_UBB | Single module | True | None | cytoplasmic_metabolism | ['degradation_machinery'] |
| X1_M4M3_flux_IFNB1 | Multiple modules | False | {'delta': [0.101, 0.281]} | cytoplasmic_metabolism | ['mitochondrial_energy_metabolism'] |
| X2_M4M3_growth_MYC_KRAS | Multiple modules | True | None | cytoplasmic_metabolism | ['mitochondrial_energy_metabolism'] |
| X3_quad_SLC2A1_RPL5_PSMB5 | Multiple modules | True | None | genetic_hub | ['membrane_system', 'biosynthetic_network', 'degradation_machinery'] |
| X4_M4M8_bact_UBB | Multiple modules | True | None | cytoplasmic_metabolism | ['degradation_machinery'] |
| X5_negtransfer_b0720_expr | Multiple modules | True | None | None | [] |
| X6_C1gate_MYC_growth | Multiple modules | True | None | cytoplasmic_metabolism | ['mitochondrial_energy_metabolism'] |
| X7_mouse_GATA1 | Multiple modules | False | {'delta': [0.3]} | genetic_hub | [] |
| X8_diverge_SNAI1_state | Multiple modules | True | None | stress_processor | [] |
