from praxis2.scheduler.quota import (
    FairQueue,
    Quota,
    QuotaConfig,
    UserQuotaState,
)


def test_quota_per_user_concurrent_limit():

    q = Quota(QuotaConfig(max_concurrent_per_user=2, global_max_queued=100))
    assert q.try_acquire("u1") is True
    assert q.try_acquire("u1") is True
    assert q.try_acquire("u1") is False

    assert q.try_acquire("u2") is True

    q.release("u1")
    assert q.try_acquire("u1") is True


def test_quota_global_queue_max_rejects_when_full():

    q = Quota(QuotaConfig(max_concurrent_per_user=100, global_max_queued=2))
    assert q.try_enqueue("u1") is True
    assert q.try_enqueue("u2") is True
    assert q.try_enqueue("u3") is False


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

    fq = FairQueue()
    fq.enqueue("u1", weight=1.0, job_id="j1")
    fq.enqueue("u2", weight=2.0, job_id="j2")
    fq.enqueue("u1", weight=1.0, job_id="j3")

    seq = [fq.dequeue() for _ in range(3)]
    assert seq[0]["user_id"] == "u2"
    assert seq[1]["user_id"] == "u1"
    assert seq[2]["user_id"] == "u1"
    assert fq.dequeue() is None


def test_fair_queue_prevents_user_starvation_within_window():

    fq = FairQueue()
    for i in range(5):
        fq.enqueue("u_heavy", weight=1.0, job_id=f"h{i}")
    fq.enqueue("u_light", weight=1.0, job_id="l1")

    seq = [fq.dequeue()["user_id"] for _ in range(6)]

    assert "u_light" in seq[:3]


def test_global_queue_size_tracked_consistently():
    q = Quota(QuotaConfig(max_concurrent_per_user=100, global_max_queued=10))
    assert q.global_queued() == 0
    q.try_enqueue("u1")
    q.try_enqueue("u1")
    assert q.global_queued() == 2
    q.dequeue("u1")
    assert q.global_queued() == 1
