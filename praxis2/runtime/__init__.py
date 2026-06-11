"""多 worker 无状态并发基座(总纲 §11.1-11.4/§11.6/§11.8)。
锁/会话池/限流/多租户/并行编排/Task 状态机/SSE 跨 worker pub-sub。
内存版单进程模拟保证每个不变量正确性可测;真 Redis 分布式实测标
@pytest.mark.integration(无 docker 自动 skip,总纲 §5⑩,M6 校准②)。"""
