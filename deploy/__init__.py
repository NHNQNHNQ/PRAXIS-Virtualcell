"""§6⑤ 部署 artifacts(总纲 §1 顶层架构 deploy/ 节)。

本目录不参与 praxis2 运行时;只放部署期文件:
- `docker-compose.yml`:本地 PG+Redis+backend worker
- `Dockerfile`:backend 镜像(pip 装依赖 + gunicorn 多 worker)
- `gunicorn.conf.py`:gunicorn workers/worker_class/bind 配置(读 praxis2.config)
- `push_backend.sh` / `push_frontend.sh`:rsync 到 .53/.40 + 远端起 service
- `hpc_submit_account.example.toml`:HPC 4 节点账号模板
- `README.md`:部署文档(本地/staging/prod 三阶段命令)
"""
