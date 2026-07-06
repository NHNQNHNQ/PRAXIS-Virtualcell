"""Phase 8 · Task 8.10:Linux/Docker 发行 smoke(10 条,`@pytest.mark.integration`)。

设计约束:
- 全部标 `@pytest.mark.integration`,CI 用 `pytest -m "not integration"` 天然跳过;
- mac 本地(非 Linux 或无 docker)**必须全 skip** —— 用统一 `skipif` 判据,不真跑 docker;
- 真跑落在 .53(Linux + Docker 齐);
- 所有 subprocess 加 `timeout` 超时保护;docker 容器测试用固定 tag + 末尾 `docker rm -f` 清理。

判据:`sys.platform != "linux"` 或 `shutil.which("docker") is None` → skip。
这两条合并成一个 marker,保证 mac(darwin,通常也无 docker)10 条全 skip、0 failed。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

# ---- 仓库根(本文件在 praxis_virtualcell/tests/,上跳两级)----
_REPO_ROOT = Path(__file__).resolve().parents[2]

# ---- 统一 skip 判据:非 Linux 或无 docker → 整组 skip(mac 必 skip)----
_IS_LINUX = sys.platform == "linux"
_HAS_DOCKER = shutil.which("docker") is not None
_NO_LINUX_DOCKER = (not _IS_LINUX) or (not _HAS_DOCKER)
_SKIP_REASON = (
    "需 Linux + docker 的发行环境(mac/无 docker 自动 skip;真跑在 .53)"
)
requires_linux_docker = pytest.mark.skipif(_NO_LINUX_DOCKER, reason=_SKIP_REASON)

# ---- 固定 docker tag / 容器名(可复现 + 便于清理)----
_IMAGE_TAG = "praxis-vc-smoke:test"
_CONTAINER_NAME = "praxis-vc-smoke-test"

# ---- 超时(秒)----
_QUICK_TIMEOUT = 60          # CLI/demo 级
_BUILD_TIMEOUT = 900         # docker build(装依赖,给足)
_RUN_TIMEOUT = 60            # docker run 拉起
_HTTP_TIMEOUT = 30           # 容器内 HTTP 探活


def _run(cmd, *, cwd=None, timeout=_QUICK_TIMEOUT, check=False):
    """薄封装 subprocess.run:统一 text/capture/timeout。"""
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
    )


def _docker_cleanup():
    """强制清理固定 tag 的容器 + 镜像(幂等,失败不抛)。"""
    try:
        _run(["docker", "rm", "-f", _CONTAINER_NAME], timeout=_RUN_TIMEOUT)
    except Exception:  # noqa: BLE001
        pass
    try:
        _run(["docker", "rmi", "-f", _IMAGE_TAG], timeout=_RUN_TIMEOUT)
    except Exception:  # noqa: BLE001
        pass


@pytest.fixture()
def demo_out(tmp_path):
    """跑一次 offline demo,产出目录供多条用例断言(避免重复跑)。"""
    out = tmp_path / "demo"
    r = _run(
        [
            "praxis-vc", "run",
            "--request", str(_REPO_ROOT / "examples" / "ahr_k562.json"),
            "--mode", "offline",
            "--out", str(out),
        ],
        cwd=_REPO_ROOT,
        timeout=_QUICK_TIMEOUT,
    )
    assert r.returncode == 0, f"praxis-vc run 失败:{r.stderr}"
    assert out.is_dir(), "demo 输出目录未生成"
    return out


@pytest.fixture(scope="module")
def docker_image():
    """构建固定 tag 镜像(module 级,复用);结束强制清理容器+镜像。"""
    _docker_cleanup()
    r = _run(
        ["docker", "build", "-f", "deploy/vc/Dockerfile", "-t", _IMAGE_TAG, "."],
        cwd=_REPO_ROOT,
        timeout=_BUILD_TIMEOUT,
    )
    assert r.returncode == 0, f"docker build 失败:{r.stderr[-2000:]}"
    yield _IMAGE_TAG
    _docker_cleanup()


def _resolve_host_port(container_name, *, container_port=8000):
    """`docker run -p 0:8000` 后,用 `docker port` 解析 docker 实际分配的空闲 host 端口。

    docker port 输出形如 `0.0.0.0:49153`(可能多行 IPv4/IPv6),取首行冒号后的端口。
    因 host 8000 可能被长期服务占用,固定绑 8000 会 address already in use;
    绑 `0:8000` 让 docker 自选空闲 host 端口,规避冲突。
    """
    r = _run(
        ["docker", "port", container_name, f"{container_port}/tcp"],
        timeout=_RUN_TIMEOUT,
    )
    assert r.returncode == 0, f"docker port 解析失败:{r.stderr}"
    line = r.stdout.strip().splitlines()[0].strip()
    host_port = int(line.rsplit(":", 1)[1])
    assert host_port > 0, f"解析到非法 host 端口:{line}"
    return host_port


@pytest.fixture(scope="module")
def running_container(docker_image):
    """module 级:用**动态空闲 host 端口**(`-p 0:8000`)起一次容器,供三条容器用例复用。

    host 8000 可能被长期运行的服务占用,固定绑 8000 会 `address already in use`;
    这里让 docker 自选空闲 host 端口,再用 `docker port` 解析实际端口。
    yield 容器可访问的 base_url(如 `http://127.0.0.1:49xxx`);teardown `docker rm -f`。
    绝不 kill host 上任何占用 8000 的进程。
    """
    _run(["docker", "rm", "-f", _CONTAINER_NAME], timeout=_RUN_TIMEOUT)
    up = _run(
        ["docker", "run", "-d", "--name", _CONTAINER_NAME,
         "-p", "0:8000", docker_image],
        timeout=_RUN_TIMEOUT,
    )
    assert up.returncode == 0, f"docker run 失败:{up.stderr}"
    assert up.stdout.strip(), "无容器 id"
    try:
        host_port = _resolve_host_port(_CONTAINER_NAME)
        yield f"http://127.0.0.1:{host_port}"
    finally:
        _run(["docker", "rm", "-f", _CONTAINER_NAME], timeout=_RUN_TIMEOUT)


# ============================================================
# 1. python >= 3.11(发行最低版本线)
# ============================================================
@pytest.mark.integration
@requires_linux_docker
def test_python_version_ge_311():
    r = _run(
        [sys.executable, "-c",
         "import sys; assert sys.version_info >= (3, 11); print('ok')"],
        timeout=_QUICK_TIMEOUT,
    )
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


# ============================================================
# 2. praxis-vc --help(CLI 可用)
# ============================================================
@pytest.mark.integration
@requires_linux_docker
def test_cli_help():
    r = _run(["praxis-vc", "--help"], cwd=_REPO_ROOT, timeout=_QUICK_TIMEOUT)
    assert r.returncode == 0, r.stderr
    assert "praxis-vc" in (r.stdout + r.stderr)


# ============================================================
# 3. offline demo 产 report.md 且 >= 9 段
# ============================================================
@pytest.mark.integration
@requires_linux_docker
def test_offline_demo_report_has_ge_9_sections(demo_out):
    report = demo_out / "report.md"
    assert report.is_file(), "无 report.md"
    text = report.read_text(encoding="utf-8")
    n_sections = sum(1 for line in text.splitlines() if line.startswith("## "))
    assert n_sections >= 9, f"report.md 仅 {n_sections} 段,应 >= 9"


# ============================================================
# 4. wheel 在全新 venv 安装(发行可装性)
# ============================================================
@pytest.mark.integration
@requires_linux_docker
def test_wheel_installs_in_fresh_venv(tmp_path):
    # 4a. 构建 wheel
    dist = tmp_path / "dist"
    build = _run(
        [sys.executable, "-m", "pip", "wheel", ".",
         "--no-deps", "-w", str(dist)],
        cwd=_REPO_ROOT,
        timeout=_BUILD_TIMEOUT,
    )
    assert build.returncode == 0, f"pip wheel 失败:{build.stderr[-2000:]}"
    wheels = list(dist.glob("*.whl"))
    assert wheels, "未产出 wheel"

    # 4b. 全新 venv 安装
    venv_dir = tmp_path / "freshvenv"
    mk = _run([sys.executable, "-m", "venv", str(venv_dir)], timeout=_QUICK_TIMEOUT)
    assert mk.returncode == 0, mk.stderr
    py = venv_dir / "bin" / "python"
    inst = _run(
        [str(py), "-m", "pip", "install", str(wheels[0])],
        timeout=_BUILD_TIMEOUT,
    )
    assert inst.returncode == 0, f"fresh-venv 安装 wheel 失败:{inst.stderr[-2000:]}"
    # 装完能 import
    chk = _run(
        [str(py), "-c", "import praxis_virtualcell; print('ok')"],
        timeout=_QUICK_TIMEOUT,
    )
    assert chk.returncode == 0 and "ok" in chk.stdout, chk.stderr


# ============================================================
# 5. docker build -f deploy/vc/Dockerfile 成功
# ============================================================
@pytest.mark.integration
@requires_linux_docker
def test_docker_build(docker_image):
    # docker_image fixture 已断言 build 成功;这里核验镜像确实存在
    r = _run(
        ["docker", "images", "-q", docker_image],
        timeout=_RUN_TIMEOUT,
    )
    assert r.returncode == 0 and r.stdout.strip(), "构建后镜像不存在"


# ============================================================
# 6. docker run 容器起(offline 网页服务,动态空闲 host 端口)
# ============================================================
@pytest.mark.integration
@requires_linux_docker
def test_docker_run_container_up(running_container):
    # running_container fixture 已用 `-p 0:8000` 起好容器;这里核验其处于 running。
    time.sleep(3)
    insp = _run(
        ["docker", "inspect", "-f", "{{.State.Running}}", _CONTAINER_NAME],
        timeout=_RUN_TIMEOUT,
    )
    assert insp.stdout.strip() == "true", (
        f"容器未处于 running:{insp.stdout} / logs: "
        f"{_run(['docker', 'logs', _CONTAINER_NAME], timeout=_RUN_TIMEOUT).stderr[-1000:]}"
    )


# ============================================================
# 7. /api/health 返回 200(动态 host 端口)
# ============================================================
@pytest.mark.integration
@requires_linux_docker
def test_container_health_200(running_container):
    code = _poll_http(f"{running_container}/api/health")
    assert code == 200, f"/api/health 状态 {code}(期望 200)"


# ============================================================
# 8. /api/reports/{id}/markdown 可下载(容器内建 job → 取 markdown,动态 host 端口)
# ============================================================
@pytest.mark.integration
@requires_linux_docker
def test_container_report_markdown_download(running_container):
    assert _poll_http(f"{running_container}/api/health") == 200, "服务未就绪"

    import urllib.request

    # 建一个 offline job
    req = {
        "species": "human", "perturbation_type": "gene",
        "perturbation_targets": ["AHR"], "input_modality": "scRNA",
        "output_modality": "delta_expression",
        "task_type": "predict_delta_expression",
    }
    payload = json.dumps({"request": req, "mode": "offline"}).encode()
    post = urllib.request.Request(
        f"{running_container}/api/jobs", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(post, timeout=_HTTP_TIMEOUT) as resp:
        assert resp.status == 200
        jid = json.loads(resp.read().decode())["job_id"]

    # 下载 markdown
    with urllib.request.urlopen(
        f"{running_container}/api/reports/{jid}/markdown",
        timeout=_HTTP_TIMEOUT,
    ) as resp:
        assert resp.status == 200
        body = resp.read().decode("utf-8")
        assert "text/markdown" in resp.headers.get("content-type", "")
        assert "# PRAXIS-VirtualCell Report" in body


# ============================================================
# 9. 输出文件齐(report.md + report.json + trace.json + provenance.json)
# ============================================================
@pytest.mark.integration
@requires_linux_docker
def test_offline_demo_output_files_complete(demo_out):
    for name in ("report.md", "report.json", "trace.json", "provenance.json"):
        f = demo_out / name
        assert f.is_file(), f"缺输出文件:{name}"
        assert f.stat().st_size > 0, f"输出文件为空:{name}"
    # report.json / trace.json / provenance.json 合法 JSON
    json.loads((demo_out / "report.json").read_text(encoding="utf-8"))
    json.loads((demo_out / "trace.json").read_text(encoding="utf-8"))
    json.loads((demo_out / "provenance.json").read_text(encoding="utf-8"))


# ============================================================
# 10. offline demo 运行时间基线(< 60s)
# ============================================================
@pytest.mark.integration
@requires_linux_docker
def test_offline_demo_runtime_baseline(tmp_path):
    out = tmp_path / "timed"
    t0 = time.monotonic()
    r = _run(
        ["praxis-vc", "run",
         "--request", str(_REPO_ROOT / "examples" / "ahr_k562.json"),
         "--mode", "offline", "--out", str(out)],
        cwd=_REPO_ROOT,
        timeout=_QUICK_TIMEOUT,
    )
    elapsed = time.monotonic() - t0
    assert r.returncode == 0, r.stderr
    assert elapsed < 60, f"offline demo 耗时 {elapsed:.1f}s,超基线 60s"


# ------------------------------------------------------------
# 辅助:轮询 HTTP 直到就绪或超时,返回状态码(失败返回 -1)
# ------------------------------------------------------------
def _poll_http(url, *, timeout=_HTTP_TIMEOUT, interval=1.0):
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + timeout
    last = -1
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                return resp.status
        except urllib.error.HTTPError as e:  # 有响应但非 2xx
            last = e.code
            return last
        except Exception:  # noqa: BLE001  连接未就绪,重试
            time.sleep(interval)
    return last
