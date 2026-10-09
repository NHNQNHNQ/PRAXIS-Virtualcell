"""Optional LLM module orchestration filtered through a safety contract and handed to deterministic ModuleRouter.
LLM output selects candidates only; predictions, hard rules, and final verdicts remain runtime-controlled. All 3
authority flags stay False; offline execution does not invoke this package.
"""
