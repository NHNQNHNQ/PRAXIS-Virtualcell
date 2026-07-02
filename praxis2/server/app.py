"""§3 step1 纯 ASGI Web 适配(M6 校准①:无 fastapi,FastAPI 是其路由糖;
M8 仍 uvicorn 启动;**M9 起 AuthMiddleware 包外层 + auth/me/info 路由
+ /api/chat-stream alias + user_id 来源 cookie**)。

路由零业务逻辑:取/建 session 的 QueryEngine,调 query(),事件流转 SSE 回吐
(对治 v1 把编排塞 chat.py,§2 边界)。

进程级单例(§11.1):store、限流器、PendingPermissionRegistry、repo、redis、email_gateway。
同 {user_id}:{session_id} 请求经 runtime/locks 串行化(§11.3)。
M9:user_id 来源切 cookie session resolve(scope["user"]),无 user → 401(§11.6 校准)。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from praxis2.admin.handlers import (
    handle_admin_audit_list,
    handle_admin_ledger_list,
    handle_admin_reconcile,
    handle_admin_stats,
    handle_admin_user_adjust,
    handle_admin_user_freeze,
    handle_admin_user_unfreeze,
    handle_admin_users_list,
)
from praxis2.admin.repo import AdminUserRepo, AuditRepo
from praxis2.agents.loader import resolve_agent
from praxis2.auth import routes as auth_routes
from praxis2.auth.middleware import AuthMiddleware
from praxis2.brains.migrate import DISCIPLINE_SLUGS
from praxis2.brains.system_prompt import build_chat_system_prompt
from praxis2.core.query import query
from praxis2.core.rmcp import get_phase
from praxis2.core.seams import MinimalCompactor
from praxis2.core.state import State
from praxis2.hooks.builtin import (
    advance_phase_on_real_retrieval,
    make_tool_use_presence_stop_hook,
)
from praxis2.llm.client import AnthropicClient
from praxis2.memory.session import SessionEntry, SessionStore, record_phase_transition, resume
from praxis2.proposals.handlers import (
    handle_admin_proposal_decide,
    handle_admin_proposal_list,
    handle_proposal_create,
    handle_proposal_list_mine,
)
from praxis2.proposals.repo import ProposalRepo
from praxis2.runtime.locks import InMemoryLockBackend, acquire_session_lock
from praxis2.runtime.pubsub import InMemoryEventBus, SessionChannel
from praxis2.runtime.ratelimit import Backpressure, RateLimiter
from praxis2.runtime.session_pool import SessionPool
from praxis2.server.chat_registry import build_chat_registry
from praxis2.server.permission_bridge import (
    BridgePermissionAdapter,
    PendingPermissionRegistry,
    ResolveResult,
)
from praxis2.server.sse import _map_kernel_event, sse_frame
from praxis2.store.base import Store
from praxis2.tools.bash import netns_available, scope_available, userns_available
from praxis2.tools.bash_policy import BashCommandPolicy
from praxis2.tools.permission import RetrieveFirstPermission
from praxis2.tools.runtools import SerialToolRunner

_logger = logging.getLogger("praxis2.server")


def _resolve_session_id(body: dict[str, Any]) -> str:
    """v0.16.1 patch:chat-stream session_id fallback 从固定 "default" 改 uuid4.hex。

    回归(v0.16.0 GA 评测发现):body 不传 session_id 时,旧代码用 "default" →
    所有匿名请求命中同 SessionPool slot → State.turn_count 跨请求累计 →
    超 max_turns=20 后立即 final reason=max_turns 死锁,需 restart gunicorn。

    修复:falsy(None/""/纯空格/缺字段)→ uuid4.hex(每请求 unique)。正常 FE
    (v0.15.0 起)显式传 session_id 命中复用路径,不受影响;只有 curl 裸测 /
    eval 脚本等边界 client 走 fallback,这些场景多是单 turn 不需复用。

    v0.16.3:
    - whitespace-only(如 "   ")也算 falsy(strip 后空)→ fallback,
      防 client 传纯空格绕过(否则 "   " 会变成有效 SessionPool key)。
    - fallback 触发时 logger.warning,便于监控异常 client(正常 FE 不该命中)。
    """
    sid = body.get("session_id")
    if not sid or not str(sid).strip():  # None / "" / 纯空格 / 缺字段 → fallback
        fallback = uuid.uuid4().hex
        _logger.warning(
            "chat-stream session_id 缺失/空,fallback uuid=%s(异常 client?正常 FE 应显式传)",
            fallback,
        )
        return fallback
    return str(sid)


async def _append_turn_entries(
    ss: SessionStore, state: State, seen_ids: set[int],
    *, user_id: str, session_id: str, phase_before: str,
) -> None:
    """GAP-B-1:把本轮 query() 新增(state.messages 中 id 不在 seen_ids 的)
    assistant / tool_result 消息 append 进 transcript(只 delta,不重写整盘)。
    每条新 uuid;读侧 load_transcript 已按 uuid dedup。user 纯文本已在 chat 路径
    单独落库,其 id 在 seen_ids → 跳过,不重复。

    对象身份(id)追踪而非位置索引:抗 reactive compact 对 state.messages 的
    reassign 截断——compact 删旧对象、保留切片仍是原对象(id 命中→跳过),本轮
    新 append 的对象 id 必不在 query 前快照(→持久)。seen_ids 仅 query 内局部:
    保留对象被 messages 持有不被 GC、id 稳定;唯一残余风险是 compact 丢弃的旧
    dict 被 GC 后地址被本轮新 dict 复用(→误跳一条 tool delta),但限于已退化的
    compact 路径 + same-size pymalloc 巧合,概率可忽略,且严格优于旧位置索引在
    compact 下的确定性漏持久。"""
    for msg in state.messages:
        if id(msg) in seen_ids:
            continue  # 历史 + 已单独持久的本轮 user → 跳过
        role = msg.get("role")
        if role == "assistant":
            etype = "assistant"
        elif role == "user":
            # 只持久 tool_result 回合(spec §123:role=user 且 content 含
            # tool_result block 才入库);stop_hook veto 等合成纯文本 user 消息
            # 跳过,否则 resume 后会被当成真实用户消息污染历史(query.py veto 路径)。
            content = msg.get("content")
            if isinstance(content, list) and any(
                isinstance(b, dict) and b.get("type") == "tool_result"
                for b in content
            ):
                etype = "user"
            else:
                continue
        else:
            continue  # 其他 role 不入库
        await ss.append_entry(SessionEntry(
            uuid=uuid.uuid4().hex, type=etype, content=msg.get("content"),
            user_id=user_id, session_id=session_id,
        ))
    # GAP-B-1 §9.1-A:最终相位≠轮前 → 补 phase-transition,保证重启 resume 的
    # rebuild_phase 能恢复相位(GAP-AH 检索先行门不误拦 resume 后首轮)。
    phase_after = get_phase(state)
    if phase_after.value != phase_before:
        await record_phase_transition(
            ss, user_id=user_id, session_id=session_id,
            to=phase_after, uuid_=uuid.uuid4().hex,
        )


# v2.0.1 §2.2:/api/agents 元数据表。slug 必须是 DISCIPLINE_SLUGS 的真子集 + "general",
# 与 resolve_agent(spec) 接受的 spec 完全一致(否则 FE 点击 sidebar 会 ValueError)。
# E501 noqa:视觉对齐 emoji/name/desc 单行,可读性优先于 100 字限制(13 项扫一眼即可)。
_AGENT_META: dict[str, dict[str, object]] = {
    "virtualcell": {"name": "VirtualCell 虚拟细胞", "emoji": "🧫", "desc": "扰动响应预测 / 跨物种 / abstain 可靠性 / Coordinator 编排",  # noqa: E501
                   "examples": ["Norman 双基因扰动预测", "这个 predictor 能用在 E. coli 上吗?", "Coordinator+abstain 给可靠预测"]},  # noqa: E501
}
# v2.0.2:Synth 已落地(brains/synth/),DISCIPLINE_SLUGS 自身已含 synth → 13 项。
# 不再需要 + ["synth"] 的拼接。
_DISCIPLINE_FOR_UI: list[str] = list(DISCIPLINE_SLUGS)


def _agent_meta(slug: str) -> dict[str, object]:
    m = _AGENT_META.get(slug, {})
    return {
        "slug": slug,
        "name": m.get("name", slug),
        "emoji": m.get("emoji", "🔬"),
        "desc": m.get("desc", ""),
        "examples": m.get("examples", []),
    }


@dataclass
class AppDeps:
    settings: Any
    store: Store
    api_key: str
    base_url: str
    # M9 新增 deps(认证 + 真后端)
    repo: Any
    redis: Any
    email_gateway: Any


def _parse_last_event_id_header(scope: dict) -> int:
    """SSE reconnect:client 携 `Last-Event-ID: N` header(EventSource 自动注入)。

    解析失败/缺失返 0(=不 replay)。ASGI scope headers 是 list[(bytes, bytes)],
    key 已小写但 client 可能大写发,小写比较稳。"""
    for k, v in scope.get("headers", []):
        if k.lower() == b"last-event-id":
            try:
                return int(v.decode("ascii", errors="replace").strip())
            except (ValueError, AttributeError):
                return 0
    return 0


async def _read_body(receive) -> dict:
    chunks = b""
    while True:
        msg = await receive()
        chunks += msg.get("body", b"")
        if not msg.get("more_body"):
            break
    if not chunks:
        return {}
    try:
        return json.loads(chunks)
    except ValueError:
        return {}


class _App:
    """纯 ASGI 应用。M9:auth 路由 merge + /api/chat-stream alias + user_id 来源 cookie。

    AuthMiddleware 包在 _App 外层:`make_app(deps)` 返回
    `_AppWithMiddleware(inner, deps.redis)`。
    """

    def __init__(self, deps: AppDeps) -> None:
        self._deps = deps
        self._locks = InMemoryLockBackend()
        # B.2(reviewer M6 C2):接 EventBus,实例级隔离(测试可注入)。
        # AppDeps 不加字段(M9 已足够多);需要真 Redis bus 时由 deps 旁路注入。
        self.event_bus = (
            getattr(deps, "event_bus", None) or InMemoryEventBus()
        )
        self.permission_registry = PendingPermissionRegistry()
        # D.1(reviewer M6 #9):接 SessionPool —— 同 (user_id, session_id) 复用
        # 服务端 State(messages/phase/recovery_attempts/stop_hook_reasons/
        # tool_use_context),不再每请求 State() 重置。LRU + 空闲 TTL 双驱逐;
        # 驱逐只丢内存副本,权威态在 store(§11.8)。默认 200 sessions × ~10KB
        # ≈ 2MB,小;TTL 1h 兼顾内存与会话热度。
        self._session_pool = SessionPool(max_size=200, idle_ttl_s=3600.0)
        # GAP-B-1 SP1:SessionStore 权威持久层(transcript→store blob)。
        # 镜像 ledger/files_repo 兜底:deps.repo._pool 不存在(FakeAuthRepo,
        # 测试)→ AttributeError → None,退回纯内存态(SessionPool 单层),零回归。
        try:
            _ = deps.repo._pool  # 仅探测存在性;真 IO 走 deps.store
            self._session_store: SessionStore | None = SessionStore(deps.store)
        except AttributeError:
            self._session_store = None
        # v0.17:MCP 连接池(lazy-once start,首个 chat-stream 请求触发)。
        # 构造时只 parse spec 不 spawn(sync 安全);spawn 在 _ensure_mcp(async)。
        from praxis2.mcp.config import parse_mcp_servers
        from praxis2.mcp.pool import MCPConnectionPool
        _mcp_specs = parse_mcp_servers(getattr(deps.settings, "mcp_servers_json", ""))
        self._mcp_pool = MCPConnectionPool(_mcp_specs)
        self._mcp_started = False
        self._mcp_lock = asyncio.Lock()
        # v0.9.1 staging hotfix:settings.static_root 非空 → 同 origin serve frontend SPA
        # 解 cookie 跨域死结(SameSite=Lax + HTTP + 跨 host:port 浏览器吞 cookie)
        from pathlib import Path as _Path
        _sr = getattr(deps.settings, "static_root", "")
        self._static_root: _Path | None = _Path(_sr).resolve() if _sr else None
        self.rate_limiter = RateLimiter(
            max_concurrent_per_user=2,
            user_qps=1000.0,
            global_llm_inflight=100,
            max_heavy_jobs_per_user=0,
        )
        # M9:Ledger 用于 /api/me/balance + register signup_gift
        from praxis2.accounting.ledger import Ledger
        try:
            ledger = Ledger(deps.repo._pool)  # PgAuthRepository 有 _pool
        except AttributeError:
            ledger = None   # FakeAuthRepository(测试)无 _pool,handler 兜底
        auth_deps = {
            "repo": deps.repo,
            "redis": deps.redis,
            "email_gateway": deps.email_gateway,
            "settings": deps.settings,
            "ledger": ledger,
        }
        # M10:FilesRepo(需要 _pool;FakeAuthRepository 无 _pool → None)
        from praxis2.files.repo import FilesRepo
        from praxis2.files.store_fs import FsStore
        try:
            files_repo = FilesRepo(deps.repo._pool)
        except AttributeError:
            files_repo = None   # 测试路径(FakeAuthRepository)
        fs_store = FsStore(deps.settings.files_root)
        # M10:boot warmup — 13 brain walk(~5s),失败不阻启动
        try:
            from praxis2.brains.profile import load_all_profiles as _lap
            _lap()
        except Exception:  # noqa: BLE001
            pass
        files_deps = {
            "repo": deps.repo,
            "files_repo": files_repo,
            "fs_store": fs_store,
            "settings": deps.settings,
        }
        self._files_deps = files_deps
        # M11.1 spawn — 构造 deps 与 LLMClient factory(每个 task 起一个新 client,避免共享连接)
        from praxis2.llm.client import LLMClient
        from praxis2.spawn.registry import SpawnRegistry
        from praxis2.spawn.repo import SpawnRepo
        try:
            spawn_repo = SpawnRepo(deps.repo._pool)
            spawn_pg_pool = deps.repo._pool
        except AttributeError:
            spawn_repo = None
            spawn_pg_pool = None
        self._spawn_registry = SpawnRegistry()
        self._spawn_deps = {
            "spawn_repo": spawn_repo,
            "spawn_registry": self._spawn_registry,
            "ledger": ledger,
            "pg_pool": spawn_pg_pool,
            "default_model": deps.settings.model,
            "max_tokens": deps.settings.max_tokens,
            "max_concurrent_per_user": deps.settings.spawn_max_concurrent_per_user,
            "price_in_per_m": deps.settings.llm_price_in_per_m_li,
            "price_out_per_m": deps.settings.llm_price_out_per_m_li,
            "partial_flush_chunks": deps.settings.spawn_partial_flush_chunks,
            "keep_last_per_user": deps.settings.spawn_keep_last_per_user,
            "llm_client_factory": lambda: LLMClient(
                api_key=deps.api_key, base_url=deps.base_url,
            ),
        }
        # M11.2 md — 构造 deps + ssh config
        from praxis2.md.repo import MdJobRepo
        from praxis2.md.ssh import SshConfig
        try:
            md_repo = MdJobRepo(deps.repo._pool)
        except AttributeError:
            md_repo = None
        ssh_cfg = SshConfig(
            host=deps.settings.hpc_ssh_host,
            user=deps.settings.hpc_ssh_user,
            key_path=deps.settings.hpc_ssh_key_path,
            timeout_s=deps.settings.hpc_ssh_timeout_s,
        )
        self._md_deps = {
            "md_repo": md_repo,
            "files_repo": files_repo,
            "fs_store": fs_store,
            "ledger": ledger,
            "pg_pool": spawn_pg_pool,                 # 复用 spawn 一样的 pool
            "ssh_cfg": ssh_cfg,
            "hpc_account": deps.settings.md_hpc_account,
            "max_concurrent_per_user": deps.settings.md_max_concurrent_per_user,
            "check_gpus_script_path": deps.settings.md_check_gpus_script_path,
            "md_gromacs_load_cmd": deps.settings.md_gromacs_load_cmd,
            "md_plumed_load_cmd": getattr(deps.settings, "md_plumed_load_cmd", ""),
            "md_mpi_load_cmd": getattr(deps.settings, "md_mpi_load_cmd", ""),
        }
        self._md_poll_lock = asyncio.Lock()  # asyncio 已在模块顶 import(I-2)
        self._md_poll_task = None
        # trajectories 端点挂在 files_routes 下,需要 md_repo + ssh_cfg;
        # 闭包持 files_deps 引用,__init__ 末注入即生效(请求还未到达)。
        files_deps["md_repo"] = md_repo
        files_deps["ssh_cfg"] = ssh_cfg
        # M12 admin v2 + proposals — 复用 spawn_pg_pool 与 ledger
        # FakeAuthRepository(测试)无 _pool → spawn_pg_pool 为 None,
        # repo 类即便 None pool 也可构,handlers 在 pg_pool 操作时报错由测试桩接住。
        self._admin_user_repo = AdminUserRepo(spawn_pg_pool, ledger)
        self._audit_repo = AuditRepo(spawn_pg_pool)
        self._proposal_repo = ProposalRepo(spawn_pg_pool)
        self._admin_deps = {
            "pg_pool": spawn_pg_pool,
            "admin_user_repo": self._admin_user_repo,
            "audit_repo": self._audit_repo,
            "reconcile_max_users": deps.settings.admin_reconcile_max_users,
        }
        self._proposal_deps = {
            "pg_pool": spawn_pg_pool,
            "proposal_repo": self._proposal_repo,
            "audit_repo": self._audit_repo,
            "proposals_per_user_per_day": deps.settings.proposals_per_user_per_day,
        }
        self._routes: dict[tuple[str, str], Callable] = {
            ("/chat/stream", "POST"): self._chat_stream,
            ("/chat/permission", "POST"): self._chat_permission,
            # v2.0.1 §3.8:同时注册 /admin/review/* 与 /api/admin/review/*,
            # legacy /admin/* 保留(老 staging 直接 curl 不破坏),前端走 /api/* 前缀。
            ("/admin/review/pending", "GET"): self._admin_list,
            ("/admin/review/approve", "POST"): self._admin_approve,
            ("/admin/review/reject", "POST"): self._admin_reject,
            ("/api/admin/review/pending", "GET"): self._admin_list,
            ("/api/admin/review/approve", "POST"): self._admin_approve,
            ("/api/admin/review/reject", "POST"): self._admin_reject,
            ("/api/chat-stream", "POST"): self._chat_stream,
            # v2.0.1 §2.2:前端 App.tsx 启动即调 /api/agents 加载 12 学科卡片。
            # 无此路由时 FE 永久 bootErr banner,主聊天链路虽能跑但 sidebar 空。
            ("/api/agents", "GET"): self._api_agents,
            ("/api/spawn", "POST"): self._spawn_post,
            ("/api/spawn/list", "GET"): self._spawn_list,
            ("/api/md/submit", "POST"): self._md_submit,
            ("/api/md/runs", "GET"): self._md_runs,
            ("/api/md/gpu-pool", "GET"): self._md_gpu_pool,
            # M12 admin v2 (8)
            ("/api/admin/users", "GET"): self._admin_users_list,
            ("/api/admin/reconcile", "POST"): self._admin_reconcile,
            ("/api/admin/ledger", "GET"): self._admin_ledger_list,
            ("/api/admin/audit-log", "GET"): self._admin_audit_list,
            ("/api/admin/stats", "GET"): self._admin_stats,
            # M12 proposals (5: user 2 + admin 1 list + admin 1 decide via dyn = 2 static)
            ("/api/proposals", "POST"): self._proposal_create,
            ("/api/me/proposals", "GET"): self._proposal_list_mine,
            # GAP-B-1 SP1:跨会话记忆会话列表(独立于 proposals 组)
            ("/api/me/sessions", "GET"): self._sessions_list_mine,
            ("/api/admin/proposals", "GET"): self._admin_proposal_list,
        }
        for (path, method), handler_name in auth_routes.ROUTES.items():
            handler_fn = getattr(auth_routes, handler_name)
            self._routes[(path, method)] = self._make_auth_handler(handler_fn, auth_deps)
        # M10:merge files_routes.ROUTES(4 个静态路径)
        from praxis2.server.routes import files as files_routes
        for (path, method), handler_name in files_routes.ROUTES.items():
            handler_fn = getattr(files_routes, handler_name)
            self._routes[(path, method)] = self._make_files_handler(handler_fn, files_deps)
        # M10.5 hotfix:merge stubs.ROUTES(5 个静态 stub 路径)
        from praxis2.server.routes import stubs as stubs_routes
        for (path, method), handler_name in stubs_routes.ROUTES.items():
            handler_fn = getattr(stubs_routes, handler_name)
            self._routes[(path, method)] = self._make_stub_handler(handler_fn)

    async def _ensure_mcp(self) -> None:
        """首个 chat-stream 请求时 lazy-once spawn MCP server(并发安全)。
        失败不抛(pool 内部 retry/skip + audit),不阻塞 chat。

        I-2 fix:asyncio.Lock double-check,且 _mcp_started 在 start_all 完成
        后才置 True —— 防并发首请求时 user B 在 A 的 spawn 未完成前拿到空工具列表
        (B 会在锁上等到 A spawn 完成)。
        """
        if self._mcp_started:
            return
        async with self._mcp_lock:
            if self._mcp_started:  # double-check:拿锁后再判(A 可能已完成)
                return
            try:
                await self._mcp_pool.start_all()
            except Exception:  # noqa: BLE001 — pool 内部已 retry/skip,双保险
                pass
            self._mcp_started = True  # spawn 完成后才置(确保后续请求拿到已就绪工具)

    def _make_auth_handler(self, fn, auth_deps):
        async def _wrapped(scope, receive, send):
            await fn(scope, receive, send, auth_deps)

        return _wrapped

    def _make_files_handler(self, fn, files_deps):
        async def _wrapped(scope, receive, send):
            await fn(scope, receive, send, files_deps)

        return _wrapped

    def _make_stub_handler(self, fn):
        async def _wrapped(scope, receive, send):
            await fn(scope, receive, send, {})

        return _wrapped

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            return
        path, method = scope["path"], scope["method"]
        # M10:动态路径 /api/files/{id} 和 /api/files/{id}/content
        if path.startswith("/api/files/") and path != "/api/files/usage":
            from praxis2.server.routes.files import (
                handle_files_delete,
                handle_files_download,
            )
            sub = path[len("/api/files/"):]
            parts = sub.split("/")
            if len(parts) == 1 and method == "DELETE":
                scope["path_params"] = {"file_id": parts[0]}
                await handle_files_delete(scope, receive, send, self._files_deps)
                return
            if len(parts) == 2 and parts[1] == "content" and method == "GET":
                scope["path_params"] = {"file_id": parts[0]}
                await handle_files_download(scope, receive, send, self._files_deps)
                return
        # M11.1 spawn 动态路径分发
        if path.startswith("/api/spawn/get/") and method == "GET":
            from praxis2.spawn.handlers import handle_spawn_get
            scope["path_params"] = {"task_id": path[len("/api/spawn/get/"):]}
            await handle_spawn_get(scope, receive, send, self._spawn_deps)
            return
        if path.startswith("/api/spawn/cancel/") and method == "POST":
            from praxis2.spawn.handlers import handle_spawn_cancel
            scope["path_params"] = {"task_id": path[len("/api/spawn/cancel/"):]}
            await handle_spawn_cancel(scope, receive, send, self._spawn_deps)
            return
        # GAP-B-1 SP2:GET /api/me/sessions/{id} 动态路由(带尾斜杠,不撞列表端点
        # /api/me/sessions)。返回该会话 transcript 的 user/assistant 文本 messages。
        if path.startswith("/api/me/sessions/") and method == "GET":
            scope["path_params"] = {"session_id": path[len("/api/me/sessions/"):]}
            await self._session_messages_mine(scope, receive, send)
            return

        # M11.2 md 动态路径
        if path.startswith("/api/md/jobs/") and method == "GET":
            tail = path[len("/api/md/jobs/"):]
            if "/" not in tail and tail:   # /api/md/jobs/{id}
                await self._ensure_md_poll_started()
                from praxis2.md.handlers import handle_md_get
                scope["path_params"] = {"job_id": tail}
                await handle_md_get(scope, receive, send, self._md_deps)
                return
        if path.startswith("/api/md/jobs/") and path.endswith("/cancel") and method == "POST":
            await self._ensure_md_poll_started()
            from praxis2.md.handlers import handle_md_cancel
            job_id = path[len("/api/md/jobs/"):-len("/cancel")]
            scope["path_params"] = {"job_id": job_id}
            await handle_md_cancel(scope, receive, send, self._md_deps)
            return

        # M12:动态 /api/admin/users/{id}/{adjust,freeze,unfreeze} POST
        if path.startswith("/api/admin/users/") and method == "POST":
            sub = path[len("/api/admin/users/"):]
            parts = sub.split("/")
            if len(parts) == 2 and parts[1] in ("adjust", "freeze", "unfreeze"):
                scope["path_params"] = {"user_id": parts[0]}
                if parts[1] == "adjust":
                    await self._admin_user_adjust(scope, receive, send)
                elif parts[1] == "freeze":
                    await self._admin_user_freeze(scope, receive, send)
                else:
                    await self._admin_user_unfreeze(scope, receive, send)
                return

        # M12:动态 /api/admin/proposals/{id}/decide POST
        if (path.startswith("/api/admin/proposals/")
                and path.endswith("/decide") and method == "POST"):
            pid = path[len("/api/admin/proposals/"):-len("/decide")]
            if pid and "/" not in pid:
                scope["path_params"] = {"proposal_id": pid}
                await self._admin_proposal_decide(scope, receive, send)
                return

        handler = self._routes.get((path, method))
        if handler is not None:
            await handler(scope, receive, send)
            return
        # v0.9.1 staging hotfix:同 origin serve frontend SPA(解 cookie 跨域)
        # PRAXIS_STATIC_ROOT 指 dist/ 时,GET 未命中 /api/* 走 SPA fallback
        if method == "GET" and self._static_root is not None:
            await self._serve_static(scope, send, path)
            return
        await self._json(send, 404, {"error": "not found"})

    async def _serve_static(self, scope, send, path: str) -> None:
        """同 origin SPA:精确文件存在 → 返;否则 / 或 unknown path → index.html(SPA router)。"""
        import os.path

        root = self._static_root
        assert root is not None
        # 安全:剥前导 /,resolve 后必须仍在 root 下(防 ../ 逃逸)
        rel = path.lstrip("/")
        candidate = (root / rel).resolve() if rel else (root / "index.html").resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            await self._json(send, 404, {"error": "not found"})
            return
        if not candidate.is_file():
            # SPA fallback:任何 unknown path 返 index.html(React Router 自己处理)
            candidate = (root / "index.html").resolve()
            if not candidate.is_file():
                await self._json(send, 404, {"error": "not found"})
                return
        # 简单 content-type 推断
        ext = os.path.splitext(candidate.name)[1].lower()
        ctype = {
            ".html": b"text/html; charset=utf-8",
            ".js":   b"application/javascript; charset=utf-8",
            ".css":  b"text/css; charset=utf-8",
            ".json": b"application/json",
            ".svg":  b"image/svg+xml",
            ".png":  b"image/png",
            ".ico":  b"image/x-icon",
            ".map":  b"application/json",
        }.get(ext, b"application/octet-stream")
        data = candidate.read_bytes()
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", ctype),
                (b"content-length", str(len(data)).encode()),
                (b"cache-control", b"no-cache" if ext == ".html" else b"public, max-age=3600"),
            ],
        })
        await send({"type": "http.response.body", "body": data})

    async def _json(self, send, status: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json; charset=utf-8")],
            }
        )
        await send({"type": "http.response.body", "body": data})

    async def _chat_stream(self, scope, receive, send) -> None:
        # M9:user_id 来源 cookie session(scope["user"]),无 → 401
        # fixup I1:统一 401 schema 为 {"error": "unauthorized", "reason": ...}
        user = scope.get("user")
        if not user:
            await self._json(
                send,
                401,
                {"error": "unauthorized", "reason": "未登录(§11.6 M9 校准)"},
            )
            return
        user_id = user["user_id"]
        body = await _read_body(receive)
        rl_decision = self.rate_limiter.acquire_session(user_id)
        if not rl_decision.allowed:
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-type", b"text/event-stream; charset=utf-8"),
                    ],
                }
            )
            bp = Backpressure.from_decision(rl_decision, eta_s=10.0)
            ev = bp.to_sse_event()
            frame = f"event: {ev['type']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
            await send(
                {
                    "type": "http.response.body",
                    "body": frame.encode(),
                    "more_body": False,
                }
            )
            return
        session_id = _resolve_session_id(body)
        message = body.get("message", "")
        # v0.15.0:auto 模式 = plan + 流末尾自动 POST /api/spawn。
        # FE 已发 body.mode ∈ {ask, plan, auto},仅 "auto" 触发末尾 spawn。
        chat_mode = body.get("mode") or "ask"
        # §7.5.0 / TEST-AGENT-FRAMEWORK §5:body.agent 决定 mode。
        # 非法 spec → 兜底 fallback "general"(开 SSE 流后发个 stream_event 告知)。
        agent_spec = body.get("agent") or "general"
        agent_route_warning: str | None = None
        try:
            selection = resolve_agent(agent_spec, user_query=message)
        except ValueError as e:
            agent_route_warning = (
                f"未知 agent spec {agent_spec!r},已 fallback general:{e}"
            )
            selection = resolve_agent("general", user_query=message)

        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/event-stream; charset=utf-8")],
            }
        )
        # B.2(reviewer M6 C2):接 EventBus —— event_id 由 bus 单一管理(§11.4),
        # 不再 nonlocal seq 各算各的;同 channel 跨连接(多标签页/重连)id 连续。
        # B.1 真流式语义保留:每 ev 即时 send,不 buffer。
        channel = SessionChannel(user_id=user_id, session_id=session_id).name()

        # Last-Event-ID replay:client reconnect 带 header → 补发历史 event,
        # 不重发已收(防乱序/丢事件,§11.4)。
        last_event_id = _parse_last_event_id_header(scope)
        if last_event_id > 0:
            replayed = await self.event_bus.replay(
                channel, last_event_id=last_event_id
            )
            for ev in replayed:
                # bus 里的 ev 已带 event_id 且已是前端协议名(publish 时入参就该是)
                # _map_kernel_event 对已知前端协议名直通,安全。
                frame = sse_frame(ev, event_id=ev["event_id"])
                await send(
                    {
                        "type": "http.response.body",
                        "body": frame.encode(),
                        "more_body": True,
                    }
                )

        async def push(event: dict) -> None:
            """map 内核事件 → SSE 前端协议名,publish 到 bus 取 event_id,
            再发 SSE frame(B.2)。bus 里存的就是前端 SSE 协议名 + event_id,
            replay 时无需重映射 / 重算 id。"""
            mapped = _map_kernel_event(event)
            ev = await self.event_bus.publish(channel, mapped)
            frame = sse_frame(ev, event_id=ev["event_id"])
            await send(
                {
                    "type": "http.response.body",
                    "body": frame.encode(),
                    "more_body": True,
                }
            )

        try:
            async with acquire_session_lock(self._locks, user_id, session_id):
                client = AnthropicClient(api_key=self._deps.api_key, base_url=self._deps.base_url)
                # §5 修复:不再 new 空 ToolRegistry(此前导致 query() 喂给
                # Anthropic API 的 tools=[] 永远为空,模型无法发起 tool_use)。
                # mode-aware:discipline agent 禁用 AgentTool(§7.5.4 防递归)。
                await self._ensure_mcp()
                bash_root = None
                bash_isolation = False
                bash_cgroup = False
                bash_netns = False
                if getattr(self._deps.settings, "bash_tool_enabled", False):
                    want_isolation = getattr(self._deps.settings, "bash_isolation", False)
                    want_netns = getattr(self._deps.settings, "bash_netns", False)
                    if (want_isolation and not userns_available()) or (
                        want_netns and not netns_available()
                    ):
                        # fail-closed:isolation/netns 任一启用却对应 namespace 不可用 → 整体不注册
                        # Bash(两者同属安全 namespace 前提,不单独降级——宁可不给 Bash 也不给
                        # "缺一层隔离"的 Bash,避免静默安全降级)。启动已 warning。
                        pass
                    else:
                        bash_root = os.path.join(self._deps.settings.files_root, user_id)
                        bash_isolation = want_isolation
                        bash_netns = want_netns
                        # cgroup fail-open:scope 不可用 → 降级 rlimit(去 cgroup,Bash 仍注册)
                        bash_cgroup = (
                            getattr(self._deps.settings, "bash_cgroup", False)
                            and scope_available()
                        )
                reg = build_chat_registry(
                    selection=selection,
                    mcp_tools=self._mcp_pool.all_tools(),
                    bash_sandbox_root=bash_root,
                    bash_isolation=bash_isolation,
                    bash_isolation_mask=getattr(self._deps.settings, "bash_isolation_mask", ""),
                    bash_cgroup=bash_cgroup,
                    bash_cgroup_mem_mb=getattr(self._deps.settings, "bash_cgroup_mem_mb", 1024),
                    bash_cgroup_cpu_pct=getattr(self._deps.settings, "bash_cgroup_cpu_pct", 100),
                    bash_netns=bash_netns,
                )
                if agent_route_warning:
                    # 非法 spec 兜底事件(可观测,§12),前端按 stream_event 容错
                    await push({"type": "stream_event", "original": {
                        "type": "agent_route_warning",
                        "message": agent_route_warning,
                        "fallback_to": "general",
                    }})

                # A.6(reviewer M6 C3):ASK 决策走 SSE bridge。B.1 后 emit_sse 直接是 push,
                # bridge 阻塞期间 control_request 即时出帧,用户能真 ASK→回复(B.1 之前
                # 因 buffered 必超时,bridge 形同摆设)。
                # v0.17 子项目2:base 换 BashCommandPolicy(非 Bash 工具透传 ALLOW,
                # 零回归;Bash 命令级黑/白/灰,ASK 经 BridgePermissionAdapter 弹前端)。
                # GAP-AH-1:外裹检索先行证据门(rmcp_op≠None 工具须本会话已成功检索才放行)
                base_perm = RetrieveFirstPermission(BashCommandPolicy())
                perm = BridgePermissionAdapter(
                    base_perm,
                    registry=self.permission_registry,
                    emit_sse=push,
                    user_id=user_id,
                    # A.6 fixup I2(reviewer):timeout 不再硬编码,由 settings 注入。
                    timeout_s=self._deps.settings.permission_ask_timeout_s,
                )
                runner = SerialToolRunner(
                    reg,
                    recovery_budget=self._deps.settings.recovery_budget,
                    permission=perm,
                    post_hooks=[advance_phase_on_real_retrieval],  # GAP-AH-1 检索→推进相位
                )
                # D.1(reviewer M6 #9):同 (user_id, session_id) 命中池 → 复用
                # State(messages/phase/recovery_attempts 等跨请求保留);miss → 新建
                # 并入池。本轮 user 消息追加到 messages 尾,query 内核负责追加
                # assistant/tool result(query.py §7.1.2)。
                st = self._session_pool.get(user_id, session_id)
                if st is None:
                    st = State()
                    # GAP-B-1:pool miss + 持久层可用 → 从 transcript resume 历史。
                    # resume() 完整编排(dedup→snip→relink→孤儿配对→中断注入→
                    # rebuild_phase);空 transcript → messages=[](等价新 State,零回归)。
                    if self._session_store is not None:
                        try:
                            await resume(
                                self._session_store, st,
                                user_id=user_id, session_id=session_id,
                            )
                        except Exception as exc:  # noqa: BLE001
                            # 持久层异常不阻塞 chat,降级空 State(今日行为);log
                            # warning 与本文件其他降级 fallback 一致(可观测)。
                            _logger.warning(
                                "resume 失败,降级空 State(user=%s session=%s):%r",
                                user_id, session_id, exc,
                            )
                    self._session_pool.put(user_id, session_id, st)
                st.messages.append({"role": "user", "content": message})
                # GAP-B-1:user 消息落 transcript(持久层可用时);失败不阻塞 chat(log 可观测)。
                if self._session_store is not None:
                    try:
                        await self._session_store.append_entry(SessionEntry(
                            uuid=uuid.uuid4().hex, type="user", content=message,
                            user_id=user_id, session_id=session_id,
                        ))
                    except Exception as exc:  # noqa: BLE001
                        _logger.warning(
                            "user 消息持久失败(user=%s session=%s):%r",
                            user_id, session_id, exc,
                        )
                # GAP-AH-2:veto 预算 per-user-turn(非 per-session)。池化 State 跨请求复用,
                # 不重置则一次 veto 后本会话 stop_hook 永久失效;每个新 user turn 给回 1 次预算
                # (turn 内 query() 重试不经此处,故 turn 内 ≤1 veto 的防循环仍成立)。
                st.stop_hook_veto_count = 0
                # 测试日志行3:新 user turn 重置"单次 query() 闭环"的进度/预算计数器。
                # 池化 State 跨请求复用,这些字段跨轮累计是设计外副作用:turn_count 累计误触
                # max_turns 熔断(query.py:57 零输出),recovery 预算被旧轮耗尽 → escalated 空响应。
                # 不碰 messages/相位/SessionStore,对 GAP-B-1/GAP-AH 正交。
                st.turn_count = 0
                st.transition = None
                st.recovery_attempts = 0
                st.max_output_tokens_recovery_count = 0
                st.max_tokens_boost = 0
                st.pending_stop_reasons.clear()
                st.usage_total = {"prompt_tokens": 0, "completion_tokens": 0}  # 计费:本轮重新累计
                # PLAN §11:把大脑案例/RMCP 规则/主路径 skill 摘要装进 system。
                # 此前 system=None 导致模型只看到 tools,不知何时调,推荐 .53 跑不了的方案。
                # 失败时退回 None(等价旧行为,不阻塞 chat)。
                try:
                    system_prompt = build_chat_system_prompt(selection, message)
                except Exception:  # noqa: BLE001
                    system_prompt = []
                # GAP-B-1:delta 起点用对象身份快照(抗 reactive compact 对 st.messages
                # 的 reassign 截断;位置索引 _prev_len 会越界漏持久 tool delta,见
                # compact-safe spec)。本轮 user 已单独持久,其 id 在快照内 → 不重复。
                _seen_ids = {id(m) for m in st.messages}
                _phase_before = get_phase(st).value  # GAP-B-1 §9.1-A:轮前相位
                # v0.15.0:auto 模式末尾 spawn 需要 buffer assistant text + end reason
                assistant_text: list[str] = []
                end_reason: str | None = None
                try:
                    async for ev in query(
                        st,
                        client=client,
                        registry=reg,
                        settings=self._deps.settings,
                        runner=runner,
                        compactor=MinimalCompactor(),
                        system=system_prompt or None,
                        stop_hook=make_tool_use_presence_stop_hook(),  # GAP-AH-2 终答证据门
                    ):
                        if ev.get("type") == "text" and isinstance(ev.get("text"), str):
                            assistant_text.append(ev["text"])
                        elif ev.get("type") == "end":
                            end_reason = ev.get("reason")
                        await push(ev)
                except Exception as e:  # noqa: BLE001
                    await push(
                        {
                            "type": "end",
                            "reason": "error",
                            "message": f"内核异常:{e!r}",
                        }
                    )
                finally:
                    await client.aclose()

                # 计费:本轮 LLM token 用量 × 单价 → consume(先答后扣,余额不足扣到 0)。
                # 失败不阻塞 chat(log)。仅 PG-backed(repo._pool 存在)扣;无 PG 零回归。
                try:
                    _pool = self._deps.repo._pool
                except AttributeError:
                    _pool = None
                if _pool is not None:
                    try:
                        import math  # noqa: PLC0415

                        from praxis2.accounting.ledger import Ledger  # noqa: PLC0415
                        _pt = int(st.usage_total.get("prompt_tokens", 0))
                        _ct = int(st.usage_total.get("completion_tokens", 0))
                        _cfg = self._deps.settings
                        _cost = math.ceil(
                            _pt * _cfg.llm_price_in_per_m_li / 1_000_000
                            + _ct * _cfg.llm_price_out_per_m_li / 1_000_000
                        )
                        if _cost > 0:
                            async with _pool.acquire() as _conn:
                                async with _conn.transaction():
                                    await Ledger(_pool).consume_capped(
                                        _conn, user_id, _cost, "chat", session_id,
                                        {"prompt_tokens": _pt, "completion_tokens": _ct},
                                    )
                    except Exception as exc:  # noqa: BLE001
                        _logger.warning(
                            "chat 扣费失败(user=%s session=%s):%r",
                            user_id, session_id, exc,
                        )

                # GAP-B-1:本轮 query 新增的 assistant/tool delta 落 transcript;
                # 失败不阻塞(log 可观测)。
                if self._session_store is not None:
                    try:
                        await _append_turn_entries(
                            self._session_store, st, _seen_ids,
                            user_id=user_id, session_id=session_id,
                            phase_before=_phase_before,
                        )
                    except Exception as exc:  # noqa: BLE001
                        _logger.warning(
                            "assistant/tool delta 持久失败(user=%s session=%s):%r",
                            user_id, session_id, exc,
                        )
                # GAP-B-1:query 内核对纯文本终答只存 last_assistant_text + SSE,不写进
                # state.messages(省 context,query.py:196),故 _append_turn_entries 的
                # delta 漏掉它 → 显式持久最终文本答复,否则 SP2 恢复看不到 assistant 散文
                # (验收②)。仅 stop 终答 + 非空文本(tool_use assistant 已在 delta 持久)。
                if self._session_store is not None and end_reason == "stop":
                    _final_text = "".join(assistant_text)
                    if _final_text.strip():
                        try:
                            await self._session_store.append_entry(SessionEntry(
                                uuid=uuid.uuid4().hex, type="assistant",
                                content=_final_text,
                                user_id=user_id, session_id=session_id,
                            ))
                        except Exception as exc:  # noqa: BLE001
                            _logger.warning(
                                "assistant 终答持久失败(user=%s session=%s):%r",
                                user_id, session_id, exc,
                            )
                # GAP-B-1:会话元数据 upsert(preview=本轮 user 消息截断 + updated_at),
                # 供 GET /api/me/sessions。pk=session_id(InMemoryStore/PgStore 通用主键)。
                # guard 用 _session_store(非 None ≡ PG-backed,与 transcript 持久同 gate):
                # 无 PG 时整体短路保持零回归;真 IO 走同源 _deps.store。
                if self._session_store is not None:
                    try:
                        await self._deps.store.meta_upsert("sessions", {
                            "user_id": user_id, "pk": session_id,
                            "preview": (message or "")[:40],
                            "updated_at": time.time(),
                        })
                    except Exception as exc:  # noqa: BLE001
                        _logger.warning(
                            "会话元数据 upsert 失败(user=%s session=%s):%r",
                            user_id, session_id, exc,
                        )

                # v0.15.0:chat 正常终答 + auto 模式 → 解析 SPEC → 自动 spawn,
                # push spawn_started/spawn_skipped SSE 让 FE 知道(SpawnModal 会自动轮询出)
                if chat_mode == "auto" and end_reason == "stop":
                    from praxis2.spawn.handlers import create_spawn_task  # noqa: PLC0415
                    from praxis2.spawn.spec_parser import (  # noqa: PLC0415
                        parse_executable_spec,
                    )
                    spec_prompt = parse_executable_spec("".join(assistant_text))
                    if spec_prompt is None:
                        await push({"type": "stream_event", "original": {
                            "type": "spawn_skipped",
                            "reason": "no_executable_spec",
                        }})
                    else:
                        spawn_model = body.get("model") or self._deps.settings.model
                        spawn_result = await create_spawn_task(
                            user_id, spec_prompt, spawn_model, self._spawn_deps,
                        )
                        if spawn_result["ok"]:
                            await push({"type": "stream_event", "original": {
                                "type": "spawn_started",
                                "task_id": spawn_result["task_id"],
                            }})
                        else:
                            await push({"type": "stream_event", "original": {
                                "type": "spawn_skipped",
                                "reason": spawn_result["error"],
                                **{k: v for k, v in spawn_result.items()
                                   if k not in ("ok", "error")},
                            }})
        finally:
            self.rate_limiter.release_session(user_id)
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def _chat_permission(self, scope, receive, send) -> None:
        # Phase A.5(reviewer M6 C4):必须先校验认证 + tenant 绑定。
        # 修复前:任何能拿到 rid(UUID hex 可能从日志/error/旁路漏)的攻击者
        #        都能替别人 allow / deny。
        # 修复后:无 cookie → 401;rid 属另一 user → 403;rid 不存在 → 404;owner → 200。
        user = scope.get("user")
        if not user:
            await self._json(
                send,
                401,
                {"error": "unauthorized", "reason": "未登录(§11.6 M9 校准)"},
            )
            return
        body = await _read_body(receive)
        rid = body.get("request_id", "")
        decision = body.get("decision", "deny")
        result = await self.permission_registry.resolve(
            rid, decision, caller_user_id=user["user_id"]
        )
        if result is ResolveResult.NOT_FOUND:
            await self._json(
                send,
                404,
                {"error": "not_found", "reason": "permission request not found or expired"},
            )
            return
        if result is ResolveResult.FORBIDDEN:
            await self._json(
                send,
                403,
                {"error": "forbidden", "reason": "cross-tenant permission resolve"},
            )
            return
        # OK 分支:wait() 的 finally 会兜底 pop;此处 cancel 是 fast-path,
        # 让 register 表在 handler 返回前尽早清理(防 wait 仍阻塞时占用)
        self.permission_registry.cancel(rid)
        await self._json(send, 200, {"ok": True})

    def _query_params(self, scope: dict) -> dict:
        from urllib.parse import parse_qs

        qs = parse_qs(scope.get("query_string", b"").decode())
        return {k: v[0] for k, v in qs.items()}

    async def _require_admin(self, scope, send) -> bool:
        """Phase A.1 / reviewer M9 C1:admin 端点强制 role == 'admin'。

        返回 True 表示已发送 401/403 响应,调用方应立即 return。
        - 未登录(scope["user"] 缺失)→ 401 unauthorized
        - 已登录但 role != 'admin'   → 403 forbidden(admin only)

        fixup I1:401/403 共用 schema {"error": "<short_code>", "reason": "<human>"},
        便于客户端按 error 字段稳定取错误码。
        fixup M1:rename _require_admin_or_403 → _require_admin
        (它现在既发 401 又发 403,status code 是实现细节不该编进名字)。
        """
        user = scope.get("user") or {}
        if not user:
            await self._json(
                send,
                401,
                {"error": "unauthorized", "reason": "未登录(§11.6 M9 校准)"},
            )
            return True
        if user.get("role") != "admin":
            await self._json(send, 403, {"error": "forbidden", "reason": "admin only"})
            return True
        return False

    async def _admin_list(self, scope, receive, send) -> None:
        from praxis2.server.routes.admin.review import handle_admin_list

        if await self._require_admin(scope, send):
            return
        user = scope["user"]
        p = self._query_params(scope)
        out = await handle_admin_list(
            self._deps.store,
            user_id=user["user_id"],
            scope=p.get("scope", "review"),
        )
        await self._json(send, 200, out)

    async def _admin_approve(self, scope, receive, send) -> None:
        from praxis2.server.routes.admin.review import handle_admin_approve

        if await self._require_admin(scope, send):
            return
        user = scope["user"]
        b = await _read_body(receive)
        out = await handle_admin_approve(
            self._deps.store,
            user_id=user["user_id"],
            scope=b.get("scope", "review"),
            cand_id=b.get("cand_id", ""),
            brain_slug=b.get("brain_slug", ""),
        )
        await self._json(send, 200, out)

    async def _api_agents(self, scope, receive, send) -> None:
        """v2.0.1 §2.2:返 12 学科 + general 元数据 + 当前 LLM model + 占位 pricing。

        - slug 单源对齐 `DISCIPLINE_SLUGS`(brains/migrate.py),
          确保 FE sidebar 列表 ↔ `resolve_agent(spec)` 完全一致。
        - examples 给一句 baseline,实际可由用户后续编辑大脑案例补充。
        - pricing 暂用 0 占位(M9 计费链路 carry,未跑通)。
        - 不要求登录(public endpoint,FE 在 AuthGate 前的 splash 阶段也调)。
        """
        agents = [_agent_meta(slug) for slug in _DISCIPLINE_FOR_UI]
        model = getattr(self._deps.settings, "model", "AWS-GPT-5.4")
        # v0.15.2(2026-06-01):FE chip 多列 aws-gpt-5.4(paratera 走 OpenAI GPT-5.4)。
        # carry:下次抽 settings.available_models env,避免 hardcode 第二个 model。
        extra = [m for m in ("aws-gpt-5.4",) if m != model]
        await self._json(send, 200, {
            "agents": agents,
            "models": [model, *extra],
            "default_model": model,
            "pricing": {
                "input_per_million_li": 0,
                "output_per_million_li": 0,
                "markup_x": 1.0,
            },
        })

    async def _admin_reject(self, scope, receive, send) -> None:
        from praxis2.server.routes.admin.review import handle_admin_reject

        if await self._require_admin(scope, send):
            return
        user = scope["user"]
        b = await _read_body(receive)
        out = await handle_admin_reject(
            self._deps.store,
            user_id=user["user_id"],
            scope=b.get("scope", "review"),
            cand_id=b.get("cand_id", ""),
            reason=b.get("reason", ""),
        )
        await self._json(send, 200, out)

    async def _spawn_post(self, scope, receive, send) -> None:
        from praxis2.spawn.handlers import handle_spawn_post
        await handle_spawn_post(scope, receive, send, self._spawn_deps)

    async def _spawn_list(self, scope, receive, send) -> None:
        from praxis2.spawn.handlers import handle_spawn_list
        await handle_spawn_list(scope, receive, send, self._spawn_deps)

    async def _md_submit(self, scope, receive, send) -> None:
        await self._ensure_md_poll_started()
        from praxis2.md.handlers import handle_md_submit
        await handle_md_submit(scope, receive, send, self._md_deps)

    async def _md_runs(self, scope, receive, send) -> None:
        await self._ensure_md_poll_started()
        from praxis2.md.handlers import handle_md_runs
        await handle_md_runs(scope, receive, send, self._md_deps)

    async def _md_gpu_pool(self, scope, receive, send) -> None:
        from praxis2.md.handlers import handle_md_gpu_pool
        await handle_md_gpu_pool(scope, receive, send, self._md_deps)

    # ---- M12 admin v2 ----
    async def _admin_users_list(self, scope, receive, send) -> None:
        await handle_admin_users_list(scope, receive, send, self._admin_deps)

    async def _admin_user_adjust(self, scope, receive, send) -> None:
        await handle_admin_user_adjust(scope, receive, send, self._admin_deps)

    async def _admin_user_freeze(self, scope, receive, send) -> None:
        await handle_admin_user_freeze(scope, receive, send, self._admin_deps)

    async def _admin_user_unfreeze(self, scope, receive, send) -> None:
        await handle_admin_user_unfreeze(scope, receive, send, self._admin_deps)

    async def _admin_reconcile(self, scope, receive, send) -> None:
        await handle_admin_reconcile(scope, receive, send, self._admin_deps)

    async def _admin_ledger_list(self, scope, receive, send) -> None:
        await handle_admin_ledger_list(scope, receive, send, self._admin_deps)

    async def _admin_audit_list(self, scope, receive, send) -> None:
        await handle_admin_audit_list(scope, receive, send, self._admin_deps)

    async def _admin_stats(self, scope, receive, send) -> None:
        await handle_admin_stats(scope, receive, send, self._admin_deps)

    # ---- M12 proposals ----
    async def _proposal_create(self, scope, receive, send) -> None:
        await handle_proposal_create(scope, receive, send, self._proposal_deps)

    async def _proposal_list_mine(self, scope, receive, send) -> None:
        await handle_proposal_list_mine(scope, receive, send, self._proposal_deps)

    async def _sessions_list_mine(self, scope, receive, send) -> None:
        """GAP-B-1:GET /api/me/sessions —— 当前用户会话列表(最近活动置顶)。"""
        user = scope.get("user")
        if not user:
            await self._json(
                send, 401, {"error": "unauthorized", "reason": "未登录"}
            )
            return
        if self._session_store is None:
            await self._json(send, 200, {"sessions": []})  # 无 PG,零回归
            return
        rows = await self._deps.store.meta_list("sessions", user["user_id"])
        rows.sort(key=lambda r: r.get("updated_at", 0.0), reverse=True)
        await self._json(send, 200, {"sessions": [
            {"session_id": r.get("pk"), "preview": r.get("preview", ""),
             "updated_at": r.get("updated_at", 0.0)}
            for r in rows
        ]})

    async def _session_messages_mine(self, scope, receive, send) -> None:
        """GAP-B-1 SP2:GET /api/me/sessions/{id} —— 返回该会话 transcript 的
        user/assistant 纯文本 messages(供前端懒填充历史显示)。tool_use/
        tool_result(content 是 list)与 phase-transition 跳过。"""
        user = scope.get("user")
        if not user:
            await self._json(
                send, 401, {"error": "unauthorized", "reason": "未登录"}
            )
            return
        if self._session_store is None:
            await self._json(send, 200, {"messages": []})  # 无 PG,零回归
            return
        session_id = scope.get("path_params", {}).get("session_id", "")
        seq = await self._session_store.load_transcript(
            user_id=user["user_id"], session_id=session_id)
        messages = [
            {"role": e.type, "text": e.content, "ts": e.timestamp}
            for e in seq
            if e.type in ("user", "assistant") and isinstance(e.content, str)
        ]
        await self._json(send, 200, {"messages": messages})

    async def _admin_proposal_list(self, scope, receive, send) -> None:
        await handle_admin_proposal_list(scope, receive, send, self._proposal_deps)

    async def _admin_proposal_decide(self, scope, receive, send) -> None:
        await handle_admin_proposal_decide(scope, receive, send, self._proposal_deps)

    async def _ensure_md_poll_started(self) -> None:
        """首次 md 请求时启动 poll worker。idempotent + lock 防并发首请求双启。"""
        if self._md_poll_task is not None and not self._md_poll_task.done():
            return
        if self._md_deps["md_repo"] is None:
            return
        async with self._md_poll_lock:
            if self._md_poll_task is not None and not self._md_poll_task.done():
                return
            import asyncio

            from praxis2.md.poll_worker import run_poll_loop
            self._md_poll_task = asyncio.create_task(run_poll_loop(
                cfg=self._md_deps["ssh_cfg"],
                repo=self._md_deps["md_repo"],
                ledger=self._md_deps["ledger"],
                pg_pool=self._md_deps["pg_pool"],
                interval_s=self._deps.settings.md_poll_interval_s,
                free_cpu_h=self._deps.settings.md_free_cpu_hours_per_job,
                price_gpu=self._deps.settings.md_price_gpu_per_h_li,
                price_cpu=self._deps.settings.md_price_cpu_per_h_li,
            ))


class _CorsMiddleware:
    """v0.9.1 staging hotfix:跨域 + Cookie credentials 支持(§11.4)。

    frontend(`.40:8080`)调 backend(`.53:8001`)需要 CORS preflight 通过 +
    `Access-Control-Allow-Credentials: true`(否则浏览器吞 Set-Cookie)。
    白名单 origin 从 settings.allowed_origins 来(空 list = 同 origin,无 CORS 头)。
    """

    def __init__(self, app, *, allowed_origins: list[str]) -> None:
        self._app = app
        self._allow = set(allowed_origins)

    def _cors_headers(self, origin: bytes) -> list[tuple[bytes, bytes]]:
        if not origin or origin.decode() not in self._allow:
            return []
        return [
            (b"access-control-allow-origin", origin),
            (b"access-control-allow-credentials", b"true"),
            (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
            (b"access-control-allow-headers", b"content-type, cookie, last-event-id"),
            (b"access-control-expose-headers", b"set-cookie"),
            (b"vary", b"Origin"),
        ]

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            return await self._app(scope, receive, send)
        headers = dict(scope.get("headers") or [])
        origin = headers.get(b"origin", b"")

        if scope["method"] == "OPTIONS":
            await send({
                "type": "http.response.start",
                "status": 204,
                "headers": self._cors_headers(origin),
            })
            await send({"type": "http.response.body", "body": b""})
            return

        cors = self._cors_headers(origin)

        async def wrapped_send(msg):
            if msg["type"] == "http.response.start" and cors:
                existing = list(msg.get("headers", []))
                msg = {**msg, "headers": existing + cors}
            await send(msg)

        await self._app(scope, receive, wrapped_send)


class _AppWithMiddleware:
    """组合:CORS + AuthMiddleware + _App,_app 属性给测试访问内层 _routes。"""

    def __init__(
        self,
        app: _App,
        redis_client,
        *,
        pepper: str,
        allowed_origins: list[str] | None = None,
    ) -> None:
        self._app = app
        self._auth = AuthMiddleware(app, redis_client=redis_client, pepper=pepper)
        self._cors = _CorsMiddleware(self._auth, allowed_origins=allowed_origins or [])
        # 暴露给现有测试:rate_limiter / permission_registry
        self.rate_limiter = app.rate_limiter
        self.permission_registry = app.permission_registry

    async def __call__(self, scope, receive, send) -> None:
        await self._cors(scope, receive, send)


def make_app(deps: AppDeps) -> _AppWithMiddleware:
    """构造 ASGI app(CORS + AuthMiddleware 外层 + _App 内层)。"""
    inner = _App(deps)
    origins = getattr(deps.settings, "allowed_origins", "")
    if isinstance(origins, str):
        origin_list = [o.strip() for o in origins.split(",") if o.strip()]
    else:
        origin_list = list(origins)
    return _AppWithMiddleware(
        inner,
        deps.redis,
        pepper=deps.settings.password_pepper,
        allowed_origins=origin_list,
    )


class _LifespanApp:
    """ASGI app wrapper:lifespan.startup 时 init PG/Redis pool(必须 in running loop)。

    v0.9.1 hotfix(staging E.7 暴露):原 make_app_default 用 asyncio.new_event_loop()
    + loop.run_until_complete() 在 uvicorn worker 启动时被调,worker 已在 running loop
    内 → RuntimeError "Cannot run the event loop while another loop is running"。
    fix:lifespan.startup 真 await,符合 ASGI lifespan 协议(§11.1)。
    """

    def __init__(self, settings) -> None:
        self._settings = settings
        self._inner: _AppWithMiddleware | None = None
        # 注:此判断与 _chat_stream 的 fail-closed 逻辑镜像(bash_tool_enabled &
        # bash_isolation & !userns_available),改动需两处同步。
        # fail-closed 可观测:启用隔离但 userns 不可用 → 启动时 warning,BashTool 不注册
        if (
            getattr(settings, "bash_tool_enabled", False)
            and getattr(settings, "bash_isolation", False)
            and not userns_available()
        ):
            _logger.warning(
                "PRAXIS_BASH_ISOLATION=true 但 userns 不可用(unshare 探测失败),"
                "fail-closed:BashTool 将不注册。需启用 unprivileged userns 或关闭隔离。"
            )
        # 注:与 _chat_stream 的 cgroup fail-open 逻辑镜像(bash_tool_enabled &
        # bash_cgroup & !scope_available),改动需两处同步。
        if (
            getattr(settings, "bash_tool_enabled", False)
            and getattr(settings, "bash_cgroup", False)
            and not scope_available()
        ):
            _logger.warning(
                "PRAXIS_BASH_CGROUP=true 但 systemd-run --scope 不可用,"
                "fail-open 降级 rlimit(资源限制仅覆盖直接子进程,孙子进程可逃逸)。"
            )
        # 注:与 _chat_stream 的 netns fail-closed 逻辑镜像(bash_tool_enabled &
        # bash_netns & !netns_available),改动需两处同步。
        if (
            getattr(settings, "bash_tool_enabled", False)
            and getattr(settings, "bash_netns", False)
            and not netns_available()
        ):
            _logger.warning(
                "PRAXIS_BASH_NETNS=true 但 user+net namespace 不可用(unshare 探测失败),"
                "fail-closed:BashTool 将不注册。需启用 unprivileged userns 或关闭网络隔离。"
            )

    async def _ensure_init(self) -> None:
        if self._inner is not None:
            return
        from praxis2.auth.email import make_email_gateway
        from praxis2.auth.repository_pg import PgAuthRepository
        from praxis2.store.pg import PgStore, make_pg_pool
        from praxis2.store.redis import make_redis_client

        pool = await make_pg_pool(self._settings.db_url)
        redis = make_redis_client(self._settings.redis_url)
        # 用 make_app() 工厂统一拼接(防遗漏 CORS allowed_origins 等中间件配置)
        self._inner = make_app(
            AppDeps(
                settings=self._settings,
                store=PgStore(pool),
                api_key=self._settings.anthropic_api_key,
                base_url=self._settings.anthropic_base_url,
                repo=PgAuthRepository(pool),
                redis=redis,
                email_gateway=make_email_gateway(self._settings),
            )
        )

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            while True:
                msg = await receive()
                if msg["type"] == "lifespan.startup":
                    try:
                        await self._ensure_init()
                        await send({"type": "lifespan.startup.complete"})
                    except Exception as e:  # noqa: BLE001
                        await send(
                            {
                                "type": "lifespan.startup.failed",
                                "message": f"{type(e).__name__}: {e}",
                            }
                        )
                        return
                elif msg["type"] == "lifespan.shutdown":
                    # v0.17 注:MCP pool 的 close_all 故意不在此调用 —— start_all 在首个
                    # chat-stream 请求的 task spawn,而 shutdown 在另一 task,跨 task 退出
                    # anyio cancel scope 必抛 RuntimeError(pool.close_all 已内部降级吞)。
                    # 优雅关闭跨 task 做不到,子进程由 OS 在 worker 退出时兜底回收。
                    # close_all 保留供单测 + 未来 worker-task 模式(v0.18)用。
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        else:
            # http/websocket:确保已 init(并发首请求安全:_ensure_init 内幂等)
            await self._ensure_init()
            assert self._inner is not None
            await self._inner(scope, receive, send)


def make_app_default():
    """gunicorn CMD 入口工厂:返 _LifespanApp,真 init 推到 lifespan.startup(§11.1)。

    生产部署用法:

        gunicorn -c deploy/gunicorn.conf.py praxis2.server.app:make_app_default

    M9:除 Anthropic settings,还需要 db_url/redis_url/password_pepper(必填,fail-fast)。
    PG/Redis 真后端 + auth 子包 + AuthMiddleware。
    """
    from praxis2.config import load_from_env

    settings = load_from_env()  # sync,fail-fast 即崩
    return _LifespanApp(settings)
