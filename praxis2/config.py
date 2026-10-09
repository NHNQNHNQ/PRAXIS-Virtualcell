"""§6⑤ 单一配置源 + fail-fast。

必填项无默认值(dataclass 强约束),`load_from_env()` 缺即抛 `ConfigError`;
**默认值仅给「零值即关闭」语义的字段**(如 `dump_prompts=""` 关闭、
`max_heavy_jobs_per_user=0` 关闭通道 B,§11.2)。

治 v1「默认值骗人 / canonical↔deployed 漂移」:任何「忘了配某项 → 跑起来
但行为不对」的路径,在本模块用 fail-fast 堵死。M0-M7 测试用 inline
`class S:` 配置不破(`Settings` 是新增可选用法,不强制替换历史测试)。"""

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """缺必填项 / 类型错误时抛(§6⑤ fail-fast,绝不静默默认)。"""


@dataclass
class Settings:
    """§6⑤ 单一配置源。必填项无默认,可选项给「零值即关」默认。

    必填:LLM 上游(api_key/base_url + 推理参数)、部署(host/port/workers)、
    限流配额(per_user 并发/qps/global_inflight/quota_max_queued)。
    可选:model(M10.5 默认 deepseek-v4-pro)、dump_prompts(空串=关 §7.2.8)、
    max_heavy_jobs_per_user(0=关 §11.5 通道 B)。"""

    # LLM 上游 + 推理参数(必填,除 model)
    anthropic_api_key: str
    anthropic_base_url: str
    max_tokens: int
    max_turns: int
    recovery_budget: int
    max_output_recovery: int

    # 部署(必填)
    host: str
    port: int
    workers: int

    # 限流配额(M6 通道 A)(必填)
    max_concurrent_per_user: int
    user_qps: float
    global_llm_inflight: int

    # 调度配额(M7 §11.5)(必填)
    quota_global_max_queued: int

    # M9 必填字段(但用空字符串默认值 fail-fast 由 load_from_env 控制)
    db_url: str = ""
    redis_url: str = ""
    password_pepper: str = ""

    # 可选(零值即关) + M10.5 model 默认
    model: str = "deepseek-v4-pro"  # M10.5:litellm yaml 切净后真名直跳
    dump_prompts: str = ""
    max_heavy_jobs_per_user: int = 0  # M7 通道 B(0=关)
    permission_ask_timeout_s: float = 60.0  # §7.6.2 ASK 用户响应超时(秒;0=立即 DENY)

    # M9 新增可选(零值即关 / dev fallback)
    cookie_secure: bool = False
    cookie_samesite: str = "Lax"
    session_ttl_days: int = 30
    allow_self_signup: bool = True
    smtp_host: str = ""  # 空 → DevEmailGateway 自动 fallback
    smtp_port: int = 0
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    # M9:注册赠送 li(=100元 默认),0 = 不赠
    signup_gift_li: int = 10000
    # M10:文件管理 3 个 env
    files_root: str = "/home/zkyd/data1/praxis2-files"
    files_quota_bytes: int = 100 * 1024**3            # 100 GB
    files_max_per_file_bytes: int = 20 * 1024**3      # 20 GB
    env_label: str = "dev"  # dev | staging | prod,用于 /api/info 返显

    # CORS(v0.9.1 staging hotfix):逗号分隔 origin 白名单,空=不发 CORS 头(同 origin 部署)
    allowed_origins: str = ""
    # 同 origin SPA(v0.9.1 hotfix):指向 dist/,backend GET 未命中 /api/* 走 SPA fallback
    # 空=不 serve static(默认),非空=同 origin 部署,根本解 cookie 跨域问题
    static_root: str = ""

    # M11.1 spawn(可选,有默认)
    spawn_max_concurrent_per_user: int = 2
    spawn_keep_last_per_user: int = 100
    spawn_partial_flush_chunks: int = 20
    llm_price_in_per_m_li: int = 1500
    llm_price_out_per_m_li: int = 6000

    # M11.2 MD + HPC SSH:默认未配置,启用时显式填写 host/user/key 三项
    hpc_ssh_host: str = ""
    hpc_ssh_user: str = ""
    hpc_ssh_key_path: str = ""
    hpc_ssh_timeout_s: float = 15.0
    md_hpc_account: str = "SCW6CHB"
    md_price_gpu_per_h_li: int = 10000
    md_price_cpu_per_h_li: int = 500
    md_free_cpu_hours_per_job: float = 1.0
    md_max_concurrent_per_user: int = 2
    md_poll_interval_s: int = 30
    md_check_gpus_script_path: str = "~/check_gpus.sh"
    # sbatch GROMACS 加载片段(默认 zkyd 的 conda env;非 zkyd 部署 override)
    md_gromacs_load_cmd: str = (
        "source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh\n"
        "conda activate praxis-md-cuda"
    )
    md_plumed_load_cmd: str = (
        "source /home/zkyd/software/gromacs-2024.3-plumed/activate_plumed.sh"
    )
    md_mpi_load_cmd: str = (
        "source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh\n"
        "conda activate praxis-md-mpi"
    )

    # M12 admin + proposals 配额
    admin_reconcile_max_users: int = 1000
    proposals_per_user_per_day: int = 20

    # v0.17 MCP client(可选,零值即关:空=不挂任何 MCP server)
    mcp_servers_json: str = ""

    # v0.17 子项目2 BashTool(默认关:软沙盒 opt-in;真隔离前 prod 不开)
    bash_tool_enabled: bool = False
    # v0.18 子项目1:文件系统真隔离(unshare userns),叠加在软沙盒上
    bash_isolation: bool = False
    # 额外遮蔽的绝对路径(逗号分隔),追加到默认敏感清单
    bash_isolation_mask: str = ""
    # v0.18 子项目2:cgroup 资源隔离(systemd-run --scope)
    bash_cgroup: bool = False
    bash_cgroup_mem_mb: int = 1024  # MemoryMax(MB),默认 1GB(与 rlimit_mem 对齐)
    bash_cgroup_cpu_pct: int = 100  # CPUQuota(%),默认 100=1 核
    # v0.18 子项目3:网络隔离(unshare --net),默认关 opt-in
    bash_netns: bool = False

    def __post_init__(self) -> None:
        """§6⑤ fail-fast:检查 prod 约束和可选 HPC SSH 配置完整性。"""
        if self.env_label == "prod" and not self.smtp_host:
            raise ConfigError(
                "env_label=prod 不允许 DevEmailGateway,请配置 PRAXIS_SMTP_HOST"
                "(§6⑤ fail-fast)"
            )

        ssh_settings = {
            "PRAXIS_HPC_SSH_HOST": self.hpc_ssh_host.strip(),
            "PRAXIS_HPC_SSH_USER": self.hpc_ssh_user.strip(),
            "PRAXIS_HPC_SSH_KEY_PATH": self.hpc_ssh_key_path.strip(),
        }
        if any(ssh_settings.values()) and not all(ssh_settings.values()):
            missing = ", ".join(key for key, value in ssh_settings.items() if not value)
            raise ConfigError(
                f"HPC SSH 配置不完整,请填写 {missing};"
                "未使用远程 MD 时请将 host/user/key 三项都留空"
            )


def _get_str(env: dict, key: str) -> str:
    v = env.get(key)
    if v is None or v == "":
        raise ConfigError(f"缺必填配置 {key}(§6⑤ fail-fast,绝不静默默认)")
    return v


def _get_int(env: dict, key: str) -> int:
    raw = _get_str(env, key)
    try:
        return int(raw)
    except ValueError as e:
        raise ConfigError(f"配置 {key}={raw!r} 不是合法整数(§6⑤ fail-fast)") from e


def _get_bool(env: dict, key: str, default: bool) -> bool:
    """M9:可选 bool 字段(空串=用默认;true/1/yes/on=True;false/0/no/off=False)。"""
    v = env.get(key, "").strip().lower()
    if v == "":
        return default
    if v in ("true", "1", "yes", "on"):
        return True
    if v in ("false", "0", "no", "off"):
        return False
    raise ConfigError(f"配置 {key}={v!r} 不是合法 bool(§6⑤)")


def _get_float(env: dict, key: str) -> float:
    raw = _get_str(env, key)
    try:
        return float(raw)
    except ValueError as e:
        raise ConfigError(f"配置 {key}={raw!r} 不是合法浮点(§6⑤ fail-fast)") from e


_KNOWN_KEYS = frozenset({
    # 必填:LLM 上游 + 推理参数
    "PRAXIS_ANTHROPIC_API_KEY", "PRAXIS_ANTHROPIC_BASE_URL", "PRAXIS_MODEL",
    "PRAXIS_MAX_TOKENS", "PRAXIS_MAX_TURNS", "PRAXIS_RECOVERY_BUDGET",
    "PRAXIS_MAX_OUTPUT_RECOVERY",
    # 必填:部署
    "PRAXIS_HOST", "PRAXIS_PORT", "PRAXIS_WORKERS",
    # 必填:限流配额(M6 通道 A) + 调度配额(M7 §11.5)
    "PRAXIS_MAX_CONCURRENT_PER_USER", "PRAXIS_USER_QPS",
    "PRAXIS_GLOBAL_LLM_INFLIGHT", "PRAXIS_QUOTA_GLOBAL_MAX_QUEUED",
    # 可选(零值即关)
    "PRAXIS_DUMP_PROMPTS", "PRAXIS_MAX_HEAVY_JOBS_PER_USER",
    # A.6 fixup I2(v0.9.1):§7.6.2 ASK 用户响应超时
    "PRAXIS_PERMISSION_ASK_TIMEOUT_S",
    # M9 必填:认证 / 持久化 / Redis
    "PRAXIS_DB_URL", "PRAXIS_REDIS_URL", "PRAXIS_PASSWORD_PEPPER",
    # M9 可选:cookie / session / signup
    "PRAXIS_COOKIE_SECURE", "PRAXIS_COOKIE_SAMESITE",
    "PRAXIS_SESSION_TTL_DAYS", "PRAXIS_ALLOW_SELF_SIGNUP",
    # M9 可选:SMTP / 环境标签 / 注册赠送
    "PRAXIS_SMTP_HOST", "PRAXIS_SMTP_PORT", "PRAXIS_SMTP_USER",
    "PRAXIS_SMTP_PASSWORD", "PRAXIS_SMTP_FROM", "PRAXIS_SIGNUP_GIFT_LI", "PRAXIS_ENV_LABEL",
    "PRAXIS_ALLOWED_ORIGINS", "PRAXIS_STATIC_ROOT",
    # M10 文件管理
    "PRAXIS_FILES_ROOT",
    "PRAXIS_FILES_QUOTA_BYTES",
    "PRAXIS_FILES_MAX_PER_FILE_BYTES",
    # v0.9.4 SkillExecTool 真 ssh 执行三件套(tools/skill_exec.py 直接读 os.environ,
    # config 不解析,这里只为通过白名单);缺即 SkillExec 自动降级到 SOP-only。
    "PRAXIS_SKILL_SSH_HOST", "PRAXIS_SKILL_REMOTE_BRAINS",
    "PRAXIS_SKILL_CONDA_INIT", "PRAXIS_SKILL_TIMEOUT_S",
    # M11.1 spawn
    "PRAXIS_SPAWN_MAX_CONCURRENT_PER_USER",
    "PRAXIS_SPAWN_KEEP_LAST_PER_USER",
    "PRAXIS_SPAWN_PARTIAL_FLUSH_CHUNKS",
    "PRAXIS_LLM_PRICE_IN_PER_M_LI",
    "PRAXIS_LLM_PRICE_OUT_PER_M_LI",
    # M11.2 MD + HPC SSH
    "PRAXIS_HPC_SSH_HOST",
    "PRAXIS_HPC_SSH_USER",
    "PRAXIS_HPC_SSH_KEY_PATH",
    "PRAXIS_HPC_SSH_TIMEOUT_S",
    "PRAXIS_MD_HPC_ACCOUNT",
    "PRAXIS_MD_PRICE_GPU_PER_H_LI",
    "PRAXIS_MD_PRICE_CPU_PER_H_LI",
    "PRAXIS_MD_FREE_CPU_HOURS_PER_JOB",
    "PRAXIS_MD_MAX_CONCURRENT_PER_USER",
    "PRAXIS_MD_POLL_INTERVAL_S",
    "PRAXIS_MD_CHECK_GPUS_SCRIPT_PATH",
    "PRAXIS_MD_GROMACS_LOAD_CMD",
    "PRAXIS_MD_PLUMED_LOAD_CMD",
    "PRAXIS_MD_MPI_LOAD_CMD",
    # M12 admin + proposals 配额
    "PRAXIS_ADMIN_RECONCILE_MAX_USERS",
    "PRAXIS_PROPOSALS_PER_USER_PER_DAY",
    # v0.17 MCP client
    "PRAXIS_MCP_SERVERS_JSON",
    # v0.17 子项目2 BashTool
    "PRAXIS_BASH_TOOL_ENABLED",
    # v0.18 子项目1:文件系统真隔离
    "PRAXIS_BASH_ISOLATION",
    "PRAXIS_BASH_ISOLATION_MASK",
    # v0.18 子项目2:cgroup 资源隔离
    "PRAXIS_BASH_CGROUP",
    "PRAXIS_BASH_CGROUP_MEM_MB",
    "PRAXIS_BASH_CGROUP_CPU_PCT",
    # v0.18 子项目3:网络隔离
    "PRAXIS_BASH_NETNS",
})
# 旁路:`PRAXIS_CFG_TEST_*` 前缀给测试覆盖用,不在白名单也放行
_CFG_TEST_PREFIX = "PRAXIS_CFG_TEST_"


def load_from_env(env: "dict | None" = None) -> Settings:
    """从环境变量装载 Settings。缺必填项 / 类型错误 / 未知 PRAXIS_* key → ConfigError。
    `env` 默认 os.environ;测试可注入字典隔离副作用。

    §6⑤ fail-fast:未知 PRAXIS_* key 拒掉,防 typo(如 PRAXIS_WROKERS=4)静默吞掉
    用默认值 — typo 与忘配同等恶劣。`PRAXIS_CFG_TEST_*` 前缀旁路给测试覆盖用。"""
    e = env if env is not None else os.environ
    unknown = sorted(
        k for k in e
        if k.startswith("PRAXIS_")
        and k not in _KNOWN_KEYS
        and not k.startswith(_CFG_TEST_PREFIX)
    )
    if unknown:
        raise ConfigError(
            f"未知配置 {unknown}(§6⑤ 拒未知;检查 typo 或在 _KNOWN_KEYS 注册)"
        )
    return Settings(
        anthropic_api_key=_get_str(e, "PRAXIS_ANTHROPIC_API_KEY"),
        anthropic_base_url=_get_str(e, "PRAXIS_ANTHROPIC_BASE_URL"),
        max_tokens=_get_int(e, "PRAXIS_MAX_TOKENS"),
        max_turns=_get_int(e, "PRAXIS_MAX_TURNS"),
        recovery_budget=_get_int(e, "PRAXIS_RECOVERY_BUDGET"),
        max_output_recovery=_get_int(e, "PRAXIS_MAX_OUTPUT_RECOVERY"),
        host=_get_str(e, "PRAXIS_HOST"),
        port=_get_int(e, "PRAXIS_PORT"),
        workers=_get_int(e, "PRAXIS_WORKERS"),
        max_concurrent_per_user=_get_int(e, "PRAXIS_MAX_CONCURRENT_PER_USER"),
        user_qps=_get_float(e, "PRAXIS_USER_QPS"),
        global_llm_inflight=_get_int(e, "PRAXIS_GLOBAL_LLM_INFLIGHT"),
        quota_global_max_queued=_get_int(e, "PRAXIS_QUOTA_GLOBAL_MAX_QUEUED"),
        db_url=_get_str(e, "PRAXIS_DB_URL"),
        redis_url=_get_str(e, "PRAXIS_REDIS_URL"),
        password_pepper=_get_str(e, "PRAXIS_PASSWORD_PEPPER"),
        # M10.5:model 改为可选,默认 deepseek-v4-pro
        model=e.get("PRAXIS_MODEL", "deepseek-v4-pro"),
        dump_prompts=e.get("PRAXIS_DUMP_PROMPTS", ""),
        max_heavy_jobs_per_user=int(e.get("PRAXIS_MAX_HEAVY_JOBS_PER_USER", "0")),
        permission_ask_timeout_s=float(
            e.get("PRAXIS_PERMISSION_ASK_TIMEOUT_S", "60.0")
        ),
        # M9 新增可选
        cookie_secure=_get_bool(e, "PRAXIS_COOKIE_SECURE", False),
        cookie_samesite=e.get("PRAXIS_COOKIE_SAMESITE", "Lax"),
        session_ttl_days=int(e.get("PRAXIS_SESSION_TTL_DAYS", "30")),
        allow_self_signup=_get_bool(e, "PRAXIS_ALLOW_SELF_SIGNUP", True),
        smtp_host=e.get("PRAXIS_SMTP_HOST", ""),
        smtp_port=int(e.get("PRAXIS_SMTP_PORT", "0")),
        smtp_user=e.get("PRAXIS_SMTP_USER", ""),
        smtp_password=e.get("PRAXIS_SMTP_PASSWORD", ""),
        smtp_from=e.get("PRAXIS_SMTP_FROM", ""),
        signup_gift_li=int(e.get("PRAXIS_SIGNUP_GIFT_LI", "10000")),
        files_root=e.get("PRAXIS_FILES_ROOT", "/home/zkyd/data1/praxis2-files"),
        files_quota_bytes=int(e.get(
            "PRAXIS_FILES_QUOTA_BYTES", str(100 * 1024**3))),
        files_max_per_file_bytes=int(e.get(
            "PRAXIS_FILES_MAX_PER_FILE_BYTES", str(20 * 1024**3))),
        env_label=e.get("PRAXIS_ENV_LABEL", "dev"),
        allowed_origins=e.get("PRAXIS_ALLOWED_ORIGINS", ""),
        static_root=e.get("PRAXIS_STATIC_ROOT", ""),
        spawn_max_concurrent_per_user=int(e.get(
            "PRAXIS_SPAWN_MAX_CONCURRENT_PER_USER", "2")),
        spawn_keep_last_per_user=int(e.get(
            "PRAXIS_SPAWN_KEEP_LAST_PER_USER", "100")),
        spawn_partial_flush_chunks=int(e.get(
            "PRAXIS_SPAWN_PARTIAL_FLUSH_CHUNKS", "20")),
        llm_price_in_per_m_li=int(e.get(
            "PRAXIS_LLM_PRICE_IN_PER_M_LI", "1500")),
        llm_price_out_per_m_li=int(e.get(
            "PRAXIS_LLM_PRICE_OUT_PER_M_LI", "6000")),
        hpc_ssh_host=e.get("PRAXIS_HPC_SSH_HOST", ""),
        hpc_ssh_user=e.get("PRAXIS_HPC_SSH_USER", ""),
        hpc_ssh_key_path=e.get("PRAXIS_HPC_SSH_KEY_PATH", ""),
        hpc_ssh_timeout_s=float(e.get("PRAXIS_HPC_SSH_TIMEOUT_S", "15.0")),
        md_hpc_account=e.get("PRAXIS_MD_HPC_ACCOUNT", "SCW6CHB"),
        md_price_gpu_per_h_li=int(e.get("PRAXIS_MD_PRICE_GPU_PER_H_LI", "10000")),
        md_price_cpu_per_h_li=int(e.get("PRAXIS_MD_PRICE_CPU_PER_H_LI", "500")),
        md_free_cpu_hours_per_job=float(e.get(
            "PRAXIS_MD_FREE_CPU_HOURS_PER_JOB", "1.0")),
        md_max_concurrent_per_user=int(e.get(
            "PRAXIS_MD_MAX_CONCURRENT_PER_USER", "2")),
        md_poll_interval_s=int(e.get("PRAXIS_MD_POLL_INTERVAL_S", "30")),
        md_check_gpus_script_path=e.get(
            "PRAXIS_MD_CHECK_GPUS_SCRIPT_PATH", "~/check_gpus.sh"),
        md_gromacs_load_cmd=e.get(
            "PRAXIS_MD_GROMACS_LOAD_CMD",
            "source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh\n"
            "conda activate praxis-md-cuda",
        ),
        md_plumed_load_cmd=e.get(
            "PRAXIS_MD_PLUMED_LOAD_CMD",
            "source /home/zkyd/software/gromacs-2024.3-plumed/activate_plumed.sh",
        ),
        md_mpi_load_cmd=e.get(
            "PRAXIS_MD_MPI_LOAD_CMD",
            "source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh\n"
            "conda activate praxis-md-mpi",
        ),
        admin_reconcile_max_users=int(e.get(
            "PRAXIS_ADMIN_RECONCILE_MAX_USERS", "1000")),
        proposals_per_user_per_day=int(e.get(
            "PRAXIS_PROPOSALS_PER_USER_PER_DAY", "20")),
        mcp_servers_json=e.get("PRAXIS_MCP_SERVERS_JSON", ""),
        bash_tool_enabled=_get_bool(e, "PRAXIS_BASH_TOOL_ENABLED", False),
        bash_isolation=_get_bool(e, "PRAXIS_BASH_ISOLATION", False),
        bash_isolation_mask=e.get("PRAXIS_BASH_ISOLATION_MASK", ""),
        bash_cgroup=_get_bool(e, "PRAXIS_BASH_CGROUP", False),
        bash_cgroup_mem_mb=int(e.get("PRAXIS_BASH_CGROUP_MEM_MB") or "1024"),
        bash_cgroup_cpu_pct=int(e.get("PRAXIS_BASH_CGROUP_CPU_PCT") or "100"),
        bash_netns=_get_bool(e, "PRAXIS_BASH_NETNS", False),
    )
