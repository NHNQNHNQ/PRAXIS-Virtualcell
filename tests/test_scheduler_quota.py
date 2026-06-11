"""§11.5 公平调度 + 配额 + 加权公平队列。"""

from praxis2.scheduler.quota import (
    FairQueue,
    Quota,
    QuotaConfig,
    UserQuotaState,
)


def test_quota_per_user_concurrent_limit():
    # §11.5 每用户并发作业配额(防单用户占满 GPU 饿死他人)
    q = Quota(QuotaConfig(max_concurrent_per_user=2, global_max_queued=100))
    assert q.try_acquire("u1") is True
    assert q.try_acquire("u1") is True
    assert q.try_acquire("u1") is False  # 超个人配额
    # 不同用户独立
    assert q.try_acquire("u2") is True
    # 释放后可再获取
    q.release("u1")
    assert q.try_acquire("u1") is True


def test_quota_global_queue_max_rejects_when_full():
    # 全局队列上限:满则拒绝(排队 vs 拒绝在 ResourceGate 层决策,本层硬拒)
    q = Quota(QuotaConfig(max_concurrent_per_user=100, global_max_queued=2))
    assert q.try_enqueue("u1") is True
    assert q.try_enqueue("u2") is True
    assert q.try_enqueue("u3") is False  # 全局队列满


def test_user_quota_state_tracks_running_and_queued():
    s = UserQuotaState()
    s.inc_running()
    s.inc_running()
    s.inc_queued()
    assert s.running == 2 and s.queued == 1
    s.dec_running()
    s.dec_queued()
    assert s.running == 1 and s.queued == 0


def test_fair_queue_weighted_round_robin_picks_higher_weight_first_when_tie():
    # 加权公平:同等队列长度下 weight 高的优先;同 weight 按 user_id 字典序确定性
    fq = FairQueue()
    fq.enqueue("u1", weight=1.0, job_id="j1")
    fq.enqueue("u2", weight=2.0, job_id="j2")
    fq.enqueue("u1", weight=1.0, job_id="j3")
    # u2 weight=2 高,优先出队;之后 u1 两个按 FIFO
    seq = [fq.dequeue() for _ in range(3)]
    assert seq[0]["user_id"] == "u2"
    assert seq[1]["user_id"] == "u1"
    assert seq[2]["user_id"] == "u1"
    assert fq.dequeue() is None  # 空队列返回 None


def test_fair_queue_prevents_user_starvation_within_window():
    # 防饥饿:u_heavy 反复入队不应让 u_light 无法被服务
    fq = FairQueue()
    for i in range(5):
        fq.enqueue("u_heavy", weight=1.0, job_id=f"h{i}")
    fq.enqueue("u_light", weight=1.0, job_id="l1")
    # 同权重:按入队顺序 FIFO,但 fair window(同权重轮询)保证 u_light 不被 5 个 heavy 全压住
    # 实现:同权重时按 (queued_count, enqueue_order) 升序排,queued 多的用户后调度
    seq = [fq.dequeue()["user_id"] for _ in range(6)]
    # u_light 应在前 3 位(被 fair 调度,不必排到第 6)
    assert "u_light" in seq[:3]


def test_global_queue_size_tracked_consistently():
    q = Quota(QuotaConfig(max_concurrent_per_user=100, global_max_queued=10))
    assert q.global_queued() == 0
    q.try_enqueue("u1")
    q.try_enqueue("u1")
    assert q.global_queued() == 2
    q.dequeue("u1")
    assert q.global_queued() == 1
