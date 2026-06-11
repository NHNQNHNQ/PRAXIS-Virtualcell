"""§11.2/S10 限流背压。两条独立通道:通道 A LLM 对话(本模块落地)、
通道 B 重算力作业(M7,§11.5 不在本模块)。

限流三层:① 每用户并发会话上限 + 每用户 QPS 令牌桶;② 全局 LLM
上游并发闸(配合 D4 单上游,最大在飞超过则排队);③ 过载 429 +
排队位次/ETA(经 SSE error/queue_position 事件,不静默丢)。
**背压优先于失败**:宁排队不雪崩(§11.2)。"""

import time
from dataclasses import dataclass


class TokenBucket:
    """令牌桶:capacity 容量 + refill_per_s 每秒回填(封顶 capacity)。"""

    def __init__(self, *, capacity: float, refill_per_s: float) -> None:
        self._cap = capacity
        self._refill = refill_per_s
        self._tokens = float(capacity)
        self._last = time.monotonic()

    def _replenish(self) -> None:
        now = time.monotonic()
        self._tokens = min(
            self._cap, self._tokens + (now - self._last) * self._refill
        )
        self._last = now

    def try_take(self, n: float = 1.0) -> bool:
        self._replenish()
        if self._tokens >= n:
            self._tokens -= n
            return True
        return False


@dataclass
class RateLimitDecision:
    allowed: bool
    http_status: int = 200       # 过载 429(S10)
    queue_position: int = 0      # SSE queue_position 事件用
    reason: str = ""


@dataclass
class Backpressure:
    """过载经 SSE error/queue_position 回吐(§7.6.3,不静默丢,不崩)。"""

    http_status: int
    queue_position: int
    eta_s: float
    reason: str

    def to_sse_event(self) -> dict:
        return {
            "type": "error",
            "http_status": self.http_status,
            "queue_position": self.queue_position,
            "eta_s": self.eta_s,
            "message": f"过载背压:{self.reason}(已排队,宁排队不雪崩)",
        }

    @classmethod
    def from_decision(
        cls, d: "RateLimitDecision", *, eta_s: float
    ) -> "Backpressure":
        """统一 RateLimitDecision → Backpressure 映射(M7 carry)。
        allowed=True 不该转 Backpressure → 抛 ValueError(语义错)。"""
        if d.allowed:
            raise ValueError(
                "Backpressure.from_decision 仅用于拒绝决策;allowed=True 决策"
                "无需转 Backpressure(M6 carry,DRY)"
            )
        return cls(
            http_status=d.http_status,
            queue_position=d.queue_position,
            eta_s=eta_s,
            reason=d.reason,
        )


class RateLimiter:
    """通道 A 限流:每用户并发会话上限 + 每用户 QPS 桶 + 全局 LLM 闸。
    第一版同步内存计数(单 worker 正确性可测);多 worker 下计数经
    Redis 原子计数,接口位标 integration(M6 校准②,留装 docker 后)。"""

    def __init__(
        self, *, max_concurrent_per_user: int, user_qps: float,
        global_llm_inflight: int,
        max_heavy_jobs_per_user: int = 0,  # M7 通道 B(默认 0 即未启用)
    ) -> None:
        self._max_concurrent = max_concurrent_per_user
        self._user_qps = user_qps
        self._global_max = global_llm_inflight
        self._max_heavy = max_heavy_jobs_per_user
        self._sessions: dict[str, int] = {}      # user_id -> 在用会话数
        self._qps_buckets: dict[str, TokenBucket] = {}
        self._llm_inflight = 0
        self._llm_queue_seq = 0
        self._heavy_jobs: dict[str, int] = {}  # M7 通道 B

    def acquire_session(self, user_id: str) -> RateLimitDecision:
        cur = self._sessions.get(user_id, 0)
        if cur >= self._max_concurrent:
            # 单调递增 per-user 入队序号留 M7(本版返回超出量+1,
            # 前端可见排队信号但不递增,§11.2 多 worker Redis 原子计数同此办法)
            return RateLimitDecision(
                allowed=False, http_status=429,
                queue_position=cur - self._max_concurrent + 1,
                reason="每用户并发会话上限",
            )
        self._sessions[user_id] = cur + 1
        return RateLimitDecision(allowed=True)

    def release_session(self, user_id: str) -> None:
        self._sessions[user_id] = max(0, self._sessions.get(user_id, 0) - 1)

    def check_qps(self, user_id: str) -> RateLimitDecision:
        b = self._qps_buckets.get(user_id)
        if b is None:
            b = TokenBucket(capacity=self._user_qps, refill_per_s=self._user_qps)
            self._qps_buckets[user_id] = b
        if b.try_take():
            return RateLimitDecision(allowed=True)
        return RateLimitDecision(
            allowed=False, http_status=429, reason="每用户 QPS 上限"
        )

    def acquire_llm_slot(self, user_id: str) -> RateLimitDecision:
        if self._llm_inflight >= self._global_max:
            self._llm_queue_seq += 1
            return RateLimitDecision(
                allowed=False, http_status=429,
                queue_position=self._llm_queue_seq,
                reason="全局 LLM 上游并发闸(D4 单上游,排队不雪崩)",
            )
        self._llm_inflight += 1
        return RateLimitDecision(allowed=True)

    def release_llm_slot(self, user_id: str) -> None:
        self._llm_inflight = max(0, self._llm_inflight - 1)

    def acquire_heavy_job(self, user_id: str) -> RateLimitDecision:
        """通道 B 重算力作业并发上限(M7,与通道 A LLM 独立,§11.5)。"""
        cur = self._heavy_jobs.get(user_id, 0)
        if cur >= self._max_heavy:
            return RateLimitDecision(
                allowed=False, http_status=429,
                queue_position=cur - self._max_heavy + 1,
                reason="每用户重算力作业并发上限(通道 B)",
            )
        self._heavy_jobs[user_id] = cur + 1
        return RateLimitDecision(allowed=True)

    def release_heavy_job(self, user_id: str) -> None:
        self._heavy_jobs[user_id] = max(0, self._heavy_jobs.get(user_id, 0) - 1)

    async def acquire_email_send(
        self, email: str, *, redis_client, ttl_s: int = 60
    ) -> RateLimitDecision:
        """M9:60s/email send-code 频控(§11.2 单一限流入口,接 redis 真后端)。"""
        from praxis2.store.redis import email_throttle_check

        ok = await email_throttle_check(redis_client, email, ttl_s=ttl_s)
        if ok:
            return RateLimitDecision(allowed=True, reason="ok")
        return RateLimitDecision(
            allowed=False, http_status=429, reason="email_send_throttled_60s"
        )
