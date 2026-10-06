"""PRAXIS-MDR-GNB 服务化层(阶段 9)。

只做 HTTP 适配:把确定性预测入口 run_mdr_query 与 registry/evidence_tiers 资产暴露成
只读 API,不重算任何科学。红线:确定性(同 raw 逐字相等)、fail-closed(unsupported 物种
不伪造预测)、LLM 不裁决、证据分层门控如实标注。
"""
