#!/usr/bin/env bash
# §6⑤ push backend (praxis2/ + brains/) to .53 + restart gunicorn (M8 Task 12 实测)
#
# 用法:
#   BACKEND_HOST=praxis-53 BACKEND_USER=praxis BACKEND_PATH=/srv/praxis2 \
#       bash deploy/push_backend.sh
#
# 必填环境变量(全缺则脚本退出):
#   BACKEND_HOST    — ssh 目标主机或 ~/.ssh/config alias
#   BACKEND_USER    — 远端用户(常 = alias 已隐含,可空)
#   BACKEND_PATH    — 远端代码目录绝对路径(server 进程的 _REPO_ROOT)
#
# 可选:
#   SERVICE_NAME              — systemd unit 名(默认 praxis2-backend.service);
#                               设为 "skip" 时跳过 systemctl restart(开发/无 sudo 场景)
#   PRAXIS_SKILL_REMOTE_BRAINS — SkillExecTool ssh 真跑的 brains 目录路径
#                               (如 /home/zkyd/data1/mzy/praxis2-brains);
#                               设了就额外 rsync 一份到那儿,server 本地
#                               (${BACKEND_PATH}/brains)仅用于枚举 SKILL.md。
set -euo pipefail

: "${BACKEND_HOST:?缺 BACKEND_HOST(目标主机或 ssh alias)}"
: "${BACKEND_PATH:?缺 BACKEND_PATH(远端代码绝对路径)}"
SERVICE_NAME="${SERVICE_NAME:-praxis2-backend.service}"

REMOTE="${BACKEND_USER:+${BACKEND_USER}@}${BACKEND_HOST}"

RSYNC_OPTS=(-avz --delete --partial --partial-dir=.rsync-partial
            --exclude '__pycache__' --exclude '*.pyc' --exclude '.venv'
            --exclude '._*' --exclude '.DS_Store')

echo "[push_backend] rsync praxis2/ → ${REMOTE}:${BACKEND_PATH}/praxis2/"
rsync "${RSYNC_OPTS[@]}" praxis2/ "${REMOTE}:${BACKEND_PATH}/praxis2/"

echo "[push_backend] rsync brains/ → ${REMOTE}:${BACKEND_PATH}/brains/ (server 本地枚举 SKILL.md)"
rsync "${RSYNC_OPTS[@]}" brains/ "${REMOTE}:${BACKEND_PATH}/brains/"

# alembic schema migrations:M11.x 必须同步,否则 backend 启动后 endpoint 503 (表不存在)
echo "[push_backend] rsync migrations/ → ${REMOTE}:${BACKEND_PATH}/migrations/"
rsync "${RSYNC_OPTS[@]}" migrations/ "${REMOTE}:${BACKEND_PATH}/migrations/"

# deploy/ 不 --delete:保护 .53 上 user 自维护的 prod conf (如 litellm_deepseek.yaml + .bak),
# 这些不在 git 但 prod 必需。本地新文件仍会 push 上去,只是不会反向删 .53 上多出的。
echo "[push_backend] rsync deploy/ → ${REMOTE}:${BACKEND_PATH}/deploy/ (no --delete; exclude prod conf)"
rsync -avz --partial --partial-dir=.rsync-partial \
      --exclude '__pycache__' --exclude '*.pyc' --exclude '.venv' \
      --exclude '._*' --exclude '.DS_Store' \
      --exclude 'litellm*.yaml*' --exclude '*.bak*' \
      deploy/ "${REMOTE}:${BACKEND_PATH}/deploy/"

# SkillExecTool 在 server 进程内 ssh 到本机 PRAXIS_SKILL_REMOTE_BRAINS 真跑 run.py。
# 这条路径独立于 BACKEND_PATH;若设了就同步一份,保证 brains 真路径与 git 一致。
if [ -n "${PRAXIS_SKILL_REMOTE_BRAINS:-}" ]; then
    echo "[push_backend] rsync brains/ → ${REMOTE}:${PRAXIS_SKILL_REMOTE_BRAINS}/ (SkillExecTool 真跑路径)"
    ssh "${REMOTE}" "mkdir -p '${PRAXIS_SKILL_REMOTE_BRAINS}'"
    rsync "${RSYNC_OPTS[@]}" brains/ "${REMOTE}:${PRAXIS_SKILL_REMOTE_BRAINS}/"
else
    echo "[push_backend] (skip)未设 PRAXIS_SKILL_REMOTE_BRAINS,跳过 SkillExec 真路径同步" >&2
fi

echo "[push_backend] pip install on remote"
ssh "${REMOTE}" "cd '${BACKEND_PATH}' && python3 -m pip install --user \
    'httpx>=0.27' 'gunicorn' 'uvicorn[standard]' 'asyncpg' 'redis>=4.2' 'anthropic' \
    'python-multipart>=0.0.9' 'python-magic>=0.4.27' 'PyYAML>=6.0' \
    'asyncssh>=2.14,<3'"

if [ "${SERVICE_NAME}" = "skip" ]; then
    echo "[push_backend] (skip)SERVICE_NAME=skip,跳过 systemctl restart" >&2
else
    echo "[push_backend] restart ${SERVICE_NAME}"
    ssh "${REMOTE}" "sudo systemctl restart '${SERVICE_NAME}' && \
        sudo systemctl status '${SERVICE_NAME}' --no-pager"
fi

echo "[push_backend] done"
