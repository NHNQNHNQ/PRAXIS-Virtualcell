# PRAXIS-2 Deployment Guide

> 总纲 §6⑤(`deploy/` 脚本)+ §6⑦(切换判据)+ §11.1(多 worker)+ §11.7(HPC 节点拓扑)

## 三阶段命令清单

### 阶段 1:本地开发

```bash
# 装运行时
pip install 'httpx>=0.27' 'gunicorn' 'uvicorn[standard]' anthropic

# 起本地 PG/Redis(需 docker)
export POSTGRES_PASSWORD=<strong-local-pwd>   # 必填(B.5),否则 compose 拒启
cd deploy && docker compose up -d postgres redis

# 单 worker(开发用)
PRAXIS_ANTHROPIC_API_KEY=sk-... \
PRAXIS_ANTHROPIC_BASE_URL=https://api.anthropic.com \
PRAXIS_MODEL=claude-3-5-sonnet-20241022 \
PRAXIS_MAX_TOKENS=4096 PRAXIS_MAX_TURNS=30 \
PRAXIS_RECOVERY_BUDGET=3 PRAXIS_MAX_OUTPUT_RECOVERY=2 \
PRAXIS_HOST=127.0.0.1 PRAXIS_PORT=8000 PRAXIS_WORKERS=1 \
PRAXIS_MAX_CONCURRENT_PER_USER=5 PRAXIS_USER_QPS=10.0 \
PRAXIS_GLOBAL_LLM_INFLIGHT=100 PRAXIS_QUOTA_GLOBAL_MAX_QUEUED=100 \
gunicorn -c deploy/gunicorn.conf.py praxis2.server.app:make_app_default

# 多 worker 本地 smoke
PRAXIS_WORKERS=2 PRAXIS_PORT=18001 gunicorn -c deploy/gunicorn.conf.py ...
```

### 阶段 2:Staging(`.40` 前端 / `.53` 后端 + HPC 提交端)

需在 `~/.ssh/config` 配好 alias:

```ssh-config
Host praxis-40
  HostName <staging frontend ip>
  User <user>
  IdentityFile ~/.ssh/id_ed25519_staging

Host praxis-53
  HostName <staging backend ip>
  User <user>
  IdentityFile ~/.ssh/id_ed25519_staging

Host bio000070
  HostName <hpc submit host>
  User bio000070
  IdentityFile ~/.ssh/id_ed25519_bio000070
```

部署命令:

```bash
# 后端 → .53
BACKEND_HOST=praxis-53 BACKEND_PATH=/srv/praxis2 \
    bash deploy/push_backend.sh

# 前端 → .40
FRONTEND_HOST=praxis-40 FRONTEND_PATH=/srv/praxis2-frontend \
    FRONTEND_DIR=../PRAXIS-kernel/frontend \
    bash deploy/push_frontend.sh

# HPC 账号配置
cp deploy/hpc_submit_account.example.toml deploy/hpc_submit_account.toml
# 编辑 hpc_submit_account.toml 填真账号(切勿提交)
echo "deploy/hpc_submit_account.toml" >> .gitignore
```

### 阶段 3:Prod 切换判据(§6⑦)

切换 ≠ big-bang,要全绿:

- [ ] §5⑦ golden 回归(`pytest tests/test_golden_regression.py`)
- [ ] §5⑥ SSE 契约(`pytest tests/test_server_sse.py tests/test_server_app.py`)
- [ ] §5④ RMCP/hook 不变量(`pytest tests/test_rmcp_*.py tests/test_hooks_*.py`)
- [ ] §5⑧ 并发/多租户(`pytest tests/test_runtime_*.py tests/test_m6_invariants.py tests/test_m7_invariants.py`)
- [ ] §11.9 压测(`pytest tests/test_m7_loadtest.py -s`,SLO 数值已回填总纲 §11.9)
- [ ] 本地 → staging staging-smoke 全过

切换:

```bash
# Tag + push
git tag -a v1.0 -m "M8: 切换判据全绿,上线"
git push origin v1.0
```

## ssh 凭证说明

`deploy/hpc_submit_account.toml` 与 `~/.ssh/id_ed25519_*` 严禁提交到 git;
`.gitignore` 已含 `*.toml`(若未,加 `hpc_submit_account.toml`)。

## 故障排查

- 容器起不来 → `docker compose logs <service>`
- gunicorn 起不来 → 检查 PRAXIS_* 环境变量是否齐(`config.py` fail-fast 抛 `ConfigError`)
- SSE 不通 → 检查 `text/event-stream` content-type 是否被代理改写
