"""§11.5 公平调度:每用户并发配额 + 加权公平队列 + 全局上限。

防单用户占满 GPU 饿死他人:① 每用户并发作业配额;② 加权公平队列(按
优先级权重,默认 1.0);③ 全局队列上限(满则硬拒,排队 vs 拒绝在
ResourceGate 层决策,本层只管硬约束)。

配额/权重在 `config.py` 单一源(M7 第一版用 QuotaConfig 显式构造,
M8 接入 config.py)。**通道 B 限流在 ratelimit.py 集成**(M7 Task 9),
本模块只做调度算法。"""

from collections import deque
from dataclasses import dataclass


@dataclass
class QuotaConfig:
    max_concurrent_per_user: int
    global_max_queued: int


@dataclass
class UserQuotaState:
    running: int = 0
    queued: int = 0

    def inc_running(self) -> None:
        self.running += 1

    def dec_running(self) -> None:
        self.running = max(0, self.running - 1)

    def inc_queued(self) -> None:
        self.queued += 1

    def dec_queued(self) -> None:
        self.queued = max(0, self.queued - 1)


class Quota:
    """每用户并发配额 + 全局队列上限。"""

    def __init__(self, config: QuotaConfig) -> None:
        self._cfg = config
        self._users: dict[str, UserQuotaState] = {}
        self._global_queued = 0

    def _state(self, user_id: str) -> UserQuotaState:
        return self._users.setdefault(user_id, UserQuotaState())

    def try_acquire(self, user_id: str) -> bool:
        """尝试占一个并发槽(running)。超个人配额则拒。"""
        s = self._state(user_id)
        if s.running >= self._cfg.max_concurrent_per_user:
            return False
        s.inc_running()
        return True

    def release(self, user_id: str) -> None:
        self._state(user_id).dec_running()

    def try_enqueue(self, user_id: str) -> bool:
        """尝试入全局排队队列。满则拒(硬约束;排队 vs 拒绝由 ResourceGate)。"""
        if self._global_queued >= self._cfg.global_max_queued:
            return False
        self._state(user_id).inc_queued()
        self._global_queued += 1
        return True

    def dequeue(self, user_id: str) -> None:
        """出队(本人作业被调度起来,从排队转 running)。"""
        s = self._state(user_id)
        if s.queued > 0:
            s.dec_queued()
            self._global_queued -= 1

    def global_queued(self) -> int:
        return self._global_queued


@dataclass
class _FairEntry:
    user_id: str
    weight: float
    job_id: str
    enqueue_seq: int = 0  # FIFO tie-breaker(同 (weight, queued_count) 时)


class FairQueue:
    """加权公平队列(总纲 §11.5)。

    排序键:(-weight, queued_count, enqueue_seq)
    - weight 越大优先(负号让 max 在前)
    - 同 weight:queued_count 少的用户优先(防饥饿:已排很多的用户让位)
    - 完全平局:FIFO(enqueue_seq 递增)
    """

    def __init__(self) -> None:
        self._entries: deque[_FairEntry] = deque()
        self._queued_per_user: dict[str, int] = {}
        self._seq = 0

    def enqueue(self, user_id: str, *, weight: float, job_id: str) -> None:
        self._seq += 1
        self._entries.append(
            _FairEntry(
                user_id=user_id, weight=weight, job_id=job_id,
                enqueue_seq=self._seq,
            )
        )
        self._queued_per_user[user_id] = (
            self._queued_per_user.get(user_id, 0) + 1
        )

    def dequeue(self) -> "dict | None":
        if not self._entries:
            return None
        # 排序键:(-weight, queued_count[user], enqueue_seq)
        best_idx = 0
        best_key = self._key_for(self._entries[0])
        for i, e in enumerate(self._entries):
            k = self._key_for(e)
            if k < best_key:
                best_key = k
                best_idx = i
        chosen = self._entries[best_idx]
        del self._entries[best_idx]
        self._queued_per_user[chosen.user_id] -= 1
        if self._queued_per_user[chosen.user_id] <= 0:
            del self._queued_per_user[chosen.user_id]
        return {
            "user_id": chosen.user_id,
            "job_id": chosen.job_id,
            "weight": chosen.weight,
        }

    def _key_for(self, e: _FairEntry) -> tuple[float, int, int]:
        return (
            -e.weight,
            self._queued_per_user.get(e.user_id, 0),
            e.enqueue_seq,
        )
