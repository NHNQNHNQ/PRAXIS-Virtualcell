# PHASE 10 — T10.3 端到端 16 CASE 表

> 8 单模块(S)+ 8 跨模块(X),`run_query` 驱动,数据源 trace_bundle.json(实测)。
> 断言明细见 `praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py`。
> **诚实**:M1/M5/M8 是 advisory(断 module_plan entry 非预测);M6 管线 limitation;
> X8 路由声明与引擎背离;X6 C1 gate NO-OP(自然输入不触发)。S2b 真实 GEARS 需 .53(延后)。

| case | 类型 | abstain | prediction | primary | secondary |
|---|---|---|---|---|---|
| S1_M1_membrane_FASN | 单模块 | True | None | genetic_hub | ['membrane_system'] |
| S2_M2_genetic_AHR | 单模块 | False | {'delta': [0.3]} | genetic_hub | [] |
| S3_M3_mito_MYC_growth | 单模块 | True | None | cytoplasmic_metabolism | ['mitochondrial_energy_metabolism'] |
| S4_M4_cobra_b0720_b1136 | 单模块 | False | {'delta': [-1.0, -1.0]} | cytoplasmic_metabolism | [] |
| S5_M5_biosynth_RPL5 | 单模块 | True | None | genetic_hub | ['biosynthetic_network'] |
| S6_M6_niche_state | 单模块 | True | None | None | [] |
| S7_M7_state_IFNB1 | 单模块 | False | {'delta': [2.485]} | stress_processor | [] |
| S8_M8_degrad_UBB | 单模块 | True | None | cytoplasmic_metabolism | ['degradation_machinery'] |
| X1_M4M3_flux_IFNB1 | 跨模块 | False | {'delta': [0.101, 0.281]} | cytoplasmic_metabolism | ['mitochondrial_energy_metabolism'] |
| X2_M4M3_growth_MYC_KRAS | 跨模块 | True | None | cytoplasmic_metabolism | ['mitochondrial_energy_metabolism'] |
| X3_quad_SLC2A1_RPL5_PSMB5 | 跨模块 | True | None | genetic_hub | ['membrane_system', 'biosynthetic_network', 'degradation_machinery'] |
| X4_M4M8_bact_UBB | 跨模块 | True | None | cytoplasmic_metabolism | ['degradation_machinery'] |
| X5_negtransfer_b0720_expr | 跨模块 | True | None | None | [] |
| X6_C1gate_MYC_growth | 跨模块 | True | None | cytoplasmic_metabolism | ['mitochondrial_energy_metabolism'] |
| X7_mouse_GATA1 | 跨模块 | False | {'delta': [0.3]} | genetic_hub | [] |
| X8_diverge_SNAI1_state | 跨模块 | True | None | stress_processor | [] |
