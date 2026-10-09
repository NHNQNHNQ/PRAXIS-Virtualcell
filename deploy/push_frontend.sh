#!/usr/bin/env bash
# §6⑤ push frontend to .40 (build + rsync) (M8 Task 12 实测)
#
# 用法:
#   FRONTEND_HOST=praxis-40 FRONTEND_PATH=/srv/praxis2-frontend FRONTEND_DIR=../frontend \
#       bash deploy/push_frontend.sh
#
# 必填环境变量:
#   FRONTEND_HOST   — ssh 目标
#   FRONTEND_PATH   — 远端 web root 绝对路径
#   FRONTEND_DIR    — 本机前端项目目录(含 package.json,默认 ../PRAXIS-kernel/frontend)
set -euo pipefail

: "${FRONTEND_HOST:?缺 FRONTEND_HOST(ssh 目标或 alias)}"
: "${FRONTEND_PATH:?缺 FRONTEND_PATH(远端 web root)}"
FRONTEND_DIR="${FRONTEND_DIR:-../PRAXIS-kernel/frontend}"
REMOTE="${FRONTEND_USER:+${FRONTEND_USER}@}${FRONTEND_HOST}"

if [ ! -d "${FRONTEND_DIR}" ]; then
    echo "[push_frontend] FRONTEND_DIR ${FRONTEND_DIR} 不存在;skip build,只 rsync 已 build 的 dist/" >&2
fi

if [ -f "${FRONTEND_DIR}/package.json" ]; then
    echo "[push_frontend] build in ${FRONTEND_DIR}"
    pushd "${FRONTEND_DIR}" >/dev/null
    if command -v pnpm >/dev/null; then
        pnpm install --frozen-lockfile && pnpm build
    elif command -v npm >/dev/null; then
        npm ci && npm run build
    else
        echo "[push_frontend] 缺 npm/pnpm,无法 build;若已 build 跳此步" >&2
    fi
    popd >/dev/null
fi

# 默认 build 输出 dist/(Vite/Next 等)
DIST_DIR="${FRONTEND_DIR}/dist"
if [ ! -d "${DIST_DIR}" ]; then
    DIST_DIR="${FRONTEND_DIR}/build"  # CRA 风格
fi

echo "[push_frontend] rsync ${DIST_DIR}/ to ${REMOTE}:${FRONTEND_PATH}/"
rsync -avz --delete --partial --partial-dir=.rsync-partial \
    --exclude '._*' \
    "${DIST_DIR}/" "${REMOTE}:${FRONTEND_PATH}/"

echo "[push_frontend] done"
