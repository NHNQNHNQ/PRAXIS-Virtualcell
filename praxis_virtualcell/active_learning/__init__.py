"""主动学习子包(Phase 5,v1.2):acquisition(information gain 启发式)+ learning_queue(优先队列)
+ ActiveLearningAgent(进 bus,产 learning_queue)。

铁律:主动学习产"该测什么"的 advisory 优先队列,用现有 disagreement/OOD/证据等级/module 弱支持
信号(v0.8 已有,确定性零 LLM)排序;**绝不碰 prediction/verdict 终决/provenance ledger/reliability
决策**(不改裁决,只建议下一步实验)。OFFLINE 默认零 LLM,本子包不 import agents_llm/llm_orchestration。
"""
