# 可选智能体服务配置

`gunicorn.conf.py` 是保留的 praxis2 服务配置，供已完成独立配置的多用户服务使用。安装依赖见根目录 `server` extra；当前整合验证覆盖离线智能体和 MDR API，没有验证远程部署。

当前单药 API 可直接从仓库根运行：

```bash
.venv/bin/praxis-mdr serve --host 127.0.0.1 --port 8000
```

旧 PRAXIS-2/VC Docker、远程 push、前端代理与 HPC 部署示例已移至同级 `PRAXIS-virtualcell-old/PRAXIS-virtualcell/deploy/`。
