"""Apply session, request, model, and resource concurrency limits."""

import time
from dataclasses import dataclass


class TokenBucket:
    def __init__(self, *, capacity: float, refill_per_s: float) -> None:
        self._cap = capacity
        self._refill = refill_per_s
        self._tokens = float(capacity)
        self._last = time.monotonic()

    def _replenish(self) -> None:
        now = time.monotonic()
        self._tokens = min(self._cap, self._tokens + (now - self._last) * self._refill)
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
    http_status: int = 200
    queue_position: int = 0
    reason: str = ""


@dataclass
class Backpressure:
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
            "message": f"Resource backpressure:{self.reason}(queued to limit overload)",
        }

    @classmethod
    def from_decision(cls, d: "RateLimitDecision", *, eta_s: float) -> "Backpressure":

        if d.allowed:
            raise ValueError("Backpressure.from_decision requires allowed=False")
        return cls(
            http_status=d.http_status,
            queue_position=d.queue_position,
            eta_s=eta_s,
            reason=d.reason,
        )


class RateLimiter:
    def __init__(
        self,
        *,
        max_concurrent_per_user: int,
        user_qps: float,
        global_llm_inflight: int,
        max_heavy_jobs_per_user: int = 0,
    ) -> None:
        self._max_concurrent = max_concurrent_per_user
        self._user_qps = user_qps
        self._global_max = global_llm_inflight
        self._max_heavy = max_heavy_jobs_per_user
        self._sessions: dict[str, int] = {}
        self._qps_buckets: dict[str, TokenBucket] = {}
        self._llm_inflight = 0
        self._llm_queue_seq = 0
        self._heavy_jobs: dict[str, int] = {}

    def acquire_session(self, user_id: str) -> RateLimitDecision:
        cur = self._sessions.get(user_id, 0)
        if cur >= self._max_concurrent:
            return RateLimitDecision(
                allowed=False,
                http_status=429,
                queue_position=cur - self._max_concurrent + 1,
                reason="Per-user concurrent session limit",
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
        return RateLimitDecision(allowed=False, http_status=429, reason="Per-user request rate limit")

    def acquire_llm_slot(self, user_id: str) -> RateLimitDecision:
        if self._llm_inflight >= self._global_max:
            self._llm_queue_seq += 1
            return RateLimitDecision(
                allowed=False,
                http_status=429,
                queue_position=self._llm_queue_seq,
                reason="Global model concurrency limit",
            )
        self._llm_inflight += 1
        return RateLimitDecision(allowed=True)

    def release_llm_slot(self, user_id: str) -> None:
        self._llm_inflight = max(0, self._llm_inflight - 1)

    def acquire_heavy_job(self, user_id: str) -> RateLimitDecision:

        cur = self._heavy_jobs.get(user_id, 0)
        if cur >= self._max_heavy:
            return RateLimitDecision(
                allowed=False,
                http_status=429,
                queue_position=cur - self._max_heavy + 1,
                reason="Per-user resource-intensive job limit",
            )
        self._heavy_jobs[user_id] = cur + 1
        return RateLimitDecision(allowed=True)

    def release_heavy_job(self, user_id: str) -> None:
        self._heavy_jobs[user_id] = max(0, self._heavy_jobs.get(user_id, 0) - 1)
