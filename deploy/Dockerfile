# §6⑤ backend 镜像(D.5 加固第二轮:多阶段 + non-root USER + .dockerignore + pin prod deps)
# 用法:在 PRAXIS-2 根目录跑 `docker build -f deploy/Dockerfile -t praxis2-backend .`
# (compose 会自动 build:`docker compose build backend`)
#
# reviewer M0/M8:#4 prod deps 必 pin / #5 non-root USER / #6 .dockerignore
# D.5 fixup:deps 阶段 mkdir + touch 让 setuptools build 通过(pyproject single source),
# runtime 阶段真 COPY praxis2 到 WORKDIR + PYTHONPATH=/app 优先于 site-packages stub

# ── Stage 1:deps(只装依赖,cache 友好) ───────────────────────
FROM python:3.13-slim AS deps
WORKDIR /app
COPY pyproject.toml ./
# Minimal stub:让 setuptools.packages.find 找得到 praxis2 包,extras 才能装上
# (真源码在 runtime 阶段 COPY,stub 在 runtime 被 WORKDIR 覆盖 + PYTHONPATH 优先)
RUN mkdir -p praxis2 && touch praxis2/__init__.py
RUN pip install --no-cache-dir ".[prod]" && rm -rf /root/.cache

# ── Stage 2:runtime(最小化,non-root) ──────────────────────
FROM python:3.13-slim
WORKDIR /app

# 非 root 用户(D.5 reviewer M0/M8 #5:容器逃逸防御)
RUN useradd -r -u 1000 -m -s /sbin/nologin praxis2

# 拷 deps 层的 site-packages + 入口脚本
COPY --from=deps /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# 拷真源码(覆盖 stub;PYTHONPATH=/app 让 cwd 优先于 site-packages)
COPY praxis2 ./praxis2
COPY deploy/gunicorn.conf.py ./gunicorn.conf.py

ENV PYTHONPATH=/app
RUN chown -R praxis2:praxis2 /app
USER praxis2

EXPOSE 8000

# gunicorn + uvicorn worker_class(总纲 §11.1 多 worker 无状态)
# `make_app_default` 在 server/app.py(M8 Task 4 加,接 config.py)
CMD ["gunicorn", "-c", "gunicorn.conf.py", "praxis2.server.app:make_app_default"]
