"""§11.1 gunicorn 多 worker 配置,从 praxis2.config 单一源读(§6⑤)。

用法:`gunicorn -c deploy/gunicorn.conf.py praxis2.server.app:make_app_default`
(workers/bind/timeout 等也可经命令行 `-w N -b host:port` 覆盖)。"""

from praxis2.config import load_from_env

_settings = load_from_env()

bind = f"{_settings.host}:{_settings.port}"
workers = _settings.workers
worker_class = "uvicorn.workers.UvicornWorker"  # 总纲 §11.1 ASGI
timeout = 1800  # M10: 20GB upload 慢路径
graceful_timeout = 30
keepalive = 5
loglevel = "info"
accesslog = "-"
errorlog = "-"
