"""八大细胞功能模块规范定义(单一真相源)。

engines 字段 = 该模块当前映射到的现有 route_table engine(可空 = 该模块暂无直接引擎,
走规则/工具/abstain)。pillars = 三大数据支柱归属(mechanistic_knowledge /
subcellular_architecture / dynamic_states)。"""
from __future__ import annotations

# 八模块规范顺序(M1..M8),前端与 registry 均以此为准
MODULE_ORDER = [
    "membrane_system",                 # M1
    "genetic_hub",                     # M2
    "mitochondrial_energy_metabolism", # M3
    "cytoplasmic_metabolism",          # M4
    "biosynthetic_network",            # M5
    "cytoskeletal_framework",          # M6
    "stress_processor",                # M7
    "degradation_machinery",           # M8
]

MODULES: dict[str, dict] = {
    "membrane_system": {
        "code": "M1", "display_name": "Membrane System",
        "engines": [],  # 暂无直接引擎,走脂质通路规则/transporter 注释
        "pillars": ["subcellular_architecture", "mechanistic_knowledge"],
    },
    "genetic_hub": {
        "code": "M2", "display_name": "Genetic Hub",
        "engines": ["donor_predictor"],  # + 未来 GEARS/scGPT
        "pillars": ["dynamic_states", "mechanistic_knowledge"],
    },
    "mitochondrial_energy_metabolism": {
        "code": "M3", "display_name": "Mitochondrial Energy Metabolism",
        "engines": ["gem_fba", "pathway_scoring"],
        "pillars": ["mechanistic_knowledge", "dynamic_states"],
    },
    "cytoplasmic_metabolism": {
        "code": "M4", "display_name": "Cytoplasmic Metabolism",
        "engines": ["gem_fba", "pathway_scoring"],
        "pillars": ["mechanistic_knowledge", "dynamic_states"],
    },
    "biosynthetic_network": {
        "code": "M5", "display_name": "Biosynthetic Network",
        "engines": [],  # 暂无;未来 AlphaFold/ESMFold/PLM
        "pillars": ["mechanistic_knowledge", "subcellular_architecture"],
    },
    "cytoskeletal_framework": {
        "code": "M6", "display_name": "Cytoskeletal Framework",
        "engines": ["spatial_niche"],
        "pillars": ["subcellular_architecture", "dynamic_states"],
    },
    "stress_processor": {
        "code": "M7", "display_name": "Stress Processor",
        "engines": ["state_scoring", "embedding"],
        "pillars": ["dynamic_states", "mechanistic_knowledge"],
    },
    "degradation_machinery": {
        "code": "M8", "display_name": "Degradation Machinery",
        "engines": [],  # 暂无;走 proteostasis/autophagy 基因集规则
        "pillars": ["mechanistic_knowledge", "subcellular_architecture"],
    },
}

# 物种特异显示别名(铁律:bacteria 不叫线粒体)。key = (species, module_id)。
_SPECIES_DISPLAY_ALIASES = {
    ("bacteria", "mitochondrial_energy_metabolism"): "Energy metabolism / redox module",
}


def module_ids() -> list[str]:
    return list(MODULE_ORDER)


def module(module_id: str) -> dict:
    if module_id not in MODULES:
        raise KeyError(f"未知模块: {module_id}(支持: {MODULE_ORDER})")
    return MODULES[module_id]


def display_name(module_id: str, *, species: str | None = None) -> str:
    if species is not None and (species, module_id) in _SPECIES_DISPLAY_ALIASES:
        return _SPECIES_DISPLAY_ALIASES[(species, module_id)]
    return module(module_id)["display_name"]
