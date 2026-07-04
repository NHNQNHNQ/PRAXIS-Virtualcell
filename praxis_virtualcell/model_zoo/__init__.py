"""model_zoo:ModelBroker 治理框架 —— 声明式注册表 + wrapper 契约 + 缓存/版本锁 + 下载契约。

设计:公开模型下载与自训模型注册标准化。缺模型/缺依赖/sha 不匹配一律 fail-closed,
绝不 silent accept。Phase 2 只交付库 + ModelBrokerAgent,可独立测试;接进 runtime 管线在 Phase 3。
"""
