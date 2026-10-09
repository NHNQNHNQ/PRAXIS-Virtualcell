"""LLM 编排子包(Phase 4,v1.1):LLMModulePlanner + safety_contract + cross_module_reasoner。

铁律:LLM 只出 module 集建议(经 safety_contract 过滤成合法候选子集),转 AgentMessage 交
ModuleRouter 用 Phase 3 确定性代码合成 ModulePlan;LLM 绝不碰 prediction/hard-rule/verdict 终决
(assert_llm_boundaries 三 flag 恒 False)。OFFLINE 默认零 LLM,本子包不被触发。
"""
