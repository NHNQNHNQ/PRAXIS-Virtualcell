"""Web 适配层(总纲 §1/§2,M6 校准①:第一版纯 ASGI,FastAPI 是其
路由糖,不引入重依赖;M8 仍 uvicorn 启动)。routes 零业务逻辑,
只调 praxis2 公共接口(§2 边界,对治 v1 把编排塞 chat.py)。"""
